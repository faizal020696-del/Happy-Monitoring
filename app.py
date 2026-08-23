import streamlit as st
import pandas as pd
from openai import OpenAI
import time
import re

# Mengambil data dari Secrets aman Streamlit
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
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

    # Pembersihan kolom angka yang aman dari error tipe data
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['gmv', 'target', 'sales', 'value', 'amount', 'cm', 'lm', 'l3m', 'misi', 'gold']):
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace('.', '', regex=False)
                                   .str.replace(',', '.', regex=False)
                                   .str.replace(r'[^0-9\.-]', '', regex=True), 
                errors='coerce'
            ).fillna(0)

    # Inisialisasi Client OpenRouter (menggunakan base_url OpenAI)
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

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
        
        ignore_words = ['berapa', 'data', 'untuk', 'bulan', 'ini', 'kemarin', 'di', 'dan', 'yang', 'dari', 'tentang', 'pencapaian', 'capaian', 'misi', 'gold', 'gmv']
        filtered_words = [word for word in prompt_lower.split() if word not in ignore_words and len(word) > 2]
        
        python_summary_text = None
        sub_df = pd.DataFrame()

        if filtered_words:
            target_keyword = filtered_words[-1] if len(filtered_words) > 0 else filtered_words[0]
            mask = df_clean_text.apply(lambda row: row.str.lower().str.contains(target_keyword).any(), axis=1)
            sub_df = df[mask]

        if len(sub_df) > 0:
            valid_metric_cols = [col for col in df.columns if any(k in col.lower() for k in ['gmv', 'cm', 'lm', 'misi', 'gold']) and not any(x in col.lower() for x in ['code', 'assignment'])]
            
            summary_lines = [f"Data akurat ditemukan ({len(sub_df)} baris) untuk kata kunci '{target_keyword}':"]
            
            for col in valid_metric_cols:
                total_val = sub_df[col].sum()
                if isinstance(total_val, (int, float)) and total_val > 0:
                    summary_lines.append(f"- {col}: Rp {total_val:,.0f}")
            
            python_summary_text = "\n".join(summary_lines)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menganalisis data via OpenRouter..."):
                if python_summary_text:
                    formatting_prompt = f"""
Kamu adalah asisten AI analitik yang teliti, profesional, dan to the point.
Berikut adalah data angka valid yang sudah dihitung secara mutlak oleh sistem:

{python_summary_text}

Tugasmu: Jawab pertanyaan user ({prompt}) dengan akurat berdasarkan data di atas.
Struktur jawaban:
1. Jawab langsung ke inti pertanyaan di kalimat pertama (ambil nominal angka dari kolom yang paling relevan dengan pertanyaan user).
2. Tambahkan **1-2 kalimat ringkasan/analisis singkat** di bawahnya secara natural.
3. Jangan menampilkan angka dari kolom lain yang tidak ditanyakan agar tidak membingungkan.

ATURAN MUTLAK: Jangan mengubah angka atau nominal Rupiah yang ada di dalam data di atas sedikit pun!
"""
                    response_text = None
                    for attempt in range(3):
                        try:
                            # Menggunakan model Google Gemma 2 (gratis & stabil di OpenRouter)
                            completion = client.chat.completions.create(
                                model="google/gemma-2-9b-it:free",
                                messages=[
                                    {"role": "user", "content": formatting_prompt}
                                ]
                            )
                            response_text = completion.choices[0].message.content
                            break
                        except Exception as api_err:
                            if attempt < 2:
                                time.sleep(1)
                                continue
                            else:
                                raise api_err
                else:
                    response_text = f"Maaf bro, data untuk '{prompt}' tidak ditemukan di dalam sistem."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
