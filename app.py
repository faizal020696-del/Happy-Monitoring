import streamlit as st
import pandas as pd
from google import genai
import re

# Mengambil data dari Secrets aman Streamlit
API_KEY = st.secrets["GEMINI_API_KEY"]
SHEET_URL = st.secrets["SHEET_URL"]

# Konfigurasi Halaman & Icon
st.set_page_config(
    page_title="Chatbot Universe SPV Happy", 
    page_icon="🌌", 
    layout="centered"
)

# Kustomisasi Tampilan Visual (Tema Deep Space Glassmorphism)
st.markdown("""
    <style>
    /* Sembunyikan elemen internal Streamlit */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stAppHeader {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    
    /* Background Utama */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
        background-attachment: fixed;
    }
    
    /* Header Container */
    .main-header {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 2.5rem 2rem;
        border-radius: 24px;
        color: white;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 15px 35px rgba(0,0,0,0.2);
        margin-bottom: 2.5rem;
    }
    .main-header h1 {
        color: #60a5fa !important;
        font-weight: 800;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 10px rgba(96, 165, 250, 0.3);
    }
    .main-header p {
        color: #cbd5e1 !important;
        font-size: 1.1rem;
        margin: 0;
        opacity: 0.9;
    }

    /* Kustomisasi Gelembung Chat */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border-radius: 18px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        padding: 1.2rem !important;
        margin-bottom: 1rem !important;
        color: #e2e8f0 !important;
    }
    
    .stChatMessage[data-testid="stChatMessageUser"] {
        background: rgba(59, 130, 246, 0.1) !important;
        border: 1px solid rgba(59, 130, 246, 0.2) !important;
    }

    /* Input Chat di Bawah */
    .stChatInputContainer {
        border-radius: 20px !important;
        bottom: 30px !important;
        background: rgba(255, 255, 255, 0.07) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        box-shadow: 0 -10px 25px rgba(0,0,0,0.1) !important;
    }
    .stChatInputContainer input {
        color: white !important;
    }
    
    .stSpinner i {
        color: #60a5fa !important;
    }
    </style>
""", unsafe_allow_html=True)

# Tampilan Header
st.markdown("""
    <div class="main-header">
        <h1>🌌 Chatbot Universe SPV Happy</h1>
        <p>Asisten AI cerdas untuk analisis data universe, sales, dan transaksi Anda.</p>
    </div>
""", unsafe_allow_html=True)

def convert_to_csv_url(url):
    sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if not sheet_id_match:
        return None
    sheet_id = sheet_id_match.group(1)
    gid_match = re.search(r'[#&?]gid=([0-9]+)', url)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

try:
    csv_url = convert_to_csv_url(SHEET_URL)
    df = pd.read_csv(csv_url)

    client = genai.Client(api_key=API_KEY)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Tampilkan Riwayat Chat
    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # Input Chat User
    if prompt := st.chat_input("Tanyakan sesuatu tentang data universe..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        data_str = df.to_csv(index=False)
        system_prompt = f"""
        Kamu adalah Asisten AI Profesional untuk SPV Happy. Tugasmu adalah menganalisis data Universe.
        Jawablah pertanyaan user dengan sopan, akurat, dan ringkas HANYA berdasarkan data CSV berikut:
        
        {data_str}
        
        Gunakan Bahasa Indonesia yang baik dan komunikatif.
        """

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menganalisis data universe..."):
                try:
                    # DIUBAH KE gemini-2.5-flash AGAR KUOTA JAUH LEBIH BANYAK
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=f"{system_prompt}\n\nPertanyaan User: {prompt}"
                    )
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as api_err:
                    st.error(f"Gagal memproses request AI: {api_err}")

except Exception as e:
    st.error(f"Gagal memuat data. Pastikan Link Google Sheets valid. Error: {e}")
