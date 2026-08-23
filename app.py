import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import re

API_KEY = st.secrets["GEMINI_API_KEY"]
SHEET_URL = st.secrets["SHEET_URL"]

st.set_page_config(
    page_title="Chatbot Universe SPV Happy", 
    page_icon="🤖", 
    layout="centered"
)

# Kustomisasi Tampilan Visual
st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stApp { background-color: #f8fafc; }
    .main-header {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        padding: 2.5rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.2);
        margin-bottom: 2rem;
    }
    .main-header h1 { color: white !important; font-weight: 800; font-size: 2.2rem; margin-bottom: 0.5rem; }
    .main-header p { color: #e0e7ff !important; font-size: 1rem; margin: 0; }
    .stChatMessage { border-radius: 16px !important; padding: 1rem 1.2rem !important; margin-bottom: 0.8rem !important; }
    .stChatInputContainer { border-radius: 15px !important; bottom: 20px !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="main-header">
        <h1>🤖 Chatbot Universe SPV Happy</h1>
        <p>Tanyakan apa saja terkait data universe, performa sales, hingga status transaksi.</p>
    </div>
""", unsafe_allow_html=True)

# 1. OPTIMASI AKURASI: Caching & Cleaning Data
@st.cache_data(ttl=300)
def load_and_clean_data(url):
    sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if not sheet_id_match:
        return None
    sheet_id = sheet_id_match.group(1)
    gid_match = re.search(r'[#&?]gid=([0-9]+)', url)
    gid = gid_match.group(1) if gid_match else "0"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    df = pd.read_csv(csv_url)
    
    # Standarisasi & Pembersihan Teks
    df.columns = df.columns.astype(str).str.strip()  # Hapus spasi di nama kolom
    df = df.dropna(how="all")  # Hapus baris yang benar-benar kosong
    df = df.fillna("-")  # Ganti nilai NaN agar tidak membingungkan LLM
    
    return df

try:
    df = load_and_clean_data(SHEET_URL)
    client = genai.Client(api_key=API_KEY)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    if prompt := st.chat_input("Tanyakan sesuatu terkait data universe..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 2. METADATA & SYSTEM INSTRUCTION UNTUK AKURASI MAXIMAL
        total_rows = len(df)
        column_names = ", ".join(df.columns.tolist())
        data_csv = df.to_csv(index=False)

        system_instruction = f"""
        Kamu adalah validator data dan asisten monitoring profesional.
        
        METADATA DATASET:
        - Total Baris Data: {total_rows}
        - Daftar Kolom: [{column_names}]
        
        DATA LENGKAP (CSV):
        {data_csv}
        
        ATURAN KETAT AKURASI DATA:
        1. Jawab pertanyaan HANYA menggunakan informasi dari data CSV di atas.
        2. Bila melakukan perhitungan (penjumlahan, pencarian baris, hitung jumlah), hitung secara teliti dan persis sesuai baris data.
        3. DILARANG berasumsi, mengira-ngira, atau menggunakan pengetahuan di luar data ini.
        4. Jika data yang diminta TIDAK ADA di dalam CSV, jawab persis: "Maaf, data tersebut tidak ditemukan dalam sistem database."
        5. Selalu sebutkan rincian nama atau ID dari data yang kamu temukan agar mudah diverifikasi.
        """

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menganalisis data..."):
                # 3. TEMPERATURE 0.0 & SYSTEM CONFIG
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.0  # Menghapus halusinasi & jawaban acak
                    )
                )
                st.markdown(response.text)
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
