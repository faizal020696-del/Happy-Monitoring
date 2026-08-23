import streamlit as st
import pandas as pd
from groq import Groq
import re

# Mengambil data dari Secrets aman Streamlit
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
SHEET_URL = st.secrets["SHEET_URL"]

# Konfigurasi Halaman & Icon
st.set_page_config(
    page_title="Chatbot Universe SPV Happy", 
    page_icon="🌌", 
    layout="centered"
)

# Kustomisasi Tampilan Visual Presisi (Tema Deep Space Dark Mode)
st.markdown("""
    <style>
    /* 1. Menghilangkan header & footer bawaan Streamlit */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stAppHeader {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    
    /* 2. BACKGROUND UTAMA: Dark Blue Navy solid/gradient halus */
    .stApp {
        background: #0d1527 !important;
        background-attachment: fixed;
    }
    
    /* 3. HEADER CONTAINER: Box Gelap Terang Elegan */
    .main-header {
        background: #172238;
        padding: 2.5rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: #60a5fa !important;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 0.8rem;
    }
    .main-header p {
        color: #94a3b8 !important;
        font-size: 1rem;
        margin: 0;
    }

    /* 4. GELEMBUNG CHAT: Dark Container */
    .stChatMessage {
        background: #172238 !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        padding: 1rem 1.2rem !important;
        margin-bottom: 1rem !important;
        color: #f1f5f9 !important;
    }
    
    .stChatMessage[data-testid="stChatMessageUser"] {
        background: #1e2d4a !important;
        border: 1px solid rgba(96, 165, 250, 0.2) !important;
    }

    /* 5. INPUT CHAT DI BAWAH & TEKS INPUT KETIK JELAS */
    .stChatInputContainer {
        border-radius: 16px !important;
        bottom: 25px !important;
        background: #172238 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Perbaikan Teks saat diketik agar terang & jelas */
    .stChatInputContainer textarea {
        color: #ffffff !important;
        background-color: transparent !important;
    }
    
    /* Loading Spinner */
    .stSpinner i {
        color: #60a5fa !important;
    }
    </style>
""", unsafe_allow_html=True)

# Tampilan Header Sesuai Gambar
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

    # Inisialisasi Client Groq
    client = Groq(api_key=GROQ_API_KEY)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Chat history
    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # Input Chat
    if prompt := st.chat_input("Tanyakan sesuatu tentang data universe..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        data_str = df.to_csv(index=False)
        system_prompt = f"""
        Kamu adalah Asisten AI Profesional untuk SPV Happy. Tugasmu adalah menganalisis data Universe.
        Jawablah pertanyaan user dengan sopan, akurat, dan ringkas HANYA berdasarkan data CSV berikut:
        
        {data_str}
        
        Gunakan Bahasa Indonesia yang baik dan komunikatif. Jika data tidak ditemukan, sampaikan dengan jujur.
        """

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menganalisis data universe..."):
                try:
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        model="llama-3.3-70b-versatile",
                    )
                    
                    response_text = chat_completion.choices[0].message.content
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})

                except Exception as api_err:
                    st.error(f"Gagal memproses AI Groq: {api_err}")

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
