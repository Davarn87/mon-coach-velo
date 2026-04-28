import streamlit as st
import requests

# Remplace par TES vrais identifiants Strava (ceux de ton dashboard API)
MY_CLIENT_ID = "193233"
MY_CLIENT_SECRET = "fc51721655e63a69a49aeba6f0287b54e29ed410"

st.title("🔑 Strava Token Generator")

# Étape 1 : Lien d'autorisation
url_auth = f"https://www.strava.com/oauth/authorize?client_id={MY_CLIENT_ID}&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=read,activity:read_all"

st.markdown(f"### [1. Clique ici pour autoriser Strava]({url_auth})")

# Étape 2 : Saisie du code reçu
st.write("---")
code_recu = st.text_input("2. Colle ici le 'code' qui apparaît dans l'URL de la page d'erreur après avoir cliqué sur autoriser :")

if code_recu:
    if "code=" in code_recu: # Au cas où tu colles toute l'URL
        code_recu = code_recu.split("code=")[1].split("&")[0]
        
    payload = {
        'client_id': MY_CLIENT_ID,
        'client_secret': MY_CLIENT_SECRET,
        'code': code_recu,
        'grant_type': 'authorization_code'
    }
    
    res = requests.post("https://www.strava.com/oauth/token", data=payload)
    
    if res.status_code == 200:
        data = res.json()
        st.success("✅ Bravo ! Voici tes jetons :")
        st.code(f"REFRESH_TOKEN = {data['refresh_token']}")
        st.write("Copie ce 'refresh_token' et mets-le dans tes Secrets Streamlit.")
    else:
        st.error(f"Erreur : {res.text}")
