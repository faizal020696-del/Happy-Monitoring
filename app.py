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

    # Membersihkan nama kolom dari spasi berlebih
    df.columns = df.columns.str.strip()

    # Dataframe string untuk pencarian aman
    df_clean_text = df.fillna("").astype(str)

    # Membersihkan kolom angka (GMV / Target / Sales / CM / L3M, dll)
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['gmv', 'target', 'sales', 'value', 'amount', 'cm', 'l3m', 'lm']):
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r'[^0-9\.-]', '', regex=True), 
                errors='coerce'
            ).fillna(0)

    client = genai.Client(api_key=API_KEY)

    # Sidebar Debugging Info
    with st.sidebar:
        st.write("### 📊 Status Data")
        st.write(f"Total Baris: {len(df)}")
        st.write(f"Total Kolom: {len(df.columns)}")
        with st.expander("Lihat Daftar Kolom"):
            st.write(list(df.columns))

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

        # --- SISTEM KALKULASI PYTHON MUTLAK ---
        prompt_lower = prompt.lower()
        python_calculated_context = ""
        
        # Ambil semua kolom yang ada unsur GMV atau angka performa
        metric_columns = [col for col in df.columns if any(k in col.lower() for k in ['gmv', 'cm', 'sales', 'value', 'target', 'lm'])]
        
        target_names = ["mulyanto", "sulistiana", "gde", "rizki", "afrianto"]
        is_name_queried = False
        
        for name in target_names:
            if name in prompt_lower:
                is_name_queried = True
                mask = df_clean_text.apply(lambda row: row.str.lower().str.contains(name).any(), axis=1)
                sub_df = df[mask]
                
                if len(sub_df) > 0:
                    python_calculated_context += f"\n=== HASIL PERHITUNGAN MUTLAK PYTHON UNTUK '{name.upper()}' ===\n"
                    python_calculated_context += f"Jumlah baris data ditemukan: {len(sub_df)} baris\n"
                    for col in metric_columns:
                        total_val = sub_df[col].sum()
                        python_calculated_context += f"- {col}: {total_val:,.0f}\n"

        # Jika user tanya spesifik soal sales, kita JANGAN kasih lihat CSV mentah ke Gemini. 
        # Biar Gemini murni hanya membaca hasil hitungan Python di atas!
        if is_name_queried and python_calculated_context:
            system_prompt = f"""
Kamu adalah asisten analisis data profesional. 
Berikut adalah hasil kalkulasi data mutlak yang dihitung langsung oleh sistem database Python:

{python_calculated_context}

Tugasmu: Jawab pertanyaan user berdasarkan hasil kalkulasi Python di atas dengan format yang rapi, jelas, dan ramah dalam bahasa Indonesia. Jangan mengubah atau menebak angka di luar data tersebut.
"""
            content_to_send = f"{system_prompt}\nPertanyaan User: {prompt}"
        else:
            # Kalau pertanyaannya umum (bukan nyari sales tertentu), baru kirim CSV secara utuh
            data_str = df.to_head(50).to_csv(index=False) # Dibatasi 50 baris teratas biar aman
            system_prompt = f"""
Kamu adalah sistem database analitik. 
Berikut adalah sampel data spreadsheet:
{data_str}
Tugasmu: Jawab pertanyaan user secara akurat berdasarkan data di atas.
"""
            content_to_send = f"{system_prompt}\n\nPertanyaan User: {prompt}"

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menganalisis data..."):
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=content_to_send
                )
                st.markdown(response.text)
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
