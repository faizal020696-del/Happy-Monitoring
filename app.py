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

def parse_number_general(val):
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
            if len(parts) > 2:
                cleaned = "".join(parts)
            elif len(parts) == 2 and len(parts[1]) == 3:
                cleaned = "".join(parts)
        elif ',' in cleaned:
            parts = cleaned.split(',')
            if len(parts) > 2:
                cleaned = "".join(parts)
            elif len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        
        val_float = float(cleaned)
        return val_float
    except Exception:
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
        if ('w1' in line_lower or 'week 1' in line_lower or 'dpd' in line_lower or 'limit' in line_lower or 'gmv' in line_lower or 'cm' in line_lower or 'target' in line_lower or 'visit' in line_lower or 'misi' in line_lower or 'wtu' in line_lower) and ('name' in line_lower or 'nama' in line_lower or 'apotek' in line_lower or 'toko' in line_lower or 'sales' in line_lower):
            header_idx = idx
            break
            
    raw_df = pd.read_csv(io.StringIO(csv_text), skiprows=header_idx, dtype=str)
    raw_df.columns = [str(c).strip() for c in raw_df.columns]

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
    
    reps_cols = [c for c in raw_df.columns if c.lower() in ['sales rep', 'salesrep', 'sales reps', 'reps', 'sales', 'pic']]
    if not reps_cols:
        reps_cols = [c for c in raw_df.columns if 'sales' in c.lower() or 'reps' in c.lower() or 'pic' in c.lower()]
    reps_col = reps_cols[0] if reps_cols else None

    # Deteksi kolom Daily GMV secara spesifik dari master sheet
    daily_gmv_col = next((c for c in raw_df.columns if 'daily gmv' in c.lower() or 'dayli gmv' in c.lower()), None)

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Halo SPV! 👋 Ada data outlet atau sales rep yang mau dicek hari ini?"}
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

        weeks_requested = []
        if re.search(r'\b(w1|week\s*1|week1|minggu\s*1|minggu1)\b', prompt_lower):
            weeks_requested.append('W1')
        if re.search(r'\b(w2|week\s*2|week2|minggu\s*2|minggu2)\b', prompt_lower):
            weeks_requested.append('W2')
        if re.search(r'\b(w3|week\s*3|week3|minggu\s*3|minggu3)\b', prompt_lower):
            weeks_requested.append('W3')
        if re.search(r'\b(w4|week\s*4|week4|minggu\s*4|minggu4)\b', prompt_lower):
            weeks_requested.append('W4')

        is_limit_query = any(k in prompt_lower for k in ['limit', 'plafond', 'sisa', 'ssisa', 'avaiability', 'availability', 'avail']) and not weeks_requested
        is_mission_query = any(k in prompt_lower for k in ['misi', 'gold', 'mission', 'campaign', 'pencapaian misi']) and not weeks_requested
        is_wtu_query = any(k in prompt_lower for k in ['wtu', 'visit', 'kunjungan']) and not weeks_requested
        
        is_total_gmv_query = (any(k in prompt_lower for k in ['total', 'semua', 'all']) and ('gmv' in prompt_lower or 'dayli' in prompt_lower or 'daily' in prompt_lower)) or prompt_lower.strip() in ['dayli gmv total', 'daily gmv total', 'total gmv', 'total daily gmv']:

        command_words = {
            'cek', 'data', 'id', 'berapa', 'total', 'jumlah', 'w1', 'w2', 'w3', 'w4', 
            'transaksi', 'tolong', 'visit', 'kunjungan', 'misi', 'gold', 'mission',
            'campaign', 'type', 'start', 'date', 'duration', 'target', 'level', 'gmv', 
            'ppn', 'gap', 'hna', 'pencapaian', 'kekurangan', 'info', 'apotek', 'toko', 'wtu',
            'sisa', 'limit', 'avg', 'l3m', 'reps', 'sales', 'pic', 'bulan', 'ini', 'dpd', 'plafond',
            'dayli', 'daily', 'semua', 'list', 'dan', 'nya'
        }

        target_row = None
        matched_reps_df = None
        matched_reps_name = None

        is_sales_query = 'reps' in prompt_lower or 'sales' in prompt_lower or 'pic' in prompt_lower
        
        if not is_sales_query and not is_total_gmv_query and reps_col:
            unique_reps = raw_df[reps_col].dropna().astype(str).unique()
            for r in unique_reps:
                r_clean = r.strip().lower()
                if r_clean and len(r_clean) > 2 and r_clean in prompt_lower and not any(kw in prompt_lower for kw in ['apotek', 'toko']):
                    is_sales_query = True
                    break

        if is_sales_query and reps_col:
            unique_reps = raw_df[reps_col].dropna().astype(str).unique()
            for r in unique_reps:
                r_clean = r.strip().lower()
                if r_clean and r_clean in prompt_lower:
                    matched_reps_name = r
                    matched_reps_df = raw_df[raw_df[reps_col].astype(str).str.strip().str.lower() == r_clean]
                    break
            
            if matched_reps_df is None or matched_reps_df.empty:
                for r in unique_reps:
                    r_clean = r.strip().lower()
                    if r_clean and len(r_clean) > 2 and r_clean in prompt_lower:
                        matched_reps_name = r
                        matched_reps_df = raw_df[raw_df[reps_col].astype(str).str.strip().str.lower() == r_clean]
                        break

        if not is_total_gmv_query and (matched_reps_df is None or matched_reps_df.empty):
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

            if target_row is None:
                outlet_query_words = [w for w in re.findall(r'\b\w+\b', prompt_lower) if w not in command_words and w not in ['apotek', 'toko', 'farma']]
                if not outlet_query_words:
                    outlet_query_words = [w for w in re.findall(r'\b\w+\b', prompt_lower) if w not in command_words]
                
                if outlet_query_words:
                    name_series = raw_df[name_col].fillna("").astype(str).str.lower()
                    scores = []
                    for idx, name_val in name_series.items():
                        if any(qw in name_val for qw in outlet_query_words):
                            score = sum(3 for qw in outlet_query_words if qw in name_val)
                            if all(qw in name_val for qw in outlet_query_words):
                                score += 20
                            scores.append((score, idx))
                    
                    if scores:
                        scores.sort(key=lambda x: x[0], reverse=True)
                        best_score, best_idx = scores[0]
                        target_row = raw_df.loc[best_idx]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Mengecek data..."):
                if is_total_gmv_query:
                    total_outlets = len(raw_df)
                    calculated_metrics = [f"• **Total Keseluruhan Outlet**: {total_outlets} outlet\n"]
                    
                    if daily_gmv_col:
                        sum_daily = sum(parse_number_general(r.get(daily_gmv_col, 0)) for _, r in raw_df.iterrows())
                        calculated_metrics.append(f"• **Total Daily GMV (Keseluruhan)**: Rp {sum_daily:,.0f}".replace(",", "."))
                    
                    cm_col = next((c for c in raw_df.columns if c.strip().lower() == 'cm'), None)
                    if cm_col:
                        sum_cm = sum(parse_number_general(r.get(cm_col, 0)) for _, r in raw_df.iterrows())
                        calculated_metrics.append(f"• **Total CM (Bulan Ini)**: Rp {sum_cm:,.0f}".replace(",", "."))

                    if 'list' in prompt_lower or 'apotek' in prompt_lower:
                        calculated_metrics.append("\n**📋 Daftar Apotek & Daily GMV:**")
                        for idx, r in raw_df.iterrows():
                            out_name = r.get(name_col, f"Baris {idx+1}")
                            daily_val = parse_number_general(r.get(daily_gmv_col, 0)) if daily_gmv_col else 0
                            calculated_metrics.append(f"- {out_name} (Daily GMV: Rp {daily_val:,.0f})".replace(",", "."))

                    response_text = "Rekap Total Keseluruhan:\n\n" + "\n".join(calculated_metrics)

                elif matched_reps_df is not None and not matched_reps_df.empty:
                    total_outlets = len(matched_reps_df)
                    calculated_metrics = [f"• **Jumlah Outlet**: {total_outlets} outlet"]

                    if daily_gmv_col:
                        sum_daily = sum(parse_number_general(r.get(daily_gmv_col, 0)) for _, r in matched_reps_df.iterrows())
                        calculated_metrics.append(f"• **Total Daily GMV**: Rp {sum_daily:,.0f}".replace(",", "."))

                    response_text = f"Rekap Total untuk Sales Rep **{str(matched_reps_name).title()}**:\n" + "\n".join(calculated_metrics)

                elif target_row is not None:
                    display_name = target_row.get(name_col, "Outlet Ditemukan")
                    calculated_metrics = []

                    if daily_gmv_col:
                        val_daily = parse_number_general(target_row.get(daily_gmv_col, 0))
                        calculated_metrics.append(f"• **Daily GMV**: Rp {val_daily:,.0f}".replace(",", "."))

                    response_text = f"Data untuk **{str(display_name).title()}**:\n\n" + "\n".join(calculated_metrics)
                else:
                    response_text = f"Data untuk pencarian tersebut tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
