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

# Kustomisasi Tampilan Visual (Tema Light Mode Clean)
st.markdown("""
    <style>
    /* 1. Menghilangkan elemen internal Streamlit */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stAppHeader {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    
    /* 2. BACKGROUND UTAMA: Putih Bersih */
    .stApp {
        background-color: #ffffff !important;
    }
    
    /* 3. HEADER CONTAINER: Gelap Elegan agar Menjolok di Background Putih */
    .main-header {
        background: #0f172a;
        padding: 2.5rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.15);
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

    /* 4. GELEMBUNG CHAT: Teks Gelap Kontras di Background Terang */
    .stChatMessage {
        background: #f8fafc !important;
        border-radius: 16px !important;
        border: 1px solid #e2e8f0 !important;
        padding: 1rem 1.2rem !important;
        margin-bottom: 1rem !important;
        color: #0f172a !important;
    }
    
    .stChatMessage[data-testid="stChatMessageUser"] {
        background: #eff6ff !important;
        border: 1px solid #bfdbfe !important;
    }

    /* 5. INPUT CHAT DI BAWAH */
    .stChatInputContainer {
        border-radius: 16px !important;
        bottom: 25px !important;
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
    }
    
    .stChatInputContainer textarea {
        color: #0f172a !important;
    }
    
    /* Loading Spinner */
    .stSpinner i {
        color: #2563eb !important;
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
                        model="llama3-70b-8192",
                    )
                    
                    response_text = chat_completion.choices[0].message.content
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})

                except Exception as api_err:
                    st.error(f"Gagal memproses AI Groq: {api_err}")

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
