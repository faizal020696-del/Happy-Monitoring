import streamlit as st
import pandas as pd
from openai import OpenAI
import re
import io
import requests

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

def parse_number_exact(val, is_dpd=False):
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'null', 'none', '', '-', ' - ']:
        return 0.0

    if is_dpd:
        match = re.search(r'(-?\d+(?:\.\d+)?)', val_str.replace(',', '.'))
        if match:
            return float(match.group(1))
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
        elif '.' in cleaned and '.' not in cleaned:
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
    
    res = requests.get(csv_url)
    csv_text = res.text
    lines = csv_text.splitlines()
    
    header_idx = 0
    for idx, line in enumerate(lines[:10]):
        if any(k in line.lower() for k in ['pharmacy name', 'nama toko', 'nama apotek', 'swiperx id', 'assignment']):
            header_idx = idx
            break
            
    raw_df = pd.read_csv(io.StringIO(csv_text), skiprows=header_idx, dtype=str)
    
    # Clean nama kolom
    new_cols = []
    for c in raw_df.columns:
        c_clean = str(c).strip()
        w_match = re.search(r'\b(w[1-4])\b', c_clean, re.IGNORECASE)
        if w_match:
            new_cols.append(w_match.group(1).upper())
        else:
            new_cols.append(c_clean)
    raw_df.columns = new_cols

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

        # --- 1. DETEKSI METRIK / INTENT ---
        detected_intents = []
        
        weeks_requested = [w for w in ['w1', 'w2', 'w3', 'w4'] if re.search(r'\b' + w + r'\b', prompt_lower)]
        if weeks_requested:
            detected_intents.append('weekly')

        if any(k in prompt_lower for k in ['1st', 'awal', 'pertama']):
            detected_intents.append('first_trx')
        if any(k in prompt_lower for k in ['last', 'terakhir', 'terbaru', 'paling baru']):
            detected_intents.append('last_trx')
        if 'l3m' in prompt_lower:
            detected_intents.append('l3m')
        if 'l2m' in prompt_lower:
            detected_intents.append('l2m')
        if any(k in prompt_lower for k in ['average', 'avg', 'rata-rata', '3 bulan', '3 bln']):
            detected_intents.append('average')
        if any(k in prompt_lower for k in ['bulan ini', 'cm', 'current month', 'bln ini']):
            detected_intents.append('cm')
        if any(k in prompt_lower for k in ['bulan lalu', 'lm', 'last month', 'bln lalu', 'kemarin', 'kemaren']):
            detected_intents.append('lm')
        if any(k in prompt_lower for k in ['target visit', 'target kunjungan']):
            detected_intents.append('target_visit')
        elif any(k in prompt_lower for k in ['visit', 'kunjungan']):
            detected_intents.append('visit')
        if any(k in prompt_lower for k in ['misi', 'mission', 'reguler', 'gold']):
            detected_intents.append('misi')
        if 'dpd' in prompt_lower:
            detected_intents.append('dpd')
        if any(k in prompt_lower for k in ['limit', 'plafon', 'kredit', 'availability', 'avaibility']):
            detected_intents.append('limit')
        if any(k in prompt_lower for k in ['gmv', 'omset', 'sales', 'penjualan', 'pencapaian', 'capaian', 'total gmv']):
            detected_intents.append('gmv')

        # --- 2. EXTRACTION NAMA PURE DENGAN REGEX SAPU BERSIH ---
        clean_prompt = prompt_lower
        clean_prompt = re.sub(r'\bdi([a-z]+)', r'\1', clean_prompt)

        junk_words = [
            r'\bberapa\b', r'\btotal\b', r'\bjumlah\b', r'\byang\b', r'\btersedia\b', r'\bada\b', 
            r'\btarget\b', r'\bvisit\b', r'\bkunjungan\b', r'\breps\b', r'\bsales\b', r'\bsalesman\b', 
            r'\blimit\b', r'\bplafon\b', r'\bdpd\b', r'\bmisi\b', r'\bmission\b', r'\bgold\b', r'\breguler\b',
            r'\bgmv\b', r'\bomset\b', r'\bdi\b', r'\bapotek\b', r'\bapotik\b', r'\btoko\b', r'\boutlet\b', 
            r'\bpt\b', r'\bcv\b', r'\bdata\b', r'\buntuk\b', r'\bbulan\b', r'\bini\b', r'\blalu\b', 
            r'\bni\b', r'\binih\b', r'\bkah\b', r'\bdong\b', r'\bcek\b', r'\binfo\b', r'\bpencapaian\b', 
            r'\bcapaian\b', r'\bperforma\b', r'\bhasil\b', r'\barea\b', r'\bmana\b', r'\byg\b', 
            r'\bsudah\b', r'\btransaksi\b', r'\bw1\b', r'\bw2\b', r'\bw3\b', r'\bw4\b',
            r'\baverage\b', r'\bavg\b', r'\brata-rata\b', r'\bratarata\b', r'\b3\b', r'\bbln\b',
            r'\bl3m\b', r'\bl2m\b', r'\blm\b', r'\bcm\b', r'\bdan\b', r'\bdan2\b',
            r'\bkemarin\b', r'\bkemaren\b', r'\bkemarin2\b', r'\bkemaren2\b',
            r'\bawal\b', r'\bpertama\b', r'\bterakhir\b', r'\bterbaru\b', r'\b1st\b', r'\blast\b', r'\btrx\b', r'\bdate\b', r'\btanggal\b',
            r'\bkapan\b', r'\bkapan2\b', r'\btgl\b'
        ]

        for junk in junk_words:
            clean_prompt = re.sub(junk, ' ', clean_prompt)

        clean_prompt = re.sub(r'[^\w\s]', ' ', clean_prompt)
        extracted_entity = " ".join(clean_prompt.split()).strip()

        # --- 3. MATCHING NAMA PURE LOOP (BEBAS ERROR .str) ---
        entity_tokens = extracted_entity.split()
        matched_rows = []

        if entity_tokens:
            ignored_cols = [c for c in raw_df.columns if any(k in c.lower() for k in ['alamat', 'address', 'jalan', 'kota'])]
            searchable_cols = [c for c in raw_df.columns if c not in ignored_cols]

            for _, r_item in raw_df[searchable_cols].fillna("").astype(str).iterrows():
                row_str = " ".join(r_item.values).lower()
                if all(t in row_str for t in entity_tokens):
                    matched_rows.append(r_item.name)
            
        sub_df = raw_df.loc[matched_rows] if matched_rows else pd.DataFrame(columns=raw_df.columns)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Mengecek data..."):
                if len(sub_df) > 0:
                    target_columns = []

                    if 'weekly' in detected_intents:
                        for w in weeks_requested:
                            target_columns.extend([c for c in sub_df.columns if re.search(r'\b' + w + r'\b', c.lower())])

                    elif 'first_trx' in detected_intents or 'last_trx' in detected_intents:
                        if 'first_trx' in detected_intents:
                            target_columns.extend([c for c in sub_df.columns if ('1st' in c.lower() or 'first' in c.lower()) and ('trx' in c.lower() or 'date' in c.lower())])
                        if 'last_trx' in detected_intents:
                            target_columns.extend([c for c in sub_df.columns if 'last' in c.lower() and ('trx' in c.lower() or 'date' in c.lower())])

                    elif 'l3m' in detected_intents or 'l2m' in detected_intents:
                        if 'l3m' in detected_intents:
                            target_columns.extend([c for c in sub_df.columns if c.lower() == 'l3m'])
                        if 'l2m' in detected_intents:
                            target_columns.extend([c for c in sub_df.columns if c.lower() == 'l2m'])

                    elif 'average' in detected_intents:
                        target_columns = [c for c in sub_df.columns if 'average' in c.lower() or 'avg' in c.lower()]

                    elif 'lm' in detected_intents:
                        target_columns = [c for c in sub_df.columns if c.lower() in ['lm', 'last month']]

                    elif 'cm' in detected_intents:
                        target_columns = [c for c in sub_df.columns if c.lower() in ['cm', 'current month']]

                    elif 'target_visit' in detected_intents:
                        target_columns = [c for c in sub_df.columns if 'target' in c.lower() and 'visit' in c.lower()]
                    elif 'visit' in detected_intents:
                        target_columns = [c for c in sub_df.columns if 'visit' in c.lower() or 'kunjungan' in c.lower()]
                    elif 'misi' in detected_intents:
                        if 'gold' in prompt_lower:
                            target_columns = [c for c in sub_df.columns if 'gold' in c.lower()]
                        elif 'reguler' in prompt_lower:
                            target_columns = [c for c in sub_df.columns if 'reguler' in c.lower()]
                        if not target_columns:
                            target_columns = [c for c in sub_df.columns if 'misi' in c.lower()]
                    elif 'dpd' in prompt_lower:
                        target_columns = [c for c in sub_df.columns if 'dpd' in c.lower()]
                    elif 'limit' in detected_intents:
                        target_columns = [c for c in sub_df.columns if 'limit' in c.lower() or 'plafon' in c.lower()]
                    elif 'gmv' in detected_intents:
                        target_columns = [c for c in sub_df.columns if 'gmv' in c.lower()]

                    if not target_columns:
                        important_keys = ['gmv', 'cm', 'lm', 'l2m', 'l3m', 'sales', 'limit', 'dpd', 'misi', 'visit', 'avg', 'average', 'trx', 'date', 'w1', 'w2', 'w3', 'w4']
                        target_columns = [c for c in sub_df.columns if any(k in c.lower() for k in important_keys)]

                    target_columns = list(dict.fromkeys(target_columns))

                    calculated_metrics = []
                    for col in target_columns:
                        col_lower = col.lower()
                        if any(ignore in col_lower for ignore in ['id', 'code', 'telepon', '%', 'nama', 'toko', 'apotek', 'address', 'sales rep', 'reps', 'salesman', 'unnamed']):
                            continue

                        if any(k in col_lower for k in ['date', 'trx', 'tanggal', 'misi', 'gold', 'reguler', 'status', 'tier']):
                            valid_rows = sub_df[sub_df[col].notna() & (sub_df[col].astype(str).str.strip() != '')]
                            if not valid_rows.empty:
                                val_raw = valid_rows[col].iloc[-1]
                                calculated_metrics.append(f"• **{col}**: {str(val_raw).strip()}")
                            else:
                                calculated_metrics.append(f"• **{col}**: -")

                        elif 'dpd' in col_lower:
                            valid_rows = sub_df[sub_df[col].notna() & (sub_df[col].astype(str).str.strip() != '')]
                            if not valid_rows.empty:
                                val_raw = valid_rows[col].iloc[-1]
                                val_parsed = parse_number_exact(val_raw, is_dpd=True)
                                calculated_metrics.append(f"• **{col}**: {val_parsed:.0f} hari")
                            else:
                                calculated_metrics.append(f"• **{col}**: 0 hari")

                        elif any(k in col_lower for k in ['limit', 'plafon', 'avaibility', 'availability', 'avg', 'average', 'l3m', 'l2m', 'lm', 'cm', 'w1', 'w2', 'w3', 'w4']):
                            valid_rows = sub_df[sub_df[col].notna() & (sub_df[col].astype(str).str.strip() != '')]
                            if not valid_rows.empty:
                                val_raw = valid_rows[col].iloc[-1]
                                val_parsed = parse_number_exact(val_raw, is_dpd=False)
                                calculated_metrics.append(f"• **{col}**: Rp {val_parsed:,.0f}".replace(",", "."))
                            else:
                                calculated_metrics.append(f"• **{col}**: Rp 0")

                        elif any(k in col_lower for k in ['visit', 'kunjungan', 'count', 'target']):
                            num_series = sub_df[col].apply(lambda x: parse_number_exact(x, is_dpd=False))
                            total_val = num_series.sum()
                            calculated_metrics.append(f"• **{col}**: {total_val:,.0f} kali".replace(",", "."))

                        else:
                            num_series = sub_df[col].apply(lambda x: parse_number_exact(x, is_dpd=False))
                            total_val = num_series.sum()
                            calculated_metrics.append(f"• **{col}**: Rp {total_val:,.0f}".replace(",", "."))

                    calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Metrik tidak terdeteksi di sheet."

                    system_prompt = f"""
Kamu adalah Assistant Data SPV.

DATA UNTUK: '{extracted_entity.title()}'.
PERTANYAAN USER: "{prompt}"

HASIL KALKULASI PRESISI:
{calc_summary_str}

Instruksi Direct:
1. Jawab LANGSUNG ke inti pertanyaan tanpa salam berbelit-belit.
2. Tampilkan HANYA angka metrik yang diminta user.
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
