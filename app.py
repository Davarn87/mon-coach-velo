import streamlit as st
import requests
import google.generativeai as genai

# --- SECRETS STRAVA ---
CLIENT_ID = st.secrets["STRAVA_CLIENT_ID"]
CLIENT_SECRET = st.secrets["STRAVA_CLIENT_SECRET"]
REFRESH_TOKEN = st.secrets["STRAVA_REFRESH_TOKEN"]
GEMINI_KEY = st.secrets["GEMINI_KEY"]

# Configuration Gemini
genai.configure(api_key=st.secrets["GEMINI_KEY"])
model = genai.GenerativeModel('models/gemini-2.5-flash')
# Remplace ta configuration Gemini par ceci pour tester :
#try:
 #   genai.configure(api_key=st.secrets["GEMINI_KEY"])
    # On liste les modèles disponibles pour TA clé
 #   available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
 #   st.write(f"Modèles accessibles : {available_models}")
    
    # On prend le premier de la liste (souvent gemini-1.5-flash)
 #   model = genai.GenerativeModel(available_models[0])
#except Exception as e:
 #   st.error(f"Erreur d'accès aux modèles : {e}")


# 2. Utilise un bloc Try/Except plus robuste pour l'analyse
try:
    # On force l'appel au modèle
    response = model.generate_content(prompt)
    feedback = response.text
except Exception as e:
    feedback = f"Désolé, j'ai eu un petit souci technique pour analyser cette sortie. (Erreur : {str(e)})"

# --- FONCTION : OBTENIR UN JETON VALIDE ---
def get_strava_access_token():
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': "refresh_token",
        'f': 'json'
    }
    res = requests.post("https://www.strava.com/oauth/token", data=payload)
    return res.json()['access_token']

# --- FONCTION : RÉCUPÉRER LA DERNIÈRE ACTIVITÉ ---
import datetime

# --- FONCTION : RÉCUPÉRER LES ACTIVITÉS DE LA SEMAINE ---
def get_weekly_activities(access_token):
    headers = {'Authorization': f"Bearer {access_token}"}
    # Calcul du timestamp d'il y a 7 jours
    seven_days_ago = int((datetime.datetime.now() - datetime.timedelta(days=7)).timestamp())
    
    url = f"https://www.strava.com/api/v3/athlete/activities?after={seven_days_ago}&per_page=50"
    res = requests.get(url, headers=headers)
    return res.json() if res.status_code == 200 else []

# --- INTERFACE ---
st.title("📅 Bilan Hebdomadaire & Objectifs")

if st.button("📊 Analyser ma semaine"):
    with st.spinner("Analyse de la semaine en cours..."):
        token = get_strava_access_token()
        activities = get_weekly_activities(token)
        
        if activities:
            # Calculs des totaux
            total_dist = sum(a['distance'] for a in activities) / 1000
            total_time_min = sum(a['moving_time'] for a in activities) / 60
            total_elev = sum(a.get('total_elevation_gain', 0) for a in activities)
            nb_seances = len(activities)
            
            # Affichage des stats
            col1, col2, col3 = st.columns(3)
            col1.metric("Distance Totale", f"{total_dist:.1f} km")
            col2.metric("Temps Total", f"{total_time_min/60:.1f} h", 
                        delta=f"{ (total_time_min/60) - st.secrets['OBJ_HEURES_SEMAINE']:.1f} h vs Obj")
            col3.metric("Dénivelé", f"{total_elev} m",
                        delta=f"{total_elev - st.secrets['OBJ_DENIVELE_SEMAINE']} m vs Obj")

            # --- PROMPT POUR LE BILAN IA ---
            prompt_bilan = f"""
            Tu es un coach expert. Voici le bilan de ma semaine de vélo :
            - Nombre de séances : {nb_seances}
            - Temps total : {total_time_min/60:.1f} heures (Objectif : {st.secrets['OBJ_HEURES_SEMAINE']}h)
            - Dénivelé total : {total_elev} m (Objectif : {st.secrets['OBJ_DENIVELE_SEMAINE']}m)
            - Distance totale : {total_dist:.1f} km

            Analyse si j'ai respecté ma charge d'entraînement. 
            Si je suis au-dessus, mets-moi en garde contre le surentraînement. 
            Si je suis en-dessous, donne-moi un conseil pour rattraper ou ajuste l'objectif.
            Sois précis et motivant.
            """
            
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            response = model.generate_content(prompt_bilan)
            
            st.success("🤖 **Bilan du Coach :**")
            st.write(response.text)
            
            # Petit détail des séances
            with st.expander("Voir le détail des séances"):
                for a in activities:
                    st.write(f"- {a['start_date_local'][:10]} : {a['name']} ({a['distance']/1000:.1f}km)")
        else:
            st.warning("Aucune activité trouvée ces 7 derniers jours.")

# --- INTERFACE ---
st.title("🚴‍♂️ Coach IA via Strava")

if st.button("🔄 Analyser ma dernière sortie Strava"):
    with st.spinner("Récupération des données Strava..."):
        try:
            token = get_strava_access_token()
            activity = get_last_strava_activity(token)
            
            if activity:
                st.markdown(f"### 📊 {activity['name']}")
                
                # Calcul de l'intensité (Strava donne les watts moyens)
                watts = activity.get('average_watts', 0)
                dist = activity.get('distance', 0) / 1000 # en km
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Distance", f"{dist:.1f} km")
                c2.metric("Watts Moy.", f"{watts} W")
                c3.metric("Dénivelé", f"{activity.get('total_elevation_gain')} m")
                
                # Feedback IA
                # Nouveau prompt plus "Pro"
                prompt = f"""
                Tu es un coach cycliste expert. Analyse cette sortie Strava :
                - Nom de la séance : {activity.get('name')}
                - Distance : {dist:.1f} km
                - Puissance moyenne : {watts} W
                - Dénivelé : {activity.get('total_elevation_gain')} m
                - Type d'activité : {activity.get('type')}
Mon FTP est de 207W, analyse si j'étais bien en Endurance (Z2) sur cette sortie"

                Donne un feedback technique en 2 ou 3 phrases maximum. 
                Parle de l'intensité, suggère une récupération si nécessaire, et reste motivant.
                """
                try:
                    # Appel au modèle avec le nom complet
                    model = genai.GenerativeModel('models/gemini-2.5-flash')
                    response = model.generate_content(prompt)
        
                    st.info(f"🤖 **Le mot du Coach :** {response.text}")
                except Exception as e:
                    st.error(f"L'IA est indisponible : {e}")
        except Exception as e:
            st.error(f"Erreur de connexion Strava : {e}")
