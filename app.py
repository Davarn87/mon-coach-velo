import streamlit as st
import requests
import google.generativeai as genai
import pandas as pd
import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Aixle kJ Coach 2026", page_icon="🚴‍♂️", layout="wide")

# --- CHARGEMENT DES SECRETS ---
try:
    GENAI_KEY = st.secrets["GEMINI_KEY"]
    STRAVA_CLIENT_ID = st.secrets["STRAVA_CLIENT_ID"]
    STRAVA_CLIENT_SECRET = st.secrets["STRAVA_CLIENT_SECRET"]
    STRAVA_REFRESH_TOKEN = st.secrets["STRAVA_REFRESH_TOKEN"]
    
    FTP = 208  # Ta FTP
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
st.title("⚡ Aixle Coach IA : Métrique kJ (Kilojoules)")
st.markdown(f"**Profil Athlète :** FTP {FTP}W | Objectif : {NOM_COURSE} (J-{JOURS_AVANT_COURSE})")

if st.button("🚀 Synchroniser & Calculer le travail (kJ)"):
    with st.spinner("Analyse énergétique des données Strava..."):
        token = get_strava_access_token()
        activities = get_activities(token)
        
        if activities:
            # --- TRAITEMENT DES DONNÉES EN kJ ---
            df_list = []
            for a in activities:
                # 1. Récupération des Watts et de la durée
                watts = a.get('average_watts', 0) if a.get('average_watts') else 0
                duration_sec = a.get('moving_time', 0)
                
                # 2. Extraction ou calcul des kJ
                # Si Strava a la valeur directe (capteur), on la prend, sinon on l'estime via les Watts
                if a.get('kilojoules'):
                    kj = a['kilojoules']
                elif watts > 0:
                    kj = (watts * duration_sec) / 1000
                else:
                    kj = (140 * duration_sec) / 1000 # Estimation par défaut à 140W de moyenne si aucune donnée
                
                df_list.append({
                    'Date': a['start_date_local'][:10],
                    'Distance': a['distance'] / 1000,
                    'Duree_min': duration_sec / 60,
                    'Watts': watts,
                    'kJ': kj
                })
                
            df = pd.DataFrame(df_list)
            df['Date'] = pd.to_datetime(df['Date'])

            # Groupement par jour pour la courbe
            df_daily = df.groupby('Date').sum().reset_index().sort_values('Date')

            # --- CALCUL DES INDICATEURS DE CHARGE kJ ---
            now = datetime.datetime.now()
            seven_days_ago = now - datetime.timedelta(days=7)
            last_7_days = df[df['Date'] >= seven_days_ago]
            
            kj_week = last_7_days['kJ'].sum()
            kj_month_total = df_daily['kJ'].sum()
            kj_week_avg_month = kj_month_total / 4 # Moyenne hebdo sur le mois
            
            # Ratio de fatigue énergétique (Aixle kJ Ratio)
            ratio_kj = kj_week / kj_week_avg_month if kj_week_avg_month > 0 else 1.0

            # --- AFFICHAGE DES MÉTRIQUES ---
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Travail Hebdo (kJ)", f"{int(kj_week)} kJ", help="Énergie totale produite cette semaine")
            with col2:
                status = "Équilibré" if 0.8 <= ratio_kj <= 1.3 else "Surcharge Énergétique" if ratio_kj > 1.3 else "Sous-entraînement"
                st.metric("Index de Fatigue (Ratio kJ)", f"{ratio_kj:.2f}", delta=status)
            with col3:
                st.metric("Total Énergie (30j)", f"{int(kj_month_total)} kJ", f"~{int(kj_month_total)} kcal brûlées")

            # --- GRAPHIQUE DES KILOJOURS ---
            st.subheader("📈 Énergie produite par jour (kJ)")
            st.area_chart(df_daily.set_index('Date')['kJ'], color="#FC4C02")

            # --- PROMPT ADAPTÉ AUX kJ POUR GEMINI 2.5 ---
            st.markdown("---")
            st.subheader("📋 Analyse Énergétique & Plan de Séance")
            
            prompt_kj = f"""
            Tu es un entraîneur cycliste expert, spécialisé dans l'entraînement par le calcul du travail mécanique (Kilojoules) et de la puissance.
            
            Données de l'athlète :
            - FTP de référence : {FTP} Watts
            - Énergie totale produite ces 7 derniers jours : {int(kj_week)} kJ
            - Énergie moyenne produite par semaine ce mois-ci : {int(kj_week_avg_month)} kJ
            - Ratio de charge de travail actuel : {ratio_kj:.2f}
            - Historique quotidien des kJ sur 30 jours : {df_daily['kJ'].astype(int).tolist()}
            - Objectif : {NOM_COURSE} dans {JOURS_AVANT_COURSE} jours.

            MISSION :
            1. Analyse ma progression et ma fatigue en te basant strictly sur le volume de kJ accumulés (ex: est-ce que mes sorties deviennent plus denses en énergie ?).
            2. Prescris une séance structurée pour demain calibrée sur ma FTP ({FTP}W). Donne une estimation de la cible de kJ à atteindre pour cette séance.
               Rappel des zones de puissance : Z1 (<115W), Z2 (115-155W), Z3 (155-185W), Z4 (185-220W), Z5 (>220W).
            3. Donne une recommandation nutritionnelle précise en glucides (carbohydrates) pour compenser ou préparer cette charge en kJ.
            """
            
            try:
                response = model.generate_content(prompt_kj)
                st.success("Analyse Aixle kJ complétée")
                
                # Carte d'entraînement stylisée
                st.markdown(f"""
                <div style="background-color: #262730; padding: 25px; border-radius: 15px; border-left: 8px solid #FC4C02; color: white;">
                    {response.text.replace('##', '###')}
                </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Erreur Gemini : {e}")
        else:
            st.warning("Aucune activité trouvée. Vérifie tes connexions Strava.")

# --- FOOTER ---
st.sidebar.markdown("---")
st.sidebar.write("🦾 Base d'analyse : Kilojoules (kJ)")
st.sidebar.write(f"FTP configurée : {FTP} W")
