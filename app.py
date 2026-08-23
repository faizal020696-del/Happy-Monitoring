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
        padding: 2rem 1.5rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 20px -4px rgba(79, 70, 229, 0.2);
        margin-bottom: 1.5rem;
    }
    .main-header h1 { color: white !important; font-weight: 800; font-size: 2rem; margin-bottom: 0.3rem; }
    .main-header p { color: #e0e7ff !important; font-size: 0.95rem; margin: 0; }
    .stChatMessage { border-radius: 16px !important; padding: 0.8rem 1.1rem !important; margin-bottom: 0.8rem !important; }
    .stChatInputContainer { border-radius: 15px !important; bottom: 20px !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="main-header">
        <h1>🤖 Assistant Universe SPV</h1>
        <p>Tanyakan info DPD, Limit, Omset, Kunjungan, atau Misi outlet & reps kapan saja!</p>
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
        st.write(f"Total Baris Data: **{len(df):,}**")
        st.write("---")
        st.write("### 💡 Tips Pertanyaan Friendly:")
        st.caption("• *Berapa limit apotek berkah jaya?*")
        st.caption("• *Berapa DPD gebang farma?*")
        st.caption("• *Berapa jumlah kunjungan di berkah jaya?*")
        st.caption("• *Minta data performa reps rizki*")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Halo SPV! 👋 Ada data outlet atau reps yang mau dicek hari ini? Ketik nama toko/reps dan data yang mau kamu ketahui ya."}
        ]

    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    if prompt := st.chat_input("Tulis pertanyaan kamu di sini..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        prompt_lower = prompt.lower()

        # --- 1. KAMUS SINONIM METRIK (DETEKSI INTENT PERTANYAAN) ---
        SYNONYM_MAP = {
            'dpd': ['dpd', 'terlambat', 'tunggakan', 'jatuh tempo', 'overdue', 'macet', 'hari'],
            'limit': ['limit', 'plafon', 'kredit', 'sisa limit', 'avaibility', 'tersedia'],
            'visit': ['kunjungan', 'visit', 'datang', 'dikunjungi'],
            'misi': ['misi', 'mission', 'reguler', 'gold', 'campaign'],
            'cm': ['cm', 'bulan ini', 'current month', 'pencapaian bulan ini'],
            'lm': ['lm', 'bulan lalu', 'last month', 'pencapaian bulan lalu'],
            'gmv': ['gmv', 'omset', 'sales', 'penjualan', 'pencapaian', 'capaian', 'target', 'l3m', 'l2m', 'peak']
        }

        detected_intents = []
        for key, synonyms in SYNONYM_MAP.items():
            if any(syn in prompt_lower for syn in synonyms):
                detected_intents.append(key)

        # --- 2. EKSTRAKSI NAMA TOKO / REPS SANGAT BERSIH (PYTHON REGEX) ---
        clean_prompt = prompt_lower
        
        junk_words = [
            r'\bberapa\b', r'\btotal\b', r'\bjumlah\b', r'\byang\b', r'\btersedia\b', r'\bada\b', 
            r'\bkunjungan\b', r'\breps\b', r'\bsales\b', r'\bsalesman\b', r'\blimit\b', r'\bplafon\b',
            r'\bdpd\b', r'\bmisi\b', r'\bgmv\b', r'\bomset\b', r'\bdi\b', r'\bdiapotek\b', r'\bdiapotik\b',
            r'\bapotek\b', r'\bapotik\b', r'\btoko\b', r'\boutlet\b', r'\bpt\b', r'\bcv\b', r'\bdata\b',
            r'\buntuk\b', r'\bbulan\b', r'\bini\b', r'\blalu\b', r'\bkah\b', r'\bdong\b', r'\btolong\b',
            r'\bcek\b', r'\blihat\b', r'\binfo\b', r'\binformasi\b', r'\btolong\b', r'\bpls\b', r'\bplz\b'
        ]
        
        for junk in junk_words:
            clean_prompt = re.sub(junk, ' ', clean_prompt)
            
        clean_prompt = re.sub(r'[^\w\s]', ' ', clean_prompt)
        extracted_entity = " ".join(clean_prompt.split()).strip()

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
            with st.spinner("Sedang mengecek data..."):
                if len(sub_df) > 0:
                    target_columns = []

                    # Filter kolom presisi sesuai intent
                    if detected_intents:
                        for col in sub_df.columns:
                            col_lower = col.lower()
                            for intent in detected_intents:
                                synonyms = SYNONYM_MAP[intent]
                                if any(syn in col_lower for syn in synonyms):
                                    if col not in target_columns:
                                        target_columns.append(col)
                    
                    # Jika user minta data umum (tanpa metrik spesifik), tampilkan metrik utama
                    is_general_query = False
                    if not target_columns:
                        is_general_query = True
                        important_keys = ['gmv', 'cm', 'lm', 'sales', 'limit', 'dpd', 'misi', 'visit', 'kunjungan']
                        for col in sub_df.columns:
                            col_lower = col.lower()
                            if any(k in col_lower for k in important_keys):
                                target_columns.append(col)

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
                            calculated_metrics.append(f"• **{col}**: {avg_dpd:.0f} hari")
                        elif any(k in col_lower for k in ['visit', 'kunjungan', 'count']):
                            calculated_metrics.append(f"• **{col}**: {total_val:,.0f} kali".replace(",", "."))
                        elif any(k in col_lower for k in ['limit', 'gmv', 'cm', 'lm', 'sales', 'pencapaian', 'misi', 'reguler', 'gold', 'target', 'omset', 'peak', 'gap']):
                            calculated_metrics.append(f"• **{col}**: Rp {total_val:,.0f}".replace(",", "."))
                        else:
                            if total_val > 0:
                                calculated_metrics.append(f"• **{col}**: {total_val:,.0f}".replace(",", "."))

                    calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Metrik yang ditanyakan tidak terdeteksi di sheet."

                    # --- PROMPT AI UNTUK TONE JAWABAN SUPEL & FRIENDLY ---
                    system_prompt = f"""
Kamu adalah Chatbot Assistant Universe SPV yang sangat ramah, profesional, dan membantu.

DATA DITEMUKAN UNTUK: '{extracted_entity.title()}'.
PERTANYAAN USER: "{prompt}"

HASIL KALKULASI DARI DATASET:
{calc_summary_str}

PETUNJUK RESPONS SUPEL:
1. Jawab dengan gaya percakapan yang ramah, sopan, dan jelas (bisa gunakan emojI yang sesuai seperti 📊, 💳, 📍, 🚀 jika relevan).
2. Jika user bertanya **hal spesifik** (misal DPD, Limit, atau Kunjungan), berikan jawaban langsung di baris pertama tanpa menyajikan daftar panjang.
3. Jika user bertanya **data umum/ringkasan**, sajikan hasil kalkulasi dalam bentuk poin-poin rapi.
4. Jangan pernah menampilkan rincian angka yang tidak relevan dengan pertanyaan user.
"""
                    response_text = ""
                    try:
                        completion = client.chat.completions.create(
                            model="google/gemini-2.0-flash-lite-001:free",
                            messages=[{"role": "user", "content": system_prompt}],
                            temperature=0.2
                        )
                        if completion.choices and len(completion.choices) > 0:
                            response_text = completion.choices[0].message.content.strip()
                    except Exception:
                        response_text = ""

                    if not response_text:
                        entity_name = extracted_entity.title() if extracted_entity else "Outlet/Reps"
                        response_text = f"Berikut data untuk **{entity_name}**:\n\n{calc_summary_str}"

                else:
                    # RESPON FRIENDLY SAAT DATA TIDAK DITEMUKAN
                    searched_name = extracted_entity.title() if extracted_entity else prompt
                    response_text = f"Waduh, data untuk **'{searched_name}'** belum ketemu nih di Google Sheet. 🤔\n\n**Coba cek tips berikut:**\n1. Pastikan ejaan nama toko/reps sudah benar.\n2. Coba gunakan kata kunci nama toko yang lebih singkat (contoh: cukup ketik *'Berkah Jaya'* atau *'Gebang'*)."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
