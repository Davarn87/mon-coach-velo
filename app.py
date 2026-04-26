import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import google.generativeai as genai

# --- CONFIGURATION API (Via Streamlit Secrets) ---
# En production, ces valeurs sont dans le menu "Secrets" de Streamlit
INTERVALS_ID = st.secrets.get("INTERVALS_ID", "TON_ID")
INTERVALS_KEY = st.secrets.get("INTERVALS_KEY", "TA_CLE_API")
GEMINI_KEY = st.secrets.get("GEMINI_KEY", "TA_CLE_GEMINI")

# Configuration de Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

# --- FONCTION : RÉCUPÉRER LA DERNIÈRE SÉANCE RÉELLE ---
def get_last_activity():
    # On définit une date de départ très ancienne (2000-01-01) pour être sûr de trouver
    url = f"https://intervals.icu/api/v1/athlete/{INTERVALS_ID}/activities?limit=1&oldest=2000-01-01"
    
    response = requests.get(url, auth=('athlete', INTERVALS_KEY))
    
    if response.status_code == 200:
        data = response.json()
        if data: # On vérifie que la liste n'est pas vide
            return data[0]
        return None
    else:
        st.error(f"Erreur API : Code {response.status_code}")
        st.write(response.text)
        return None

# --- FONCTION : ANALYSE IA PAR GEMINI ---
def get_ia_feedback(activity_data, profil):
    prompt = f"""
    En tant que coach cycliste expert, analyse cette séance :
    - Nom : {activity_data.get('name')}
    - Charge (TSS) : {activity_data.get('icu_training_load')}
    - Puissance Moyenne : {activity_data.get('average_watts')}W
    - Fréquence Cardiaque Moyenne : {activity_data.get('average_heartrate')} bpm
    - Profil athlète : {profil['niveau']}, poids {profil['poids']}kg.
    
    Donne un feedback court (3 phrases), motivant et technique sur la qualité du travail.
    """
    response = model.generate_content(prompt)
    return response.text

# --- INTERFACE ---
st.title("🤖 Coach Autonome Gemini")

if st.button("🔄 Synchroniser et Analyser ma dernière sortie"):
    with st.spinner("Gemini analyse tes watts..."):
        activity = get_last_activity()
        
        if activity:
            st.markdown('<div class="tile-container">', unsafe_allow_html=True)
            st.subheader(f"📊 Analyse de : {activity['name']}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Watts Moy.", f"{activity['average_watts']}W")
            c2.metric("TSS", activity['icu_training_load'])
            c3.metric("Rendement (EF)", activity.get('efficiency_factor', 'N/A'))
            
            # Appel à l'IA
            feedback = get_ia_feedback(activity, st.session_state.profil)
            
            st.markdown("---")
            st.markdown(f"**💬 Le mot du Coach Gemini :**")
            st.write(feedback)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("Impossible de récupérer les données d'Intervals.icu. Vérifie tes clés API.")
