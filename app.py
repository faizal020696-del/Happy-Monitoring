import streamlit as st
import pandas as pd
import re
import io
import requests

SHEET_URL = st.secrets.get("SHEET_URL", "")

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
    
    # Normalisasi nama kolom W1 - W4
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

        name_cols = [c for c in raw_df.columns if any(k in c.lower() for k in ['name', 'nama', 'pharmacy', 'toko', 'apotek'])]
        name_col = name_cols[0] if name_cols else raw_df.columns[0]

        ignore_words = {'transaksi', 'w1', 'w2', 'w3', 'w4', 'berapa', 'total', 'jumlah', 'apotek', 'apotik', 'toko', 'cek', 'data'}
        words = [w for w in re.findall(r'\b\w+\b', prompt_lower) if w not in ignore_words]
        
        target_row = None

        if words:
            name_series = raw_df[name_col].fillna("").astype(str).str.lower()
            
            # Filter buang baris yang mengandung kata wilayah rekap (sangiang, periuk, total, dll)
            not_summary_filter = ~name_series.str.contains('sangiang|periuk|total|region|all area', regex=True)
            
            # Cari baris yang mengandung SEMUA kata kunci dan bukan baris rekap
            matches = raw_df[name_series.apply(lambda x: all(w in x for w in words)) & not_summary_filter]
            if not matches.empty:
                target_row = matches.iloc[0]
            else:
                # Cari baris yang mengandung SETIDAKNYA satu kata kunci dan bukan baris rekap
                matches = raw_df[name_series.apply(lambda x: any(w in x for w in words)) & not_summary_filter]
                if not matches.empty:
                    target_row = matches.iloc[0]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Mengecek data..."):
                if target_row is not None:
                    display_name = target_row.get(name_col, "Outlet Ditemukan")
                    target_columns = weeks_requested if weeks_requested else ['W1', 'W2', 'W3', 'W4']
                    target_columns = [c for c in target_columns if c in raw_df.columns]

                    calculated_metrics = []
                    for col in target_columns:
                        val_raw = str(target_row.get(col, '')).strip()
                        val_parsed = parse_number_exact(val_raw)
                        calculated_metrics.append(f"• **{col}**: Rp {val_parsed:,.0f}".replace(",", "."))

                    response_text = f"Data untuk **{str(display_name).title()}**:\n" + "\n".join(calculated_metrics)
                else:
                    response_text = f"Data untuk pencarian **'{prompt}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
