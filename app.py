import streamlit as st
import requests
import google.generativeai as genai
import pandas as pd
import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Aixle Coach IA 2026", page_icon="🚴‍♂️", layout="wide")

# --- CHARGEMENT DES SECRETS ---
try:
    GENAI_KEY = st.secrets["GEMINI_KEY"]
    STRAVA_CLIENT_ID = st.secrets["STRAVA_CLIENT_ID"]
    STRAVA_CLIENT_SECRET = st.secrets["STRAVA_CLIENT_SECRET"]
    STRAVA_REFRESH_TOKEN = st.secrets["STRAVA_REFRESH_TOKEN"]
    
    # Paramètres de coaching
    FTP = 208  # Ta FTP actuelle
    OBJ_ANNUEL = st.secrets.get("OBJECTIF_ANNUEL", 5000)
    NOM_COURSE = st.secrets.get("NOM_COURSE", "Objectif Principal")
    JOURS_AVANT_COURSE = st.secrets.get("JOURS_AVANT_COURSE", 30)
    
    genai.configure(api_key=GENAI_KEY)
    model = genai.GenerativeModel('models/gemini-2.5-flash')
except Exception as e:
    st.error(f"Erreur de configuration (Secrets) : {e}")
    st.stop()

# --- FONCTIONS TECHNIQUES ---
def get_strava_access_token():
    payload = {
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'refresh_token': STRAVA_REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    }
    res = requests.post("https://www.strava.com/oauth/token", data=payload)
    return res.json().get('access_token')

def get_activities(access_token, days=30):
    headers = {'Authorization': f"Bearer {access_token}"}
    after = int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp())
    url = f"https://www.strava.com/api/v3/athlete/activities?after={after}&per_page=100"
    res = requests.get(url, headers=headers)
    return res.json() if res.status_code == 200 else []

# --- INTERFACE PRINCIPALE ---
st.title("⚡ Aixle Coach IA : Dashboard 2026")
st.markdown(f"**Profil Athlète :** FTP {FTP}W | Objectif : {NOM_COURSE} (J-{JOURS_AVANT_COURSE})")

if st.button("🚀 Synchroniser & Analyser ma forme"):
    with st.spinner("Récupération des données Strava..."):
        token = get_strava_access_token()
        activities = get_activities(token)
        
        if activities:
            # --- TRAITEMENT DES DONNÉES ---
            # --- REMPLACE LE BLOC DE TRAITEMENT DES DONNÉES PAR CELUI-CI ---

            df = pd.DataFrame([
                {
                    'Date': a['start_date_local'][:10],
                    'Distance': a['distance'] / 1000,
                    'Duree_min': a['moving_time'] / 60,
                    'Watts': a.get('average_watts', 0) if a.get('average_watts') else 0,
                    # Si Strava n'a pas de suffer_score, on l'estime (Temps * Intensité relative)
                    'Charge': a.get('suffer_score') if a.get('suffer_score') else (a['moving_time'] / 60) * ( (a.get('average_watts', 150) / FTP) ** 2 * 100 / 60 )
                } for a in activities
            ])
            
            # On s'assure que 'Charge' n'est jamais nul pour le graphique
            df['Charge'] = df['Charge'].fillna(df['Duree_min'] * 0.8) # Valeur par défaut basée sur le temps
            # --- AFFICHAGE DES MÉTRIQUES ---
            col1, col2, col3 = st.columns(3)
            
            last_7_days = df[df['Date'] >= (datetime.datetime.now() - datetime.timedelta(days=7))]
            load_week = last_7_days['Charge'].sum()
            load_month_avg = df_daily['Charge'].sum() / 4
            ratio = load_week / load_month_avg if load_month_avg > 0 else 1.0
            
            with col1:
                st.metric("Charge Hebdo", f"{int(load_week)} pts")
            with col2:
                status = "Optimal" if 0.8 <= ratio <= 1.3 else "Fatigue" if ratio > 1.3 else "Reprise"
                st.metric("Ratio de Forme", f"{ratio:.2f}", delta=status)
            with col3:
                total_km = df['Distance'].sum()
                st.metric("Distance (30j)", f"{total_km:.1f} km")

            # --- GRAPHIQUE DE CHARGE ---
            st.subheader("📈 Courbe de charge d'entraînement (PMC)")
            st.area_chart(df_daily.set_index('Date')['Charge'], color="#FC4C02")

            # --- ANALYSE IA GÉNÉRATIVE ---
            st.markdown("---")
            st.subheader("📋 Prescription de l'IA Coach")
            
            prompt = f"""
            Tu es un coach cycliste expert type Aixle.
            Données de l'athlète :
            - FTP : {FTP} Watts
            - Historique charge (30j) : {df_daily['Charge'].tolist()}
            - Ratio actuel : {ratio:.2f}
            - Jours restants avant {NOM_COURSE} : {JOURS_AVANT_COURSE}

            MISSION :
            1. Analyse l'état de fraîcheur.
            2. Génère une séance précise pour demain en utilisant les zones basées sur la FTP de {FTP}W :
               - Z1 (Récup) : < 115W
               - Z2 (Endurance) : 115-155W
               - Z3 (Tempo) : 155-185W
               - Z4 (Seuil) : 185-220W
               - Z5 (PMA) : > 220W
            
            FORMAT :
            - Diagnostic de forme
            - Bloc "SÉANCE DU JOUR" structuré (Échauffement, Corps, Récup) avec les Watts cibles.
            - Conseil nutritionnel.
            """
            
            try:
                response = model.generate_content(prompt)
                st.success("Analyse terminée")
                
                # Style "Carte d'entraînement"
                st.markdown(f"""
                <div style="background-color: #262730; padding: 25px; border-radius: 15px; border-left: 8px solid #FC4C02; color: white;">
                    {response.text.replace('##', '###')}
                </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Erreur Gemini : {e}")
        else:
            st.warning("Aucune activité trouvée. Vérifie tes permissions Strava (scope:activity:read_all).")

# --- FOOTER ---
st.sidebar.markdown("---")
st.sidebar.write("🦾 Powered by Gemini 2.5 Flash")
st.sidebar.write(f"Cible 2026 : {st.secrets.get('OBJECTIF_ANNUEL', 5000)} km")
