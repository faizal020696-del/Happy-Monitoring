import streamlit as st
import pandas as pd
from openai import OpenAI
import re
import json

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
        st.write("### 📊 Status Data Master")
        st.write(f"Total Baris: {len(df)}")
        st.write("### 📋 Daftar Kolom Sheet:")
        for idx, col in enumerate(df.columns):
            st.text(f"{idx+1}. {col}")

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

        # --- 1. KAMUS SINONIM METRIK (FLEKSIBEL DI TINGKAT PYTHON) ---
        SYNONYM_MAP = {
            'dpd': ['dpd', 'terlambat', 'tunggakan', 'jatuh tempo', 'overdue', 'macet', 'hari'],
            'limit': ['limit', 'plafon', 'kredit', 'sisa limit', 'avaibility'],
            'misi': ['misi', 'mission', 'reguler', 'gold', 'campaign'],
            'cm': ['cm', 'bulan ini', 'current month', 'pencapaian bulan ini'],
            'lm': ['lm', 'bulan lalu', 'last month', 'pencapaian bulan lalu'],
            'gmv': ['gmv', 'omset', 'sales', 'penjualan', 'pencapaian', 'capaian', 'target', 'l3m', 'l2m', 'peak']
        }

        detected_intents = []
        for key, synonyms in SYNONYM_MAP.items():
            if any(syn in prompt_lower for syn in synonyms):
                detected_intents.append(key)

        # --- 2. AI EKSTRAKSI ENTITAS NAMA ---
        extraction_prompt = f"""
Saring pertanyaan user dan kembalikan format JSON:
{{"entity": "<nama entitas bersih>"}}

Aturan:
Ambil HANYA kata kunci nama toko/reps/objek (misal: "gebang farma", "rizki", "afrianto"). 
Abaikan kata metrik seperti "dpd", "limit", "misi", "reguler", "gold", "apotek", "reps", "sales", "gmv", "pencapaian", "bulan ini", dll.

Input: "{prompt}"
JSON:"""

        extracted_entity = ""
        try:
            ext_res = client.chat.completions.create(
                model="google/gemini-2.0-flash-lite-001:free",
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.0
            )
            raw_out = ext_res.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', raw_out, re.DOTALL)
            if json_match:
                parsed_json = json.loads(json_match.group(0))
                extracted_entity = parsed_json.get("entity", "").lower().strip()
        except Exception:
            extracted_entity = ""

        if not extracted_entity:
            clean_prompt = re.sub(r'[^\w\s]', ' ', prompt_lower)
            stop_words = set(['berapa', 'total', 'gmv', 'dpd', 'limit', 'misi', 'reguler', 'gold', 'pencapaian', 'pencapian', 'capaian', 'target', 'data', 'untuk', 'bulan', 'ini', 'reps', 'sales', 'salesman', 'apotek', 'apotik', 'toko', 'outlet', 'pt', 'cv'])
            extracted_entity = " ".join([w for w in clean_prompt.split() if w not in stop_words and len(w) > 1])

        entity_tokens = extracted_entity.split()
        sub_df = pd.DataFrame()

        if entity_tokens:
            is_reps_query = any(k in prompt_lower for k in ['reps', 'sales', 'salesman', 'rep'])
            is_apotek_query = any(k in prompt_lower for k in ['apotek', 'apotik', 'toko', 'outlet', 'customer', 'pelanggan'])

            ignored_cols = [c for c in df.columns if any(k in c.lower() for k in ['alamat', 'address', 'jalan', 'street', 'kota', 'city', 'keterangan', 'remark'])]
            searchable_cols = [c for c in df.columns if c not in ignored_cols]

            if is_reps_query:
                reps_cols = [c for c in searchable_cols if any(k in c.lower() for k in ['reps', 'sales', 'salesman', 'nama reps', 'nama sales'])]
                if not reps_cols:
                    reps_cols = searchable_cols

                pattern = r'\b' + re.escape(extracted_entity) + r'\b'
                mask_reps = pd.Series(False, index=df.index)
                for col in reps_cols:
                    mask_reps |= df_clean_text[col].str.lower().str.contains(pattern, regex=True, na=False)
                sub_df = df[mask_reps]

            elif is_apotek_query:
                apotek_cols = [c for c in searchable_cols if any(k in c.lower() for k in ['toko', 'apotek', 'apotik', 'outlet', 'customer', 'pelanggan', 'nama toko', 'nama apotek'])]
                if not apotek_cols:
                    apotek_cols = searchable_cols

                pattern = r'\b' + r'\b.*\b'.join([re.escape(t) for t in entity_tokens]) + r'\b'
                mask_apotek = pd.Series(False, index=df.index)
                for col in apotek_cols:
                    mask_apotek |= df_clean_text[col].str.lower().str.contains(pattern, regex=True, na=False)
                sub_df = df[mask_apotek]

            if len(sub_df) == 0:
                series_clean = df_clean_text[searchable_cols].apply(lambda row: " ".join(row.values).lower(), axis=1)
                pattern_fallback = r'\b' + r'\b.*\b'.join([re.escape(t) for t in entity_tokens]) + r'\b'
                sub_df = df[series_clean.str.contains(pattern_fallback, regex=True, na=False)]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menghitung data presisi..."):
                if len(sub_df) > 0:
                    target_columns = []

                    # --- 3. PEMILIHAN KOLOM PRESISI SESUAI SINONIM ---
                    if detected_intents:
                        for col in sub_df.columns:
                            col_lower = col.lower()
                            for intent in detected_intents:
                                synonyms = SYNONYM_MAP[intent]
                                if any(syn in col_lower for syn in synonyms):
                                    if col not in target_columns:
                                        target_columns.append(col)
                    
                    # Jika user bertanya umum/tidak menyebut metrik spesifik, pilihkan metrik utama saja
                    if not target_columns:
                        important_keys = ['gmv', 'cm', 'lm', 'sales', 'limit', 'dpd', 'misi', 'pencapaian']
                        for col in sub_df.columns:
                            col_lower = col.lower()
                            if any(k in col_lower for k in important_keys):
                                target_columns.append(col)

                    # Fallback akhir jika masih belum ada
                    if not target_columns:
                        target_columns = list(sub_df.columns)

                    calculated_metrics = []
                    for col in target_columns:
                        col_lower = col.lower()
                        if any(ignore in col_lower for ignore in ['date', 'tanggal', 'id', 'code', 'zip', 'durasi', 'duration', 'telepon', 'phone', '%', 'pct', 'nama', 'toko', 'apotek', 'address', 'alamat', 'status']):
                            continue

                        num_series = sub_df[col].apply(parse_number_exact)
                        total_val = num_series.sum()

                        if 'dpd' in col_lower:
                            avg_dpd = num_series.mean()
                            calculated_metrics.append(f"- **{col}**: {avg_dpd:.0f} hari")
                        elif any(k in col_lower for k in ['limit', 'gmv', 'cm', 'lm', 'sales', 'pencapaian', 'misi', 'reguler', 'gold', 'target', 'omset', 'peak', 'gap']):
                            calculated_metrics.append(f"- **{col}**: Rp {total_val:,.0f}".replace(",", "."))
                        else:
                            if total_val > 0:
                                calculated_metrics.append(f"- **{col}**: {total_val:,.0f}".replace(",", "."))

                    calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Metrik yang ditanyakan tidak terdeteksi."

                    system_prompt = f"""
Kamu adalah Senior Data Analyst SPV yang ramah dan langsung pada inti jawaban.

DITEMUKAN DATA UNTUK ENTITAS: '{extracted_entity.title()}'.
PERTANYAAN USER: "{prompt}"

HASIL KALKULASI PRESISI PYTHON:
{calc_summary_str}

Instruksi Utama:
1. Jawab LANGSUNG di kalimat pertama dengan singkat dan padat (contoh: "DPD untuk **Apotek Gebang Farma** adalah **13 hari**.").
2. JANGAN PERNAH menampilkan daftar data angka yang tidak ditanyakan oleh user, kecuali jika user memang meminta seluruh data secara ringkas.
"""
                    response_text = ""
                    try:
                        completion = client.chat.completions.create(
                            model="google/gemini-2.0-flash-lite-001:free",
                            messages=[{"role": "user", "content": system_prompt}],
                            temperature=0.0
                        )
                        if completion.choices and len(completion.choices) > 0:
                            response_text = completion.choices[0].message.content.strip()
                    except Exception:
                        response_text = ""

                    if not response_text:
                        entity_name = extracted_entity.title() if extracted_entity else "Entitas"
                        response_text = f"Data **{entity_name}**:\n\n{calc_summary_str}"

                else:
                    response_text = f"Maaf bro, data untuk **'{extracted_entity}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
