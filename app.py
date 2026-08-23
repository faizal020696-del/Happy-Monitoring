import streamlit as st
import pandas as pd
from google import genai
import re

API_KEY = st.secrets["GEMINI_API_KEY"]
SHEET_URL = st.secrets["SHEET_URL"]

st.set_page_config(
    page_title="Chatbot Universe SPV Happy", 
    page_icon="🤖", 
    layout="centered"
)

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

    # --- PEMBERSIHAN KOLOM ANGKA SECARA TOTAL ---
    # Mengubah semua kolom yang ada kata 'gmv' atau 'sales' menjadi angka murni
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['gmv', 'target', 'sales', 'value', 'amount']):
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r'[^0-9\.-]', '', regex=True), 
                errors='coerce'
            ).fillna(0)

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

        # --- LOGIKA PENCARIAN CERDAS (PYTHON-POWERED) ---
        # Jika user menyebutkan nama sales atau kata kunci total, Python yang hitung duluan!
        prompt_lower = prompt.lower()
        python_calculated_context = ""
        
        # Cari kolom nama sales / rep / spv secara otomatis
        rep_column = next((col for col in df.columns if any(k in col.lower() for k in ['rep', 'sales', 'nama', 'spv', 'pic'])), None)
        gmv_column = next((col for col in df.columns if 'gmv' in col.lower()), None)

        if rep_column and gmv_column:
            # Cek sales siapa yang dipanggil di chat (misal: Mulyanto, Gde, dll)
            # Kita ambil unik nilai dari kolom rep untuk dicocokkan dengan pertanyaan user
            unique_reps = df[rep_column].dropna().astype(str).unique()
            for rep in unique_reps:
                if rep.lower() in prompt_lower:
                    # Filter dataframe khusus sales tersebut
                    sub_df = df[df[rep_column].astype(str).str.lower() == rep.lower()]
                    total_gmv_exact = sub_df[gmv_column].sum()
                    python_calculated_context += f"\n[HASIL KALKULASI PYTHON RESMI UNTUK '{rep}']: Total baris data: {len(sub_df)} baris. Total GMV mutlak: {total_gmv_exact:,.0f}\n"

        # Jika user minta total keseluruhan GMV
        if "total" in prompt_lower and gmv_column and not python_calculated_context:
            grand_total = df[gmv_column].sum()
            python_calculated_context += f"\n[HASIL KALKULASI PYTHON RESMI KESELURUHAN]: Total GMV seluruh data adalah: {grand_total:,.0f}\n"

        data_str = df.to_csv(index=False)
        system_prompt = f"""
Kamu adalah sistem database analitik yang sangat akurat. 
ATURAN UTAMA: Jika ada blok [HASIL KALKULASI PYTHON RESMI] di bawah ini, KAMU WAJIB MEMAKAI ANGKA TERSEBUT SECARA MUTLAK. Dilarang menghitung ulang atau mengubah angka tersebut!

Berikut adalah daftar kolom: {list(df.columns)}

{python_calculated_context}

Berikut adalah data keseluruhan dalam format CSV:
{data_str}

Tugasmu: Jawab pertanyaan user secara akurat dan profesional berdasarkan data dan hasil kalkulasi Python di atas.
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
