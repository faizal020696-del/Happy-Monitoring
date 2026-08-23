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

    df.columns = df.columns.str.strip()
    df_clean_text = df.fillna("").astype(str)

    # Membersihkan kolom angka agar bisa dihitung totalnya
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['gmv', 'target', 'sales', 'value', 'amount', 'cm', 'lm', 'l3m']):
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.replace(r'[^0-9\.-]', '', regex=True), 
                errors='coerce'
            ).fillna(0)

    client = genai.Client(api_key=API_KEY)

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

        prompt_lower = prompt.lower()
        
        # PENCARIAN UNIVERSAL: Mendeteksi kata penting dari pertanyaan user (mengabaikan kata tanya umum)
        stop_words = ['berapa', 'data', 'untuk', 'bulan', 'ini', 'kemarin', '1', '2', '3', 'di', 'dan', 'yang', 'dari', 'tentang']
        keywords = [word for word in prompt_lower.split() if word not in stop_words and len(word) > 2]
        
        python_summary_text = None
        sub_df = pd.DataFrame()

        # Mencari baris di dataframe yang mengandung kata kunci dari user
        if keywords:
            mask = pd.Series([False] * len(df))
            for kw in keywords:
                mask = mask | df_clean_text.apply(lambda row: row.str.lower().str.contains(kw).any(), axis=1)
            sub_df = df[mask]

        if len(sub_df) > 0:
            # Jika data ditemukan, hitung metrik angka yang relevan
            valid_metric_cols = [col for col in df.columns if any(k in col.lower() for k in ['gmv', 'cm', 'lm']) and not any(x in col.lower() for x in ['code', 'assignment'])]
            
            summary_lines = [f"Ditemukan {len(sub_df)} baris data terkait kata kunci '{prompt}':"]
            
            for col in valid_metric_cols:
                total_val = sub_df[col].sum()
                if total_val > 0:
                    summary_lines.append(f"- {col}: Rp {total_val:,.0f}")
            
            python_summary_text = "\n".join(summary_lines)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menganalisis data..."):
                if python_summary_text:
                    formatting_prompt = f"""
Kamu adalah asisten AI analitik yang ramah, profesional, dan to the point.
Berikut adalah data angka valid yang sudah dihitung secara mutlak oleh sistem berdasarkan pencarian kata kunci user:

{python_summary_text}

Tugasmu: Jawab pertanyaan user ({prompt}) dengan gaya bahasa yang mengalir natural.
Struktur jawaban yang diinginkan:
1. Jawab langsung ke inti pertanyaan di kalimat pertama (sebutkan angka atau total yang ditanyakan user secara spesifik).
2. Tambahkan **1-2 kalimat ringkasan (summary/analisis singkat)** di bawahnya untuk menyimpulkan data tersebut secara manusiawi.
3. Jangan menampilkan rincian metrik lain yang tidak berhubungan agar tetap *clean*.

ATURAN MUTLAK: Jangan mengubah angka atau nominal Rupiah yang ada di dalam data di atas sedikit pun!
"""
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=formatting_prompt
                    )
                    response_text = response.text
                else:
                    # Jika data benar-benar tidak ada sama sekali di file CSV
                    response_text = f"Maaf bro, setelah dicek di dalam database/spreadsheet, data untuk '{prompt}' tidak ditemukan atau tidak tercatat."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
