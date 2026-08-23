import streamlit as st
import pandas as pd
from openai import OpenAI
import re

OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
SHEET_URL = st.secrets["SHEET_URL"]

st.set_page_config(
    page_title="Chatbot Universe SPV Happy", 
    page_icon="🤖", 
    layout="centered"
)

# Kustomisasi Tampilan Visual
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
    
    # Pembersihan angka otomatis di Python
    df_clean_text = df.fillna("").astype(str)
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['gmv', 'target', 'sales', 'value', 'amount', 'cm', 'lm', 'misi', 'gold']):
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace('.', '', regex=False)
                                   .str.replace(',', '.', regex=False)
                                   .str.replace(r'[^0-9\.-]', '', regex=True), 
                errors='coerce'
            ).fillna(0)

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
        ignore_words = ['berapa', 'data', 'untuk', 'bulan', 'ini', 'kemarin', 'di', 'dan', 'yang', 'dari', 'tentang', 'pencapaian', 'capaian', 'misi', 'gold', 'gmv', 'total', 'totalin', 'tim', 'gw', 'saya', 'tolong', 'coba']
        search_tokens = [word for word in prompt_lower.split() if word not in ignore_words and len(word) > 2]
        
        # 1. PYTHON FILTER & HITUNG KETAT
        sub_df = pd.DataFrame()
        if search_tokens:
            row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
            mask = row_combined.apply(lambda x: any(token in x for token in search_tokens))
            sub_df = df[mask]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menyusun ringkasan cepat..."):
                if len(sub_df) > 0:
                    # Ambil kolom metrik utama
                    metric_cols = [col for col in df.columns if any(k in col.lower() for k in ['gmv', 'target', 'cm', 'lm']) and not any(x in col.lower() for x in ['code', 'assignment'])]
                    
                    # Rangkum totalnya langsung pakai Python (Super Cepat!)
                    totals_summary = []
                    for c in metric_cols:
                        val = sub_df[c].sum()
                        if val != 0:
                            totals_summary.append(f"{c}: Rp {val:,.0f}")
                    
                    data_ringkas = "\n".join(totals_summary)

                    # Prompt sangat pendek agar respons AI secepat kilat
                    system_prompt = f"""
Kamu adalah asisten SPV yang ramah dan cepat.
Berikut adalah HASIL KALKULASI PASTI dari sistem (Ditemukan {len(sub_df)} baris data):
{data_ringkas}

Pertanyaan user: "{prompt}"

Tugas:
Jawab langsung pertanyaan user menggunakan data nominal angka pasti di atas.
Berikan penjelasan/analisis singkat (1-2 kalimat) yang logis berdasarkan angka tersebut.
JANGAN mengubah angka nominal sedikit pun!
"""
                    try:
                        # Menggunakan model tercepat & ter-ringan
                        completion = client.chat.completions.create(
                            model="meta-llama/llama-3.2-1b-instruct:free",
                            messages=[{"role": "user", "content": system_prompt}]
                        )
                        response_text = completion.choices[0].message.content
                    except Exception:
                        try:
                            completion = client.chat.completions.create(
                                model="openrouter/free",
                                messages=[{"role": "user", "content": system_prompt}]
                            )
                            response_text = completion.choices[0].message.content
                        except Exception as err:
                            response_text = f"**Hasil Total Data:**\n\n" + "\n".join([f"- {item}" for item in totals_summary])
                else:
                    response_text = f"Maaf bro, data untuk **'{' '.join(search_tokens)}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
