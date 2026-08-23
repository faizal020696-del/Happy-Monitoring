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

def parse_number_exact(val):
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'null', 'none', '', '-', ' - ']:
        return 0.0

    cleaned = re.sub(r'[^0-9\,\.]', '', val_str)
    if not cleaned:
        return 0.0

    try:
        if '.' in cleaned and ',' in cleaned:
            if cleaned.rfind('.') < cleaned.rfind(','):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif '.' in cleaned:
            parts = cleaned.split('.')
            if len(parts) > 1:
                cleaned = cleaned.replace('.', '')
        elif ',' in cleaned:
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')

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
    
    # Normalisasi nama kolom agar persis W1, W2, W3, W4 tanpa angka di belakangnya
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
        
        # 1. Deteksi minggu apa saja yang diminta secara eksplisit
        weeks_requested = [w for w in ['W1', 'W2', 'W3', 'W4'] if re.search(r'\b' + w.lower() + r'\b', prompt_lower)]

        # 2. Buang kata kunci sampah dari prompt untuk murni mengambil nama toko/reps
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

        matched_indices = []
        entity_tokens = extracted_entity.split()

        if entity_tokens:
            # Hanya cari di kolom teks seperti 'Pharmacy Name' atau kolom nama/assignment agar aman
            name_cols = [c for c in raw_df.columns if any(k in c.lower() for k in ['name', 'nama', 'pharmacy', 'toko', 'apotek', 'assignment', 'reps'])]
            if not name_cols:
                name_cols = raw_df.columns

            for idx, row in raw_df[name_cols].iterrows():
                row_text = " ".join([str(val) for val in row.values if pd.notna(val)]).lower()
                if all(token in row_text for token in entity_tokens):
                    matched_indices.append(idx)
            
        sub_df = raw_df.loc[matched_indices] if matched_indices else pd.DataFrame(columns=raw_df.columns)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Mengecek data..."):
                if len(sub_df) > 0:
                    # 3. Tentukan kolom target secara presisi
                    target_columns = []
                    if weeks_requested:
                        target_columns = [w for w in weeks_requested if w in sub_df.columns]
                    
                    if not target_columns:
                        important_keys = ['GMV', 'CM', 'LM', 'L2M', 'L3M', 'Sales', 'Limit', 'DPD', 'Misi', 'Visit', 'Avg', 'Trx', 'W1', 'W2', 'W3', 'W4']
                        target_columns = [c for c in sub_df.columns if any(k.upper() == c.upper() for k in important_keys)]

                    target_columns = list(dict.fromkeys(target_columns))

                    calculated_metrics = []
                    for col in target_columns:
                        col_upper = col.upper()
                        if any(ignore in col_upper for ignore in ['ID', 'CODE', 'TELEPON', '%', 'NAMA', 'TOKO', 'APOTEK', 'ADDRESS', 'REPS', 'SALESMAN', 'UNNAMED']):
                            continue

                        series_vals = sub_df[col].dropna()
                        if not series_vals.empty:
                            val_raw = str(series_vals.iloc[-1]).strip()
                            if val_raw and val_raw.lower() not in ['nan', 'none', '']:
                                val_parsed = parse_number_exact(val_raw)
                                if val_parsed > 0 or col_upper in ['W1', 'W2', 'W3', 'W4', 'GMV', 'SALES', 'LIMIT']:
                                    calculated_metrics.append(f"• **{col}**: Rp {val_parsed:,.0f}".replace(",", "."))
                                else:
                                    calculated_metrics.append(f"• **{col}**: {val_raw}")
                            else:
                                calculated_metrics.append(f"• **{col}**: Rp 0")
                        else:
                            calculated_metrics.append(f"• **{col}**: Rp 0")

                    calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Data tidak ditemukan."

                    system_prompt = f"""
Kamu adalah Assistant Data SPV.
DATA UNTUK: '{extracted_entity.title()}'.
PERTANYAAN USER: "{prompt}"
HASIL KALKULASI:
{calc_summary_str}
Jawab langsung ke inti metrik yang diminta user secara rapi dan akurat berdasarkan hasil kalkulasi di atas.
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
