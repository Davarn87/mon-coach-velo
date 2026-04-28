import streamlit as st
import requests
import google.generativeai as genai

# --- SECRETS STRAVA ---
CLIENT_ID = st.secrets["STRAVA_CLIENT_ID"]
CLIENT_SECRET = st.secrets["STRAVA_CLIENT_SECRET"]
REFRESH_TOKEN = st.secrets["STRAVA_REFRESH_TOKEN"]
GEMINI_KEY = st.secrets["GEMINI_KEY"]

# Configuration Gemini
genai.configure(api_key=GEMINI_KEY)
# 1. Utilise le nom complet du modèle stable
model = genai.GenerativeModel('models/gemini-1.5-flash')

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
def get_last_strava_activity(access_token):
    headers = {'Authorization': f"Bearer {access_token}"}
    # On récupère les activités du sportif authentifié
    res = requests.get("https://www.strava.com/api/v3/athlete/activities?per_page=1", headers=headers)
    if res.status_code == 200:
        return res.json()[0]
    return None

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

                Donne un feedback technique en 2 ou 3 phrases maximum. 
                Parle de l'intensité, suggère une récupération si nécessaire, et reste motivant.
                """
                try:
                    # Appel au modèle avec le nom complet
                    model = genai.GenerativeModel('models/gemini-1.5-flash')
                    response = model.generate_content(prompt)
        
                    st.info(f"🤖 **Le mot du Coach :** {response.text}")
                except Exception as e:
                    st.error(f"L'IA est indisponible : {e}")
          except Exception as e:
            st.error(f"Erreur de connexion Strava : {e}")
