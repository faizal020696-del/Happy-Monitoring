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

def parse_number_clean(val):
    if pd.isna(val) or val is None:
        return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'null', 'none', '', '-', ' - ']:
        return None

    # Cek apakah nilai tersebut berupa teks biasa (bukan angka)
    cleaned = re.sub(r'[^0-9\,\.]', '', val_str)
    if not cleaned:
        return val_str # Kembalikan teks aslinya jika bukan angka (misal status atau nama)

    try:
        if '.' in cleaned and ',' in cleaned:
            if cleaned.rfind('.') < cleaned.rfind(','):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif '.' in cleaned:
            parts = cleaned.split('.')
            if len(parts) > 2:
                cleaned = "".join(parts[:-1]) + "." + parts[-1]
        elif ',' in cleaned:
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')

        return float(cleaned)
    except Exception:
        return val_str

try:
    csv_url = convert_to_csv_url(SHEET_URL)
    res = requests.get(csv_url)
    csv_text = res.text
    lines = csv_text.splitlines()
    
    header_idx = 0
    for idx, line in enumerate(lines[:15]):
        line_lower = line.lower()
        if ('w1' in line_lower or 'week 1' in line_lower or 'dpd' in line_lower or 'limit' in line_lower) and ('name' in line_lower or 'nama' in line_lower or 'apotek' in line_lower or 'toko' in line_lower):
            header_idx = idx
            break
            
    raw_df = pd.read_csv(io.StringIO(csv_text), skiprows=header_idx, dtype=str)
    raw_df.columns = [str(c).strip() for c in raw_df.columns]

    name_cols = [c for c in raw_df.columns if any(k in c.lower() for k in ['name', 'nama', 'pharmacy', 'toko', 'apotek'])]
    name_col = name_cols[0] if name_cols else raw_df.columns[0]
    
    id_cols = [c for c in raw_df.columns if 'id' in c.lower()]

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

        # Deteksi minggu (W1-W4)
        weeks_requested = [w for w in ['W1', 'W2', 'W3', 'W4'] if re.search(r'\b' + w.lower() + r'\b', prompt_lower)]
        
        # Deteksi kata kunci khusus lain seperti DPD, Limit, Status, dll.
        metric_requested = None
        for col in raw_df.columns:
            col_lower = col.lower()
            if col_lower in prompt_lower or any(kw in prompt_lower for kw in [col_lower, col_lower.replace(' ', '')]):
                if col != name_col and col not in id_cols:
                    metric_requested = col
                    break

        # Fallback manual jika keyword singkat (misal "dpd" atau "limit")
        if not metric_requested:
            if 'dpd' in prompt_lower:
                for c in raw_df.columns:
                    if 'dpd' in c.lower():
                        metric_requested = c
                        break
            elif 'limit' in prompt_lower:
                for c in raw_df.columns:
                    if 'limit' in c.lower():
                        metric_requested = c
                        break

        target_row = None
        
        # 1. Cari berdasarkan ID (4-6 digit)
        id_match_prompt = re.search(r'\b(\d{4,6})\b', prompt)
        if id_match_prompt and id_cols:
            search_id = id_match_prompt.group(1)
            for idx, row in raw_df.iterrows():
                for col in id_cols:
                    val_id = str(row.get(col, '')).strip()
                    if val_id == search_id:
                        target_row = row
                        break
                if target_row is not None:
                    break

        # 2. Cari berdasarkan nama toko di prompt
        if target_row is None:
            ignore_words = {'transaksi', 'w1', 'w2', 'w3', 'w4', 'berapa', 'total', 'jumlah', 'apotek', 'apotik', 'toko', 'cek', 'data', 'id', 'dpd', 'limit'}
            query_words = [w for w in re.findall(r'\b\w+\b', prompt_lower) if w not in ignore_words]
            
            if query_words:
                name_series = raw_df[name_col].fillna("").astype(str).str.lower()
                match_mask = name_series.apply(lambda x: all(qw in x for qw in query_words))
                matches = raw_df[match_mask]
                
                if not matches.empty:
                    target_row = matches.iloc[0]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Mengecek data..."):
                if target_row is not None:
                    display_name = target_row.get(name_col, "Outlet Ditemukan")
                    calculated_metrics = []

                    # Jika user menanyakan metrik spesifik (DPD / Limit / Kolom Lain)
                    if metric_requested:
                        val_raw = target_row.get(metric_requested, "Tidak tersedia")
                        val_parsed = parse_number_clean(val_raw)
                        if isinstance(val_parsed, float):
                            val_str = f"Rp {val_parsed:,.0f}".replace(",", ".")
                        else:
                            val_str = str(val_raw)
                        calculated_metrics.append(f"• **{metric_requested}**: {val_str}")

                    # Jika user meminta minggu W1-W4 atau tidak spesifik kolom
                    elif weeks_requested or not metric_requested:
                        target_weeks = weeks_requested if weeks_requested else [c for c in raw_df.columns if re.search(r'w[1-4]', c, re.IGNORECASE)]
                        for w in target_weeks:
                            # Cari kolom yang cocok
                            matching_cols = [c for c in raw_df.columns if w.lower() in c.lower()]
                            if matching_cols:
                                col_name = matching_cols[0]
                                val_raw = target_row.get(col_name, 0)
                                val_parsed = parse_number_clean(val_raw)
                                val_str = f"Rp {val_parsed:,.0f}".replace(",", ".") if isinstance(val_parsed, float) else str(val_raw)
                                calculated_metrics.append(f"• **{w}**: {val_str}")

                    if calculated_metrics:
                        response_text = f"Data untuk **{str(display_name).title()}**:\n" + "\n".join(calculated_metrics)
                    else:
                        response_text = f"Kolom data yang diminta tidak ditemukan untuk outlet **{str(display_name).title()}**."
                else:
                    response_text = f"Data untuk pencarian tersebut tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
