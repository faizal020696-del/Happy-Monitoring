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

# Parser khusus transaksi mingguan (W1-W4) agar murni angka
def parse_number_transaction(val):
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'null', 'none', '', '-', ' - ', '0']:
        return 0.0
    cleaned = re.sub(r'[^0-9]', '', val_str)
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except Exception:
        return 0.0

# Parser presisi tinggi untuk kolom umum (CM, LM, L2M, L3M, DPD, Limit, dll)
def parse_number_general(val):
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'null', 'none', '', '-', ' - ']:
        return 0.0
    
    # Jika format di sheet mengandung format mata uang atau desimal desimal (misal 39,841.00 atau 39.841)
    # Kita bersihkan karakter selain angka, titik, dan koma
    cleaned = re.sub(r'[^0-9\,\.]', '', val_str)
    if not cleaned:
        return 0.0
    
    try:
        # Jika ada titik dan koma (format luar/lokal campuran)
        if '.' in cleaned and ',' in cleaned:
            if cleaned.rfind('.') < cleaned.rfind(','):
                # Format koma sebagai desimal (contoh: 39.841,50)
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # Format titik sebagai desimal (contoh: 39,841.50)
                cleaned = cleaned.replace(',', '')
        elif '.' in cleaned:
            parts = cleaned.split('.')
            # Jika titik lebih dari satu, asumsikan itu pemisah ribuan (contoh: 39.841.200)
            if len(parts) > 2:
                cleaned = "".join(parts)
            elif len(parts) == 2 and len(parts[1]) == 3:
                # Titik di belakang 3 digit seringkali adalah pemisah ribuan di format Indonesia (misal: 39.841)
                cleaned = "".join(parts)
        elif ',' in cleaned:
            parts = cleaned.split(',')
            if len(parts) > 2:
                cleaned = "".join(parts)
            elif len(parts) == 2 and len(parts[1]) <= 2:
                # Koma sebagai desimal (contoh: 39841,5)
                cleaned = cleaned.replace(',', '.')
            else:
                # Koma sebagai pemisah ribuan
                cleaned = cleaned.replace(',', '')
        
        val_float = float(cleaned)
        return val_float
    except Exception:
        # Fallback terakhir: ambil semua digit murninya saja jika gagal parsing
        digits_only = re.sub(r'[^0-9]', '', val_str)
        if digits_only:
            return float(digits_only)
        return 0.0

