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
    .stChatMessage { border-radius: 16px !important; padding: 1rem 1.2rem !important; margin-bottom: 0.8rem !important; box-shadow: 0 2px 5px rgba(0,0,0,0.03) !important; }
    .stChatInputContainer { border-radius: 15px !important; bottom: 20px !important; }
    </style>
""", unsafe_allow_html=True)

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

    # --- PEMBERSIHAN KOLOM ANGKA YANG AMAN ---
    for col in df.columns:
        if 'gmv' in col.lower() or 'target' in col.lower() or 'sales' in col.lower():
            # Ubah dulu jadi string, buang karakter non-digit (seperti titik, koma, huruf, atau simbol mata uang)
            df[col] = (
                df[col].astype(str)
                .str.replace(r'[^0-9]', '', regex=True)
            )
            # Kosongkan string kosong, lalu ubah ke tipe angka (Numeric)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

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

        # --- LOGIKA PENCARIAN & KALKULASI PYTHON SPESIFIK ---
        filtered_context = ""
        prompt_lower = prompt.lower()
        
        sales_names = ["sulistiana", "gde", "rizki", "mulyanto", "afrianto"]
        matched_sales = [name for name in sales_names if name in prompt_lower]
        
        if matched_sales:
            rep_col = next((col for col in df.columns if 'rep' in col.lower() or 'sales' in col.lower() or 'nama' in col.lower()), None)
            gmv_col = next((col for col in df.columns if 'gmv' in col.lower()), None)
            
            if rep_col and gmv_col:
                for name in matched_sales:
                    sub_df = df[df[rep_col].astype(str).str.lower().str.contains(name)]
                    exact_sum = sub_df[gmv_col].sum()
                    filtered_context += f"\n[DATA VALID PYTHON UNTUK {name.upper()}]: Total baris ditemukan: {len(sub_df)} baris. Total GMV pasti: {int(exact_sum):,}\n"

        data_str = df.to_csv(index=False)
        system_prompt = f"""
Kamu adalah sistem database analitik yang sangat akurat. Dilarang menebak angka. 
Jika ada bagian [DATA VALID PYTHON] di bawah ini, KAMU WAJIB MENGGUNAKAN ANGKA TERSEBUT SECARA MUTLAK untuk menjawab pertanyaan user.

Berikut adalah data keseluruhan dalam format CSV:
{data_str}

{filtered_context}

Tugasmu: Jawab pertanyaan user secara akurat berdasarkan data dan hasil kalkulasi Python di atas dalam bahasa Indonesia yang rapi dan profesional.
"""

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menganalisis data..."):
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=f"{system_prompt}\n\nPertanyaan User: {prompt}"
                )
                st.markdown(response.text)
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
