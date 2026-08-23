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

# Kustomisasi Tampilan Visual Streamlit
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

def parse_number_exact(val):
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'null', 'none', '-', '']:
        return 0.0

    cleaned = re.sub(r'[^0-9\,\.-]', '', val_str)
    if not cleaned:
        return 0.0

    try:
        if '.' in cleaned and ',' in cleaned:
            if cleaned.rfind('.') < cleaned.rfind(','):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned and '.' not in cleaned:
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif '.' in cleaned and ',' not in cleaned:
            parts = cleaned.split('.')
            if len(parts) > 2:
                cleaned = cleaned.replace('.', '')
            elif len(parts) == 2:
                if len(parts[1]) == 3:
                    cleaned = cleaned.replace('.', '')
                elif len(parts[1]) != 2:
                    cleaned = cleaned.replace('.', '')

        return float(cleaned)
    except Exception:
        return 0.0

try:
    csv_url = convert_to_csv_url(SHEET_URL)
    df = pd.read_csv(csv_url, dtype=str)
    df.columns = df.columns.str.strip()
    df_clean_text = df.fillna("").astype(str)

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
        
        # Cari nama Reps utama
        target_reps = None
        for name in ['sulistiana', 'afrianto', 'rizki', 'gde', 'mulyanto']:
            if name in prompt_lower:
                target_reps = name
                break

        # Identifikasi kolom khusus Reps/Sales & GMV
        reps_cols = [c for c in df.columns if any(k in c.lower() for k in ['reps', 'sales', 'nama reps'])]
        gmv_cols = [c for c in df.columns if any(k in c.lower() for k in ['gmv', 'ach', 'total harga', 'nominal', 'sales'])]
        status_cols = [c for c in df.columns if 'status' in c.lower()]

        filtered_df = df.copy()

        # 1. Filter Status (Abaikan canceled/failed jika kolom status ada)
        if status_cols:
            s_col = status_cols[0]
            filtered_df = filtered_df[~filtered_df[s_col].astype(str).str.lower().isin(['canceled', 'cancel', 'failed', 'batal'])]

        # 2. Filter hanya pada kolom khusus Reps
        if target_reps and reps_cols:
            r_col = reps_cols[0]
            filtered_df = filtered_df[filtered_df[r_col].astype(str).str.lower().str.contains(target_reps)]
        elif not target_reps:
            # Jika tanya Total Team / Happy
            stop_words = ['berapa', 'total', 'gmv', 'pencapaian', 'capaian', 'data', 'untuk', 'bulan', 'ini', 'di', 'dan', 'yang', 'dari', 'gw', 'saya']
            tokens = [w for w in prompt_lower.split() if w not in stop_words and len(w) > 1]
            if tokens:
                row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
                filtered_df = df[row_combined.apply(lambda x: any(t in x for t in tokens))]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Kalkulasi data presisi..."):
                if len(filtered_df) > 0 and gmv_cols:
                    calculated_metrics = []
                    for g_col in gmv_cols:
                        if not any(ignore in g_col.lower() for ignore in ['date', 'tanggal', 'id', 'code', 'durasi']):
                            total_val = filtered_df[g_col].apply(parse_number_exact).sum()
                            if total_val > 0:
                                calculated_metrics.append(f"- **{g_col}**: Rp {total_val:,.0f}".replace(",", "."))

                    calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Tidak ada kolom angka yang terhitung."
                    
                    system_prompt = f"""
Kamu adalah Senior Data Analyst SPV.

DITEMUKAN HASIL KALKULASI PRESISI PYTHON:
{calc_summary_str}

Pertanyaan User: "{prompt}"

Instruksi:
1. GUNAKAN ANGKA DARI LIST DI ATAS UNTUK MENJAWAB TOTAL GMV/PENCAPAIAN.
2. Jawab secara langsung di kalimat pertama.
3. DILARANG MELAKUKAN PENJUMLAHAN MANUAL DENGAN RUMUS LAIN.
"""
                    response_text = ""
                    models_to_try = [
                        "google/gemini-2.0-flash-lite-001:free",
                        "google/gemini-2.0-flash-exp:free",
                        "openrouter/free"
                    ]

                    for model_id in models_to_try:
                        try:
                            completion = client.chat.completions.create(
                                model=model_id,
                                messages=[{"role": "user", "content": system_prompt}],
                                temperature=0.0
                            )
                            if completion.choices and len(completion.choices) > 0:
                                res = completion.choices[0].message.content
                                if res and len(res.strip()) > 5:
                                    response_text = res
                                    break
                        except Exception:
                            continue

                    if not response_text or len(response_text.strip()) < 5:
                        response_text = f"Berikut total angkanya:\n\n{calc_summary_str}"

                else:
                    response_text = "Maaf bro, data untuk pencarian tersebut tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
