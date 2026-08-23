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
                if len(parts[1]) == 3 or len(parts[1]) != 2:
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

        # --- 1. AI EKSTRAKSI NAMA ENTITAS & KATEGORI SUBJEK ---
        extraction_prompt = f"""
Analisis pertanyaan user berikut dan berikan output format JSON persis seperti ini:
{{"entity": "<nama entitas>", "category": "<REPS atau APOTEK atau GENERAL>"}}

Aturan Ekstraksi:
1. "entity": Ambil HANYA nama spesifik (misal: "gebang farma", "rizki", "afrianto"). Abaikan kata "apotek", "reps", "gmv", "pencapaian", "bulan ini", dll.
2. "category": 
   - Pilih "REPS" jika user bertanya tentang Sales/Reps/Salesman.
   - Pilih "APOTEK" jika user bertanya tentang Apotek/Toko/Outlet/Pelanggan.
   - Pilih "GENERAL" jika tidak spesifik.

Kalimat Input: "{prompt}"
Output JSON:"""

        extracted_entity = ""
        category = "GENERAL"

        try:
            ext_res = client.chat.completions.create(
                model="google/gemini-2.0-flash-lite-001:free",
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.0
            )
            raw_out = ext_res.choices[0].message.content.strip()
            # Ambil JSON
            json_match = re.search(r'\{.*\}', raw_out, re.DOTALL)
            if json_match:
                import json
                parsed_json = json.loads(json_match.group(0))
                extracted_entity = parsed_json.get("entity", "").lower().strip()
                category = parsed_json.get("category", "GENERAL").upper()
        except Exception:
            extracted_entity = ""
            category = "GENERAL"

        # Fallback manual jika ekstraksi AI gagal
        if not extracted_entity:
            clean_prompt = re.sub(r'[^\w\s]', ' ', prompt.lower())
            stop_words = set([
                'berapa', 'total', 'gmv', 'pencapaian', 'pencapian', 'capaian', 'misi', 'reguler', 'gold', 
                'target', 'data', 'untuk', 'bulan', 'ini', 'kemarin', 'di', 'dan', 'yang', 
                'dari', 'tentang', 'tim', 'gw', 'saya', 'tolong', 'coba', 'reps', 'sales', 
                'apotek', 'apotik', 'toko', 'outlet', 'seberapa', 'banyak', 'pt', 'cv'
            ])
            entity_tokens = [w for w in clean_prompt.split() if w not in stop_words and len(w) > 1]
            extracted_entity = " ".join(entity_tokens)
            if any(k in prompt.lower() for k in ['apotek', 'apotik', 'toko', 'outlet']):
                category = "APOTEK"
            elif any(k in prompt.lower() for k in ['reps', 'sales', 'salesman']):
                category = "REPS"

        entity_tokens = extracted_entity.split()
        sub_df = pd.DataFrame()

        if entity_tokens:
            # Identifikasi kolom target berdasarkan kategori
            target_cols = []
            if category == "APOTEK":
                target_cols = [c for c in df.columns if any(k in c.lower() for k in ['apotek', 'apotik', 'toko', 'outlet', 'customer', 'pelanggan', 'nama toko', 'nama apotek'])]
            elif category == "REPS":
                target_cols = [c for c in df.columns if any(k in c.lower() for k in ['reps', 'sales', 'salesman', 'nama reps', 'nama sales'])]

            # STRATEGI 1: Search di kolom target spesifik jika ada
            if target_cols:
                target_series = df_clean_text[target_cols].apply(lambda row: " ".join(row.values).lower(), axis=1)
                mask_target = target_series.apply(lambda x: all(t in x for t in entity_tokens))
                sub_df = df[mask_target]

            # STRATEGI 2: Fallback ke pencarian seluruh kolom jika tidak ditemukan di kolom spesifik
            if len(sub_df) == 0:
                row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
                mask_all = row_combined.apply(lambda x: all(t in x for t in entity_tokens))
                sub_df = df[mask_all]

                if len(sub_df) == 0 and len(entity_tokens) > 1:
                    specific_token = max(entity_tokens, key=len)
                    mask_spec = row_combined.str.contains(re.escape(specific_token), regex=True, na=False)
                    sub_df = df[mask_spec]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menghitung data dengan presisi 100%..."):
                if len(sub_df) > 0:
                    calculated_metrics = []
                    
                    # Filter Kolom Penjumlahan yang Valid (HANYA Nominal GMV/Sales)
                    valid_cols = []
                    for col in sub_df.columns:
                        col_lower = col.lower()
                        # Abaikan kolom non-nominal
                        if any(ignore in col_lower for ignore in ['count', 'visit', 'target', '%', 'pct', 'date', 'tanggal', 'id', 'code', 'durasi', 'duration']):
                            continue
                        if any(k in col_lower for k in ['gmv', 'cm', 'lm', 'sales', 'pencapaian']):
                            valid_cols.append(col)

                    # Prioritaskan kolom CM / Current Month jika user menanyakan bulan ini
                    cm_cols = [c for c in valid_cols if any(k in c.lower() for k in ['cm', 'current', 'bulan ini', 'total'])]
                    target_calculation_cols = cm_cols if cm_cols else valid_cols

                    for col in target_calculation_cols:
                        num_series = sub_df[col].apply(parse_number_exact)
                        total_val = num_series.sum()
                        if total_val > 0:
                            calculated_metrics.append(f"- **{col}**: Rp {total_val:,.0f}".replace(",", "."))

                    calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Tidak ada kolom angka nominal yang dapat terhitung."
                    
                    sub_df_sample = sub_df.dropna(how='all', axis=1).head(10)
                    data_table_md = sub_df_sample.to_markdown(index=False)

                    system_prompt = f"""
Kamu adalah Senior Data Analyst SPV yang sangat teliti.

DITEMUKAN **{len(sub_df)} BARIS DATA** UNTUK ENTITAS: '{extracted_entity}' (Kategori: {category}).

HASIL KALKULASI PRESISI PYTHON UNTUK **SELURUH {len(sub_df)} BARIS DATA** (GUNAKAN ANGKA INI):
{calc_summary_str}

SAMPEL RINCIAN TABEL DARI GOOGLE SHEET (Max 10 baris):
{data_table_md}

Pertanyaan User: "{prompt}"

Instruksi Sangat Penting:
1. GUNAKAN HASIL KALKULASI PRESISI PYTHON DI ATAS UNTUK MENJAWAB TOTAL ANGKA/GMV! JANGAN MENAMBAHKAN/MENJUMLAHKAN MANUAL LAGI PAKAI AI.
2. Jawab secara to the point di kalimat pertama dengan menyebutkan nama entitas dan angka total nominal rupiah yang presisi.
3. Jika user bertanya "bulan ini", utamakan angka dari kolom CM (Current Month) atau MTD. Jika tidak ada, jelaskan bahwa angka berasal dari kolom LM (Last Month).
4. JANGAN PERNAH menampilkan rincian penjumlahan tambah-tambahan manual `(a + b + c)` yang dipotong-potong di jawaban.
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
                        response_text = f"Ditemukan **{len(sub_df)} baris data** untuk {category.lower()} '{extracted_entity}'. Berikut rincian total angkanya:\n\n{calc_summary_str}"

                else:
                    response_text = f"Maaf bro, data untuk **'{extracted_entity}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
