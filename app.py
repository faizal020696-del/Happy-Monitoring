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
        if ',' in cleaned:
            parts = cleaned.split(',')
            if len(parts[-1]) <= 2:
                cleaned = "".join(parts[:-1])
            else:
                cleaned = cleaned.replace(',', '')

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
        
        # Kata dasar yang dibuang untuk ekstrak kata kunci
        stop_words = [
            'berapa', 'total', 'gmv', 'pencapaian', 'capaian', 'misi', 'reguler', 'gold', 
            'target', 'data', 'untuk', 'bulan', 'ini', 'kemarin', 'di', 'dan', 'yang', 
            'dari', 'tentang', 'tim', 'gw', 'saya', 'tolong', 'coba', 'reps', 'sales', 'apotek', 'apotik'
        ]
        
        entity_tokens = [w for w in prompt_lower.split() if w not in stop_words and len(w) > 1]
        if not entity_tokens:
            entity_tokens = [w for w in prompt_lower.split() if len(w) > 2]

        sub_df = pd.DataFrame()
        if entity_tokens:
            row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
            
            # Tingkat 1: Cari yang cocok dengan SEMUA kata kunci
            mask_all = row_combined.apply(lambda x: all(t in x for t in entity_tokens))
            sub_df = df[mask_all]
            
            # Tingkat 2: Fallback jika 0 hasil
            if len(sub_df) == 0:
                mask_any = row_combined.apply(lambda x: any(t in x for t in entity_tokens))
                sub_df = df[mask_any]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menghitung data dengan presisi 100%..."):
                if len(sub_df) > 0:
                    calculated_metrics = []
                    
                    # 1. Prioritaskan Kolom Utama Pencapaian (CM / MTD / ACH)
                    priority_cols = [c for c in sub_df.columns if any(k in c.lower() for k in ['gmv ach', 'gmv cm', 'pencapaian cm', 'total gmv', 'ach gmv'])]
                    
                    # 2. Jika tidak ada nama spesifik, ambil kolom GMV/Pencapaian umum (abaikan target/persentase)
                    if not priority_cols:
                        priority_cols = [c for c in sub_df.columns if any(k in c.lower() for k in ['gmv', 'cm', 'ach', 'pencapaian']) and not any(ignore in c.lower() for ignore in ['target', '%', 'pct', 'status', 'id', 'date', 'tanggal'])]

                    for col in priority_cols:
                        col_lower = col.lower()
                        if not any(ignore in col_lower for ignore in ['target', 'date', 'tanggal', 'id', 'code', '%', 'pct', 'status']):
                            num_series = sub_df[col].apply(parse_number_exact)
                            total_val = num_series.sum()
                            if total_val > 0:
                                calculated_metrics.append(f"- **{col}**: Rp {total_val:,.0f}".replace(",", "."))

                    calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Tidak ada kolom angka nominal yang terhitung."
                    
                    sub_df_sample = sub_df.dropna(how='all', axis=1).head(10)
                    data_table_md = sub_df_sample.to_markdown(index=False)

                    system_prompt = f"""
Kamu adalah Senior Data Analyst SPV yang sangat teliti.

DITEMUKAN **{len(sub_df)} BARIS DATA** UNTUK PENCARIAN USER.

HASIL KALKULASI PRESISI PYTHON DARI DATA TERFILTER:
{calc_summary_str}

SAMPEL TABEL DATA DARI GOOGLE SHEET (Max 10 baris):
{data_table_md}

Pertanyaan User: "{prompt}"

Instruksi Sangat Penting:
1. GUNAKAN LANGSUNG ANGKA HASIL KALKULASI PYTHON DI ATAS UNTUK MENJAWAB TOTAL GMV/PENCAPAIAN! DILARANG MENGHITUNG PENJUMLAHAN MANUAL ULANG DENGAN AI.
2. Jawab secara to the point di kalimat pertama. Format: "Total pencapaian GMV [Nama Reps/Entitas] bulan ini adalah Rp [Angka]."
3. JANGAN PERNAH menampilkan rincian penjumlahan tambah-tambahan manual `(a + b + c)` yang dipotong-potong di jawaban.
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
                        response_text = f"Ditemukan **{len(sub_df)} baris data**. Berikut rincian angkanya:\n\n{calc_summary_str}"

                else:
                    search_kw = ' '.join(entity_tokens) if entity_tokens else prompt
                    response_text = f"Maaf bro, data untuk **'{search_kw}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
