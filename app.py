import streamlit as st
import pandas as pd
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
    
    # Normalisasi nama kolom
    new_cols = []
    for c in raw_df.columns:
        c_clean = str(c).strip()
        w_match = re.search(r'\b(w[1-4])\b', c_clean, re.IGNORECASE)
        if w_match:
            new_cols.append(w_match.group(1).upper())
        else:
            new_cols.append(c_clean)
    raw_df.columns = new_cols

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
        weeks_requested = [w for w in ['W1', 'W2', 'W3', 'W4'] if re.search(r'\b' + w.lower() + r'\b', prompt_lower)]

        clean_prompt = prompt_lower
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
            r'\bl3m\b', r'\bl2m\b', r'\blm\b', r'\bcm\b', r'\bdan\b', r'\bkapan\b', r'\btgl\b'
        ]
        for junk in junk_words:
            clean_prompt = re.sub(junk, ' ', clean_prompt)

        clean_prompt = re.sub(r'[^\w\s]', ' ', clean_prompt)
        extracted_entity = " ".join(clean_prompt.split()).strip()
        if not extracted_entity:
            extracted_entity = prompt

        matched_indices = []
        name_cols = [c for c in raw_df.columns if any(k in c.lower() for k in ['name', 'nama', 'pharmacy', 'toko', 'apotek'])]
        if not name_cols:
            name_cols = raw_df.columns

        search_tokens = [t for t in extracted_entity.split() if len(t) > 2]
        if not search_tokens:
            search_tokens = extracted_entity.split()

        for idx, row in raw_df[name_cols].iterrows():
            row_text = " ".join([str(val) for val in row.values if pd.notna(val)]).lower()
            if search_tokens and all(token in row_text for token in search_tokens):
                # Validasi tambahan: abaikan baris yang terindikasi sebagai total/summary wilayah besar jika ada baris outlet detailnya
                matched_indices.append(idx)

        # Filter baris: Jika ada banyak baris yang cocok, buang baris yang nilai W1-nya tidak masuk akal (diatas 1 miliar misal, atau baris pertama jika itu rekap)
        valid_indices = []
        for idx in matched_indices:
            row_data = raw_df.loc[idx]
            # Cek nilai W1 untuk memastikan ini bukan baris rekap triliunan
            w1_val = parse_number_exact(row_data.get('W1', 0))
            if w1_val < 1_000_000_000: # Asumsi transaksi mingguan toko normal di bawah 1 miliar
                valid_indices.append(idx)
        
        # Jika semua terfilter habis (atau memang angkanya besar), ambil baris terakhir dari hasil pencocokan (biasanya baris detail ada di bawah rekap)
        if not valid_indices and matched_indices:
            valid_indices = [matched_indices[-1]]
        elif not valid_indices:
            valid_indices = matched_indices

        sub_df = raw_df.loc[valid_indices] if valid_indices else pd.DataFrame(columns=raw_df.columns)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Mengecek data..."):
                if len(sub_df) > 0:
                    target_columns = []
                    if weeks_requested:
                        target_columns = [w for w in weeks_requested if w in sub_df.columns]
                    
                    if not target_columns:
                        target_columns = ['W1', 'W2', 'W3', 'W4']

                    target_columns = [c for c in target_columns if c in sub_df.columns]

                    calculated_metrics = []
                    target_row = sub_df.iloc[0]
                    display_name = target_row.get(name_cols[0], extracted_entity.title())

                    for col in target_columns:
                        val_raw = str(target_row.get(col, '')).strip()
                        val_parsed = parse_number_exact(val_raw)
                        calculated_metrics.append(f"• **{col}**: Rp {val_parsed:,.0f}".replace(",", "."))

                    calc_summary_str = "\n".join(calculated_metrics)
                    response_text = f"Data untuk **{str(display_name).title()}**:\n{calc_summary_str}"

                else:
                    response_text = f"Waduh, data untuk **'{extracted_entity.title()}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
