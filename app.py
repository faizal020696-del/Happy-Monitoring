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

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Halo SPV! 👋 Ada data outlet atau reps yang mau dicek hari ini?"}
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

        # --- 1. KAMUS INTENT METRIK KHUSUS ---
        detected_intents = []
        
        # Cek spesifik waktu dulu
        is_cm = any(k in prompt_lower for k in ['bulan ini', 'cm', 'current month', 'bln ini'])
        is_lm = any(k in prompt_lower for k in ['bulan lalu', 'lm', 'last month', 'bln lalu'])
        
        if is_cm:
            detected_intents.append('cm')
        elif is_lm:
            detected_intents.append('lm')
        elif 'dpd' in prompt_lower:
            detected_intents.append('dpd')
        elif any(k in prompt_lower for k in ['limit', 'plafon', 'kredit', 'avaibility']):
            detected_intents.append('limit')
        elif any(k in prompt_lower for k in ['visit', 'kunjungan']):
            detected_intents.append('visit')
        elif any(k in prompt_lower for k in ['gmv', 'omset', 'sales', 'penjualan']):
            detected_intents.append('gmv')

        # --- 2. REGEX EXTRACTION SUPER BERSIH UNTUK NAMA ---
        clean_prompt = prompt_lower

        # Hapus awalan 'di' yang nempel di kata lain (misal: "dibulan", "diapotek")
        clean_prompt = re.sub(r'\bdi([a-z]+)', r'\1', clean_prompt)
        
        junk_patterns = [
            r'\bberapa\b', r'\btotal\b', r'\bjumlah\b', r'\byang\b', r'\btersedia\b', r'\bada\b', 
            r'\bkunjungan\b', r'\breps\b', r'\bsales\b', r'\bsalesman\b', r'\blimit\b', r'\bplafon\b',
            r'\bdpd\b', r'\bmisi\b', r'\bgmv\b', r'\bomset\b', r'\bdi\b', r'\bapotek\b', r'\bapotik\b', 
            r'\btoko\b', r'\boutlet\b', r'\bpt\b', r'\bcv\b', r'\bdata\b', r'\buntuk\b', r'\bbulan\b', 
            r'\bini\b', r'\blalu\b', r'\bni\b', r'\binih\b', r'\bkah\b', r'\bdong\b', r'\bcek\b', r'\binfo\b'
        ]
        
        for junk in junk_patterns:
            clean_prompt = re.sub(junk, ' ', clean_prompt)
            
        clean_prompt = re.sub(r'[^\w\s]', ' ', clean_prompt)
        extracted_entity = " ".join(clean_prompt.split()).strip()

        entity_tokens = extracted_entity.split()
        sub_df = pd.DataFrame()

        if entity_tokens:
            ignored_cols = [c for c in df.columns if any(k in c.lower() for k in ['alamat', 'address', 'jalan', 'kota'])]
            searchable_cols = [c for c in df.columns if c not in ignored_cols]

            pattern = r'\b' + r'\b.*\b'.join([re.escape(t) for t in entity_tokens]) + r'\b'
            series_clean = df_clean_text[searchable_cols].apply(lambda row: " ".join(row.values).lower(), axis=1)
            sub_df = df[series_clean.str.contains(pattern, regex=True, na=False)]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Mengecek data..."):
                if len(sub_df) > 0:
                    target_columns = []

                    # --- 3. FILTERING KOLOM ON-POINT ---
                    if 'cm' in detected_intents:
                        # Prioritaskan kolom CM jika user tanya "bulan ini"
                        target_columns = [c for c in sub_df.columns if c.lower() == 'cm' or 'cm' in c.lower()]
                    elif 'lm' in detected_intents:
                        target_columns = [c for c in sub_df.columns if c.lower() == 'lm' or 'lm' in c.lower()]
                    elif 'dpd' in detected_intents:
                        target_columns = [c for c in sub_df.columns if 'dpd' in c.lower()]
                    elif 'limit' in detected_intents:
                        target_columns = [c for c in sub_df.columns if 'limit' in c.lower()]
                    elif 'visit' in detected_intents:
                        target_columns = [c for c in sub_df.columns if 'visit' in c.lower() or 'kunjungan' in c.lower()]
                    elif 'gmv' in detected_intents:
                        target_columns = [c for c in sub_df.columns if any(k in c.lower() for k in ['gmv', 'sales', 'cm'])]

                    # Fallback jika tidak ada intent spesifik
                    if not target_columns:
                        important_keys = ['gmv', 'cm', 'lm', 'sales', 'limit', 'dpd']
                        target_columns = [c for c in sub_df.columns if any(k in c.lower() for k in important_keys)]

                    calculated_metrics = []
                    for col in target_columns:
                        col_lower = col.lower()
                        if any(ignore in col_lower for ignore in ['id', 'code', 'telepon', '%', 'nama', 'toko', 'apotek', 'address']):
                            continue

                        num_series = sub_df[col].apply(parse_number_exact)
                        total_val = num_series.sum()

                        if 'dpd' in col_lower:
                            calculated_metrics.append(f"• **{col}**: {num_series.mean():.0f} hari")
                        elif any(k in col_lower for k in ['visit', 'kunjungan', 'count']):
                            calculated_metrics.append(f"• **{col}**: {total_val:,.0f} kali".replace(",", "."))
                        else:
                            calculated_metrics.append(f"• **{col}**: Rp {total_val:,.0f}".replace(",", "."))

                    calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Metrik tidak terdeteksi."

                    system_prompt = f"""
Kamu adalah Assistant Data SPV.

DATA UNTUK: '{extracted_entity.title()}'.
PERTANYAAN USER: "{prompt}"

HASIL KALKULASI PRESISI:
{calc_summary_str}

Instruksi Ringkas & Direct:
1. Jawab LANGSUNG di baris pertama tanpa salam berbelit-belit.
2. Contoh jika tanya GMV bulan ini: "GMV **Afrianto** bulan ini (CM) adalah **Rp 533.296.016**."
3. HANYA sebutkan angka metrik yang diminta user. JANGAN tampilkan daftar kolom lainnya!
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
                        response_text = f"Data **{extracted_entity.title()}**:\n{calc_summary_str}"

                else:
                    searched_name = extracted_entity.title() if extracted_entity else prompt
                    response_text = f"Waduh, data untuk **'{searched_name}'** tidak ditemukan di Google Sheet. Cek ejaan nama toko/reps ya bro."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
