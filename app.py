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

# Kustomisasi Tampilan Visual Total (Tema Deep Space Glassmorphism)
st.markdown("""
    <style>
    /* 1. Menghilangkan elemen internal Streamlit agar bersih */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stAppHeader {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    
    /* 2. BACKGROUND UTAMA: Deep Space Gradient */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
        background-attachment: fixed;
    }
    
    /* 3. HEADER CONTAINER: Futuristik & Terang */
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
        color: #60a5fa !important; /* Biru muda cerah */
        font-weight: 800;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 10px rgba(96, 165, 250, 0.3);
    }
    .main-header p {
        color: #cbd5e1 !important; /* Abu-abu terang */
        font-size: 1.1rem;
        margin: 0;
        opacity: 0.9;
    }

    /* 4. KUSTOMISASI GELEMBUNG CHAT: Glassmorphism */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border-radius: 18px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        padding: 1.2rem !important;
        margin-bottom: 1rem !important;
        color: #e2e8f0 !important; /* Teks chat abu-abu sangat terang */
    }
    
    /* Warna teks khusus untuk user agar beda */
    .stChatMessage[data-testid="stChatMessageUser"] {
        background: rgba(59, 130, 246, 0.1) !important; /* Sedikit sentuhan biru */
        border: 1px solid rgba(59, 130, 246, 0.2) !important;
    }

    /* 5. INPUT CHAT DI BAWAH: Diangkat & Dipercantik */
    .stChatInputContainer {
        border-radius: 20px !important;
        bottom: 30px !important; /* Jarak aman dari badge bawah */
        background: rgba(255, 255, 255, 0.07) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        box-shadow: 0 -10px 25px rgba(0,0,0,0.1) !important;
    }
    .stChatInputContainer input {
        color: white !important;
    }
    
    /* Warna Spinner Loading */
    .stSpinner i {
        color: #60a5fa !important;
    }
    </style>
""", unsafe_allow_html=True)

# Tampilan Header Tema Baru
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

    # Chat history dengan avatar modern
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
        # Prompt sistem yang lebih profesional
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
    st.error(f"Gagal memuat data. Pastikan Link Google Sheets valid dan Public. Error: {e}")
