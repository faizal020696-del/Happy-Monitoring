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
        if ('w1' in line_lower or 'week 1' in line_lower or 'dpd' in line_lower or 'limit' in line_lower or 'gmv' in line_lower or 'cm' in line_lower or 'target' in line_lower or 'visit' in line_lower) and ('name' in line_lower or 'nama' in line_lower or 'apotek' in line_lower or 'toko' in line_lower):
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
            if not any(k in prompt_lower for k in ['w1', 'w2', 'w3', 'w4', 'week', 'minggu', 'gmv', 'total', 'cm', 'lm', 'l2m', 'l3m', 'lalu', 'kemarin', 'sisa', 'limit', 'avg', 'average', 'target', 'visit', 'last', 'terakhir']):
                weeks_requested = ['W1', 'W2', 'W3', 'W4']

        is_limit_query = any(k in prompt_lower for k in ['limit', 'plafond', 'sisa', 'ssisa', 'avaiability', 'availability', 'avail']) and not weeks_requested
        is_general_gmv_query = 'gmv' in prompt_lower and not weeks_requested and not is_limit_query and not any(k in prompt_lower for k in ['lalu', 'kemarin', 'peak', 'l3m', 'l2m', 'cm', 'lm', 'average', 'avg'])
        
        # Deteksi query terkait visit (Target Visit / Visit Count / Last Visit)
        is_visit_query = any(k in prompt_lower for k in ['target visit', 'visit count', 'visit', 'kunjungan', 'last visit', 'terakhir']) and not weeks_requested

        metric_requested = None
        if not weeks_requested and not is_limit_query and not is_general_gmv_query and not is_visit_query:
            if 'avg' in prompt_lower or 'average' in prompt_lower:
                for c in raw_df.columns:
                    c_low = c.lower()
                    if ('average' in c_low or 'avg' in c_low) and 'l3m' in c_low:
                        metric_requested = c
                        break
                if not metric_requested:
                    for c in raw_df.columns:
                        if 'average' in c.lower() or 'avg' in c.lower():
                            metric_requested = c
                            break
            elif re.search(r'\bl3m\b', prompt_lower) and not 'average' in prompt_lower and not 'avg' in prompt_lower:
                for c in raw_df.columns:
                    if c.strip().lower() == 'l3m':
                        metric_requested = c
                        break
            elif re.search(r'\bl2m\b', prompt_lower):
                for c in raw_df.columns:
                    if c.strip().lower() == 'l2m':
                        metric_requested = c
                        break
            elif re.search(r'\blm\b', prompt_lower) or 'lalu' in prompt_lower or 'kemarin' in prompt_lower:
                for c in raw_df.columns:
                    if c.strip().lower() == 'lm':
                        metric_requested = c
                        break
            elif re.search(r'\bcm\b', prompt_lower) or 'bulan ini' in prompt_lower:
                for c in raw_df.columns:
                    if c.strip().lower() == 'cm':
                        metric_requested = c
                        break

            if not metric_requested:
                for c in raw_df.columns:
                    c_lower = c.lower()
                    if 'gmv' in prompt_lower and 'gmv' in c_lower and 'daily' not in c_lower:
                        metric_requested = c
                        break
                    elif 'dpd' in prompt_lower and 'dpd' in c_lower:
                        metric_requested = c
                        break

            if not metric_requested:
                for col in raw_df.columns:
                    col_lower = col.lower()
                    if col != name_col and col not in id_cols and col_lower in prompt_lower:
                        metric_requested = col
                        break

        target_row = None
        
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
            ignore_words = {
                'transaksi', 'wtu', 'w1', 'w2', 'w3', 'w4', 'week', 'week1', 'week2', 'week3', 'week4', 
                'minggu', 'minggu1', 'minggu2', 'minggu3', 'minggu4', '1', '2', '3', '4', 
                'berapa', 'total', 'jumlah', 'apotek', 'apotik', 'toko', 'cek', 'data', 'id', 'dpd', 'limit', 'sisa', 'ssisa',
                'bulan', 'ini', 'kemarin', 'lalu', 'gmv', 'penjualan', 'omset', 'cm', 'lm', 'l2m', 'l3m', 'average', 'avg',
                'target', 'visit', 'count', 'last', 'terakhir'
            }
            query_words = [w for w in re.findall(r'\b\w+\b', prompt_lower) if w not in ignore_words]
            query_words = ['gebang' if w == 'gabang' else w for w in query_words]
            
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

                    if is_limit_query:
                        total_limit_col = next((c for c in raw_df.columns if 'total' in c.lower() and 'limit' in c.lower()), None)
                        avail_limit_col = next((c for c in raw_df.columns if c != total_limit_col and ('limit' in c.lower() or 'sisa' in c.lower() or 'avail' in c.lower() or 'plafond' in c.lower())), None)

                        if total_limit_col:
                            val_total = parse_number_general(target_row.get(total_limit_col, 0))
                            calculated_metrics.append(f"• **{total_limit_col}**: Rp {val_total:,.0f}".replace(",", "."))
                        if avail_limit_col:
                            val_avail = parse_number_general(target_row.get(avail_limit_col, 0))
                            calculated_metrics.append(f"• **{avail_limit_col}**: Rp {val_avail:,.0f}".replace(",", "."))
                        
                        if not calculated_metrics:
                            calculated_metrics.append("Data limit tidak ditemukan di kolom sheet.")

                    elif is_general_gmv_query:
                        cm_col = next((c for c in raw_df.columns if c.strip().lower() == 'cm'), None)
                        lm_col = next((c for c in raw_df.columns if c.strip().lower() == 'lm'), None)
                        l2m_col = next((c for c in raw_df.columns if c.strip().lower() == 'l2m'), None)
                        l3m_col = next((c for c in raw_df.columns if c.strip().lower() == 'l3m'), None)
                        avg_col = next((c for c in raw_df.columns if ('average' in c.lower() or 'avg' in c.lower()) and 'l3m' in c.lower()), None)
                        if not avg_col:
                            avg_col = next((c for c in raw_df.columns if 'average' in c.lower() or 'avg' in c.lower()), None)

                        calculated_metrics.append("**📊 Performa Bulanan:**")
                        target_cols_gmv = [
                            ("CM (Bulan Ini)", cm_col),
                            ("LM (Bulan Lalu)", lm_col),
                            ("L2M", l2m_col),
                            ("L3M", l3m_col),
                            ("Average / AVG L3M", avg_col)
                        ]

                        for label, col in target_cols_gmv:
                            if col:
                                val_parsed = parse_number_general(target_row.get(col, 0))
                                calculated_metrics.append(f"• **{label}**: Rp {val_parsed:,.0f}".replace(",", "."))

                        calculated_metrics.append("\n**📅 Performa Per Week (Mingguan):**")
                        for w in ['W1', 'W2', 'W3', 'W4']:
                            if w in week_cols_map:
                                col_name = week_cols_map[w]
                                val_raw = target_row.get(col_name, 0)
                                val_parsed = parse_number_transaction(val_raw)
                                calculated_metrics.append(f"• **{w}**: Rp {val_parsed:,.0f}".replace(",", "."))

                        if not calculated_metrics:
                            calculated_metrics.append("Data ringkasan GMV tidak ditemukan di kolom sheet.")

                    elif is_visit_query:
                        target_visit_col = next((c for c in raw_df.columns if 'target' in c.lower() and 'visit' in c.lower()), None)
                        visit_count_col = next((c for c in raw_df.columns if 'visit count' in c.lower() or ('visit' in c.lower() and 'cm' in c.lower())), None)
                        if not visit_count_col:
                            visit_count_col = next((c for c in raw_df.columns if c != target_visit_col and 'visit' in c.lower() and 'last' not in c.lower()), None)
                        
                        # Deteksi kolom Last Visit / Visit Terakhir
                        last_visit_col = next((c for c in raw_df.columns if ('last' in c.lower() and 'visit' in c.lower()) or 'terakhir' in c.lower() or ('visit' in c.lower() and ('date' in c.lower() or 'tanggal' in c.lower()))), None)

                        calculated_metrics.append("**📍 Performa & Riwayat Kunjungan (Visit):**")
                        if target_visit_col:
                            val_target = parse_number_general(target_row.get(target_visit_col, 0))
                            calculated_metrics.append(f"• **{target_visit_col}**: {val_target:,.0f}".replace(",", "."))
                        if visit_count_col:
                            val_count = parse_number_general(target_row.get(visit_count_col, 0))
                            calculated_metrics.append(f"• **{visit_count_col}**: {val_count:,.0f}".replace(",", "."))
                        if last_visit_col:
                            val_last = target_row.get(last_visit_col, "-")
                            calculated_metrics.append(f"• **{last_visit_col}**: {val_last}")
                        
                        if not target_visit_col and not visit_count_col and not last_visit_col:
                            calculated_metrics.append("Data Target Visit, Visit Count, atau Last Visit tidak ditemukan di kolom sheet.")

                    elif metric_requested:
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