try:
    csv_url = convert_to_csv_url(SHEET_URL)
    res = requests.get(csv_url)
    csv_text = res.text
    lines = csv_text.splitlines()
    
    header_idx = 0
    for idx, line in enumerate(lines[:15]):
        line_lower = line.lower()
        if ('w1' in line_lower or 'week 1' in line_lower or 'dpd' in line_lower or 'limit' in line_lower or 'gmv' in line_lower or 'cm' in line_lower) and ('name' in line_lower or 'nama' in line_lower or 'apotek' in line_lower or 'toko' in line_lower):
            header_idx = idx
            break
            
    raw_df = pd.read_csv(io.StringIO(csv_text), skiprows=header_idx, dtype=str)
    raw_df.columns = [str(c).strip() for c in raw_df.columns]

    # Petakan kolom W1-W4 secara fleksibel
    week_cols_map = {}
    for col in raw_df.columns:
        col_lower = col.lower()
        if re.search(r'\bw[,\s_-]*1\b', col_lower) or 'week1' in col_lower or 'week 1' in col_lower or 'minggu1' in col_lower or 'minggu 1' in col_lower:
            week_cols_map['W1'] = col
        elif re.search(r'\bw[,\s_-]*2\b', col_lower) or 'week2' in col_lower or 'week 2' in col_lower or 'minggu2' in col_lower or 'minggu 2' in col_lower:
            week_cols_map['W2'] = col
        elif re.search(r'\bw[,\s_-]*3\b', col_lower) or 'week3' in col_lower or 'week 3' in col_lower or 'minggu3' in col_lower or 'minggu 3' in col_lower:
            week_cols_map['W3'] = col
        elif re.search(r'\bw[,\s_-]*4\b', col_lower) or 'week4' in col_lower or 'week 4' in col_lower or 'minggu4' in col_lower or 'minggu 4' in col_lower:
            week_cols_map['W4'] = col

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

        # Deteksi variasi minggu yang luas
        weeks_requested = []
        if re.search(r'\b(w1|week\s*1|week1|minggu\s*1|minggu1)\b', prompt_lower):
            weeks_requested.append('W1')
        if re.search(r'\b(w2|week\s*2|week2|minggu\s*2|minggu2)\b', prompt_lower):
            weeks_requested.append('W2')
        if re.search(r'\b(w3|week\s*3|week3|minggu\s*3|minggu3)\b', prompt_lower):
            weeks_requested.append('W3')
        if re.search(r'\b(w4|week\s*4|week4|minggu\s*4|minggu4)\b', prompt_lower):
            weeks_requested.append('W4')

        if ('wtu' in prompt_lower or 'transaksi' in prompt_lower) and not weeks_requested:
            if not any(k in prompt_lower for k in ['w1', 'w2', 'w3', 'w4', 'week', 'minggu', 'gmv', 'total', 'cm', 'lm', 'l2m', 'l3m']):
                weeks_requested = ['W1', 'W2', 'W3', 'W4']

        # Deteksi pencarian metrik khusus (CM, LM, L2M, L3M, Average, DPD, dll)
        metric_requested = None
        if not weeks_requested:
            if re.search(r'\bl3m\b', prompt_lower) and not 'average' in prompt_lower:
                for c in raw_df.columns:
                    if c.strip().lower() == 'l3m':
                        metric_requested = c
                        break
            elif re.search(r'\bl2m\b', prompt_lower):
                for c in raw_df.columns:
                    if c.strip().lower() == 'l2m':
                        metric_requested = c
                        break
            elif re.search(r'\blm\b', prompt_lower):
                for c in raw_df.columns:
                    if c.strip().lower() == 'lm':
                        metric_requested = c
                        break
            elif re.search(r'\bcm\b', prompt_lower) or 'bulan ini' in prompt_lower:
                for c in raw_df.columns:
                    if c.strip().lower() == 'cm':
                        metric_requested = c
                        break
            elif 'average' in prompt_lower or 'avg' in prompt_lower:
                for c in raw_df.columns:
                    if 'average' in c.lower() or 'avg' in c.lower():
                        metric_requested = c
                        break

            if not metric_requested:
                for c in raw_df.columns:
                    c_lower = c.lower()
                    if 'gmv' in prompt_lower and 'gmv' in c_lower and 'daily' not in c_lower:
                        metric_requested = c
                        break
                    elif 'total' in prompt_lower and 'total' in c_lower:
                        metric_requested = c
                        break
                    elif 'dpd' in prompt_lower and 'dpd' in c_lower:
                        metric_requested = c
                        break
                    elif 'limit' in prompt_lower and 'limit' in c_lower:
                        metric_requested = c
                        break

            if not metric_requested:
                for col in raw_df.columns:
                    col_lower = col.lower()
                    if col != name_col and col not in id_cols and col_lower in prompt_lower:
                        metric_requested = col
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

        # 2. Cari berdasarkan nama outlet
        if target_row is None:
            ignore_words = {
                'transaksi', 'wtu', 'w1', 'w2', 'w3', 'w4', 'week', 'week1', 'week2', 'week3', 'week4', 
                'minggu', 'minggu1', 'minggu2', 'minggu3', 'minggu4', '1', '2', '3', '4', 
                'berapa', 'total', 'jumlah', 'apotek', 'apotik', 'toko', 'cek', 'data', 'id', 'dpd', 'limit',
                'bulan', 'ini', 'kemarin', 'lalu', 'gmv', 'penjualan', 'omset', 'cm', 'lm', 'l2m', 'l3m', 'average', 'avg'
            }
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

                    if metric_requested:
                        val_raw = target_row.get(metric_requested, "Tidak tersedia")
                        val_parsed = parse_number_general(val_raw)
                        if isinstance(val_parsed, float):
                            if 'dpd' in metric_requested.lower():
                                val_str = f"{val_parsed:.0f}"
                            else:
                                val_str = f"Rp {val_parsed:,.0f}".replace(",", ".")
                        else:
                            val_str = str(val_raw)
                        calculated_metrics.append(f"• **{metric_requested}**: {val_str}")
                    else:
                        target_weeks = weeks_requested if weeks_requested else ['W1', 'W2', 'W3', 'W4']
                        for w in target_weeks:
                            if w in week_cols_map:
                                col_name = week_cols_map[w]
                                val_raw = target_row.get(col_name, 0)
                                val_parsed = parse_number_transaction(val_raw)
                                calculated_metrics.append(f"• **{w}**: Rp {val_parsed:,.0f}".replace(",", "."))

                    if calculated_metrics:
                        response_text = f"Data untuk **{str(display_name).title()}**:\n" + "\n".join(calculated_metrics)
                    else:
                        response_text = f"Data untuk kolom tersebut tidak ditemukan."
                else:
                    response_text = f"Data untuk pencarian tersebut tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
