import streamlit as st
import pandas as pd
from groq import Groq
import re

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
SHEET_URL = st.secrets["SHEET_URL"]

st.set_page_config(
    page_title="Chatbot Universe SPV Happy", 
    page_icon="🌌", 
    layout="centered"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stAppHeader {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    
    .stApp {
        background-color: #ffffff !important;
    }
    
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
    
    .stSpinner i {
        color: #2563eb !important;
    }
    </style>
""", unsafe_allow_html=True)

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

    client = Groq(api_key=GROQ_API_KEY)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    if prompt := st.chat_input("Tanyakan sesuatu tentang data universe..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # OPTIMASI TEKS CSV: Ambil maksimal 500 baris terbaru agar tidak Error 413
        df_limited = df.tail(500) 
        data_str = df_limited.to_csv(index=False)

        system_prompt = f"""
        Kamu adalah Asisten AI Profesional untuk SPV Happy. Tugasmu adalah menganalisis data Universe.
        Jawablah pertanyaan user dengan sopan, akurat, dan ringkas HANYA berdasarkan data CSV berikut:
        
        {data_str}
        
        Gunakan Bahasa Indonesia yang baik dan komunikatif. Jika data tidak ditemukan, sampaikan dengan jujur.
        """

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menganalisis data universe..."):
                models_to_try = [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-8b-instant"
                ]
                
                response_text = None
                last_error = None

                for model_name in models_to_try:
                    try:
                        chat_completion = client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": prompt}
                            ],
                            model=model_name,
                        )
                        response_text = chat_completion.choices[0].message.content
                        break
                    except Exception as err:
                        last_error = err
                        continue

                if response_text:
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                else:
                    st.error(f"Gagal memproses AI Groq: {last_error}")

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
