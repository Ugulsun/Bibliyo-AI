# src/auth.py
import streamlit as st
import json
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

# Sabitler
SCOPES = ['https://www.googleapis.com/auth/drive']
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
TOKEN_FILE = "token.json"

def check_app_password():
    """Uygulama kilidi."""
    if "auth_success" not in st.session_state:
        st.session_state.auth_success = False

    if not st.session_state.auth_success:
        st.markdown("## 🔒 Güvenlik Kilidi")
        pwd = st.text_input("Uygulama Şifresi:", type="password")
        if st.button("Giriş"):
            if "APP_PASSWORD" not in st.secrets:
                st.error("Secrets ayarı eksik! (APP_PASSWORD)")
                st.stop()
            if pwd == st.secrets["APP_PASSWORD"]:
                st.session_state.auth_success = True
                st.rerun()
            else:
                st.error("Yanlış şifre!")
        st.stop()

def get_google_creds():
    """Google OAuth Token Yönetimi."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except:
            os.remove(TOKEN_FILE)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            except:
                creds = None

    if not creds:
        if "oauth" not in st.secrets:
            st.error("Secrets içinde [oauth] ayarı bulunamadı!")
            st.stop()
            
        client_config = json.loads(st.secrets["oauth"]["CLIENT_CONFIG"])
        flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
        
        st.title("Google Bağlantısı")
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.markdown(f"1. [İzin Linki]({auth_url})")
        code = st.text_input("2. Google Kodunu Yapıştır:")
        
        if code:
            flow.fetch_token(code=code)
            creds = flow.credentials
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            st.rerun()
        st.stop()
        
    return creds
