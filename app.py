import streamlit as st
import pandas as pd
from google import genai
import re

# Mengambil data dari Secrets aman Streamlit
API_KEY = st.secrets["GEMINI_API_KEY"]
SHEET_URL = st.secrets["SHEET_URL"]

st.set_page_config(
    page_title="Chatbot Universe SPV Happy", 
    page_icon="🤖", 
    layout="centered"
)

# Kustomisasi Tampilan Visual (CSS Aman)
st.markdown("""
    <style>
    /* Sembunyikan elemen internal Streamlit yang bisa disembunyikan */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    
    /* Background Utama */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Header Container dengan Gradient */
    .main-header {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        padding: 2.5rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.2);
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white !important;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 0.5rem;
    }
    .main-header p {
        color: #e0e7ff !important;
        font-size: 1rem;
        margin: 0;
    }

    /* Kustomisasi Gelembung Chat */
    .stChatMessage {
        border-radius: 16px !important;
        padding: 1rem 1.2rem !important;
        margin-bottom: 0.8rem !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03) !important;
    }
    
    /* Input Chat di Bawah Diberi Space Agar Tidak Tertutup Badge */
    .stChatInputContainer {
        border-radius: 15px !important;
        bottom: 20px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Tampilan Header
st.markdown("""
    <div class="main-header">
        <h1>🤖 Chatbot Universe SPV Happy</h1>
        <p>Tanyakan apa saja terkait data universe kalian.</p>
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

    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    if prompt := st.chat_input("Tanyakan sesuatu terkait data universe..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # --- OPTIMASI ANGKA (MENGHINDARI HALUSINASI AI) ---
        # Mencari tahu kolom mana yang berupa angka untuk dibantu hitung via Pandas
        numeric_summary = ""
        prompt_lower = prompt.lower()
        
        if any(keyword in prompt_lower for keyword in ["total", "jumlah", "rata-rata", "sum", "average", "gmv"]):
            # Coba cari kolom numerik secara otomatis
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                calc_results = []
                for col in numeric_cols:
                    total_val = df[col].sum()
                    mean_val = df[col].mean()
                    calc_results.append(f"- Kolom '{col} -> Total: {total_val:,.2f}, Rata-rata: {mean_val:,.2f}")
                numeric_summary = "\n[HASIL PERHITUNGAN PYTHON RESMI - GUNAKAN ANGKA INI JIKA DITANYAKAN TOTAL/RATA-RATA]:\n" + "\n".join(calc_results)

        data_str = df.to_csv(index=False)
        system_prompt = f"""
Kamu adalah sistem database analitik yang presisi tinggi. Saat user meminta detail atau total angka, dilarang melakukan estimasi atau tebakan matematis sendiri. Tarik datanya secara mentah dari baris yang sesuai atau gunakan hasil kalkulasi Python yang sudah disediakan di bawah jika relevan.

Berikut adalah data terbaru dalam format CSV:
{data_str}

{numeric_summary}

Tugasmu: Jawab pertanyaan user secara akurat HANYA berdasarkan data dan kalkulasi di atas dalam bahasa Indonesia yang rapi, profesional, dan komunikatif.
"""

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menganalisis data..."):
                response = client.models.generate_content(
                    model='gemini-2.5-flash',  # Menggunakan versi model flash yang stabil
                    contents=f"{system_prompt}\n\nPertanyaan User: {prompt}"
                )
                st.markdown(response.text)
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
