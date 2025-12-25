# src/main.py
import streamlit as st
import json
import time
from datetime import datetime
from pypdf import PdfReader
from docx import Document

# Kendi modüllerimizi çağırıyoruz
from auth import check_app_password, get_google_creds
from drive_manager import DriveManager
import google.genai as genai # AI motoru şimdilik burada kalsın

# --- AYARLAR ---
st.set_page_config(page_title="Bibliyo-AI", page_icon="📚", layout="wide")
ANA_KLASOR = "Bibliyo-AI_Projeler"

# --- YARDIMCI FONKSİYONLAR ---
def metni_parcala(metin):
    return [p.strip() for p in metin.split('\n\n') if p.strip()]

def ai_cevir(metin, api_key, talimatlar, hafiza):
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"GÖREV: Çeviri\nTALİMAT: {talimatlar}\nHAFIZA: {hafiza}\nMETİN: {metin}"
        res = client.models.generate_content(model="gemini-2.5-pro", contents=prompt)
        return res.text.strip()
    except Exception as e: return f"Hata: {str(e)}"

# --- AKIŞ ---
check_app_password()
creds = get_google_creds()
dm = DriveManager(creds)
ana_id = dm.get_or_create_folder(ANA_KLASOR)

# --- SIDEBAR ---
with st.sidebar:
    st.header("Bibliyo-AI 1.0")
    api_key = st.text_input("Gemini API Key", type="password")
    if st.button("Projeleri Yenile"):
        st.session_state.aktif_proje_id = None
        st.rerun()

if "aktif_proje_id" not in st.session_state:
    st.session_state.aktif_proje_id = None

# --- EKRAN 1: LİSTE ---
if st.session_state.aktif_proje_id is None:
    st.title("📚 Kitaplığım")
    tab1, tab2 = st.tabs(["Projeler", "Yeni Kitap Ekle"])
    
    with tab1:
        projeler = dm.list_files(ana_id)
        # Sadece klasör olanları filtrele
        projeler = [p for p in projeler if p['mimeType'] == 'application/vnd.google-apps.folder']
        
        if not projeler: st.info("Kütüphane boş.")
        
        for p in projeler:
            if st.button(f"📖 {p['name']}", key=p['id']):
                st.session_state.aktif_proje_id = p['id']
                st.session_state.aktif_proje_adi = p['name']
                st.rerun()

    with tab2:
        ad = st.text_input("Kitap Adı")
        dosya = st.file_uploader("Dosya", type=['pdf', 'docx', 'txt'])
        
        if st.button("Başlat") and ad and dosya:
            with st.spinner("Kitap rafa yerleştiriliyor..."):
                p_id = dm.get_or_create_folder(ad, ana_id)
                
                # Metin Okuma
                if dosya.name.endswith('.pdf'): txt = "".join([p.extract_text() for p in PdfReader(dosya).pages])
                elif dosya.name.endswith('.docx'): txt = "\n\n".join([p.text for p in Document(dosya).paragraphs])
                else: txt = dosya.read().decode('utf-8')
                
                # Dosyaları Oluştur
                dm.upload_file(p_id, "TALIMATLAR.txt", "Akademik ve akıcı çevir.", "text/plain")
                dm.upload_file(p_id, "OGRENDIKLERIM.txt", "Henüz veri yok.", "text/plain")
                
                db = {"meta": {"ad": ad}, "paragraflar": [{"id": i, "orjinal": p, "ceviri": "", "durum": "bekliyor"} for i, p in enumerate(metni_parcala(txt))]}
                dm.upload_file(p_id, "veritabani.json", json.dumps(db), "application/json")
                
                st.success("Hazır!")
                time.sleep(1); st.rerun()

# --- EKRAN 2: ÇALIŞMA MASASI ---
else:
    pid = st.session_state.aktif_proje_id
    st.header(f"✍️ {st.session_state.aktif_proje_adi}")
    
    # Verileri Çek
    files = dm.list_files(pid)
    db_id = next((f['id'] for f in files if f['name'] == 'veritabani.json'), None)
    talimat_id = next((f['id'] for f in files if f['name'] == 'TALIMATLAR.txt'), None)
    hafiza_id = next((f['id'] for f in files if f['name'] == 'OGRENDIKLERIM.txt'), None)
    
    if db_id:
        db = json.loads(dm.read_file(db_id))
        talimatlar = dm.read_file(talimat_id) if talimat_id else ""
        hafiza = dm.read_file(hafiza_id) if hafiza_id else ""
        
        # --- Editör Kısmı (Basitleştirilmiş) ---
        if "cursor" not in st.session_state: st.session_state.cursor = 0
        idx = st.session_state.cursor
        paragraf = db['paragraflar'][idx]
        
        c1, c2 = st.columns(2)
        c1.info(paragraf['orjinal'])
        
        if c2.button("🤖 Çevir") and api_key:
            paragraf['ceviri'] = ai_cevir(paragraf['orjinal'], api_key, talimatlar, hafiza)
            st.rerun()
            
        yeni = c2.text_area("Çeviri", paragraf['ceviri'], height=200)
        
        if c2.button("Kaydet"):
            paragraf['ceviri'] = yeni
            paragraf['durum'] = "onaylandi"
            dm.upload_file(pid, "veritabani.json", json.dumps(db), "application/json")
            
            if idx < len(db['paragraflar']) - 1: st.session_state.cursor += 1
            st.success("Kaydedildi")
            st.rerun()
            
        # Navigasyon
        if st.button("Sonraki >>"):
             if idx < len(db['paragraflar']) - 1: st.session_state.cursor += 1; st.rerun()
    else:
        st.error("Veritabanı dosyası bulunamadı!")
