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

# Kustomisasi Tampilan Visual Light Mode
st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stAppHeader {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    .stApp { background-color: #ffffff !important; }
    
    .main-header {
        background: #0f172a;
        padding: 2.5rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.15);
        margin-bottom: 2rem;
    }
    .main-header h1 { color: #60a5fa !important; font-weight: 800; font-size: 2.2rem; margin-bottom: 0.8rem; }
    .main-header p { color: #94a3b8 !important; font-size: 1rem; margin: 0; }

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
    .stChatInputContainer textarea { color: #0f172a !important; }
    .stSpinner i { color: #2563eb !important; }
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

        # SOLUSI: Deteksi Sapaan Ringan vs Pertanyaan Data
        common_greetings = ["hi", "halo", "hello", "pagi", "siang", "malam", "ping", "tes", "test", "terima kasih", "makasih"]
        is_greeting = prompt.strip().lower() in common_greetings

        if is_greeting:
            system_prompt = "Kamu adalah Asisten AI Profesional untuk SPV Happy. Sapa balik user dengan sopan, ramah, dan informasikan bahwa kamu siap membantu menganalisis data Universe."
        else:
            # Cari baris yang relevan dengan keyword user
            keywords = prompt.lower().split()
            mask = df.astype(str).apply(lambda row: row.str.lower().str.contains('|'.join(keywords)).any(), axis=1)
            filtered_df = df[mask]

            # Ambil maksimal 15 baris sampel agar token tetap kecil
            if len(filtered_df) == 0:
                sample_data = df.head(10).to_csv(index=False)
            else:
                sample_data = filtered_df.head(15).to_csv(index=False)

            system_prompt = f"""
            Kamu adalah Asisten AI Profesional untuk SPV Happy.
            Informasi Ringkas Data:
            - Total Baris: {len(df)}
            - Nama Kolom: {list(df.columns)}
            - Sampel Data Terkait:
            {sample_data}

            Jawab pertanyaan user berdasarkan sampel data di atas dengan sopan dan singkat.
            """

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Memproses respon..."):
                try:
                    available_models = client.models.list()
                    active_model_ids = [m.id for m in available_models.data if hasattr(m, 'id')]

                    if not active_model_ids:
                        st.error("Tidak ada model AI yang ditemukan di akun Groq kamu.")
                    else:
                        response_text = None
                        last_err = None
                        
                        for model_id in active_model_ids:
                            try:
                                chat_completion = client.chat.completions.create(
                                    messages=[
                                        {"role": "system", "content": system_prompt},
                                        {"role": "user", "content": prompt}
                                    ],
                                    model=model_id,
                                    max_tokens=500
                                )
                                response_text = chat_completion.choices[0].message.content
                                break
                            except Exception as e:
                                last_err = e
                                continue

                        if response_text:
                            st.markdown(response_text)
                            st.session_state.messages.append({"role": "assistant", "content": response_text})
                        else:
                            st.error(f"Gagal memproses AI Groq: {last_err}")

                except Exception as api_err:
                    st.error(f"Gagal mengambil daftar model Groq: {api_err}")

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
