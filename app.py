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
        is_general_gmv_query = 'gmv' in prompt_lower and not weeks_requested and not is_limit_query and not is_mission_query and not is_wtu_query and not any(k in prompt_lower for k in ['lalu', 'kemarin', 'peak', 'l3m', 'l2m', 'cm', 'lm', 'average', 'avg'])

        command_words = {
            'cek', 'data', 'id', 'berapa', 'total', 'jumlah', 'w1', 'w2', 'w3', 'w4', 
            'transaksi', 'tolong', 'visit', 'kunjungan', 'misi', 'gold', 'mission',
            'campaign', 'type', 'start', 'date', 'duration', 'target', 'level', 'gmv', 
            'ppn', 'gap', 'hna', 'pencapaian', 'kekurangan', 'info', 'apotek', 'toko', 'wtu',
            'sisa', 'limit', 'avg', 'l3m', 'reps', 'sales', 'pic', 'bulan', 'ini', 'dpd', 'plafond'
        }

        target_row = None
        matched_reps_df = None
        matched_reps_name = None

        is_sales_query = 'reps' in prompt_lower or 'sales' in prompt_lower or 'pic' in prompt_lower
        
        if not is_sales_query and reps_col:
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

        if matched_reps_df is None or matched_reps_df.empty:
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
                outlet_query_words = [w for w in re.findall(r'\b\w+\b', prompt_lower) if w not in command_words]
                if outlet_query_words:
                    name_series = raw_df[name_col].fillna("").astype(str).str.lower()
                    scores = []
                    for idx, name_val in name_series.items():
                        score = sum(1 for qw in outlet_query_words if qw in name_val)
                        if all(qw in name_val for qw in outlet_query_words):
                            score += 10
                        scores.append((score, idx))
                    scores.sort(key=lambda x: x[0], reverse=True)
                    best_score, best_idx = scores[0]
                    if best_score > 0:
                        target_row = raw_df.loc[best_idx]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Mengecek data..."):
                if matched_reps_df is not None and not matched_reps_df.empty:
                    total_outlets = len(matched_reps_df)
                    calculated_metrics = [f"• **Jumlah Outlet**: {total_outlets} outlet"]

                    cm_col = next((c for c in raw_df.columns if c.strip().lower() == 'cm'), None)
                    lm_col = next((c for c in raw_df.columns if c.strip().lower() == 'lm'), None)
                    l2m_col = next((c for c in raw_df.columns if c.strip().lower() == 'l2m'), None)
                    l3m_col = next((c for c in raw_df.columns if c.strip().lower() == 'l3m'), None)
                    avg_col = next((c for c in raw_df.columns if ('average' in c.lower() or 'avg' in c.lower()) and 'l3m' in c.lower()), None)
                    if not avg_col:
                        avg_col = next((c for c in raw_df.columns if 'average' in c.lower() or 'avg' in c.lower()), None)

                    if is_limit_query:
                        limit_cols = [c for c in raw_df.columns if any(term in c.lower() for term in ['limit', 'plafond', 'sisa', 'avail'])]
                        for col in limit_cols:
                            sum_val = sum(parse_number_general(r.get(col, 0)) for _, r in matched_reps_df.iterrows())
                            calculated_metrics.append(f"• **Total {col}**: Rp {sum_val:,.0f}".replace(",", "."))
                    elif is_mission_query:
                        mission_cols = [c for c in raw_df.columns if any(term in c.lower() for term in ['misi', 'gold', 'mission', 'campaign'])]
                        for col in mission_cols:
                            calculated_metrics.append(f"• **Kolom {col}**: (Data rekap misi sales rep)")
                    elif is_wtu_query:
                        wtu_cols = [c for c in raw_df.columns if any(term in c.lower() for term in ['wtu', 'visit', 'kunjungan'])]
                        if wtu_cols:
                            calculated_metrics.append("\n**📋 Data WTU / Kunjungan:**")
                            for col in wtu_cols:
                                sum_val = sum(parse_number_general(r.get(col, 0)) for _, r in matched_reps_df.iterrows())
                                val_formatted = f"{sum_val:,.0f}".replace(",", ".") if sum_val > 0 else "Cek detail sheet"
                                calculated_metrics.append(f"• **Total {col}**: {val_formatted}")
                        else:
                            calculated_metrics.append("• Kolom WTU / visit tidak ditemukan pada sheet.")
                    else:
                        calculated_metrics.append("\n**📊 Total Performa Bulanan:**")
                        target_cols_gmv = [
                            ("CM (Bulan Ini)", cm_col),
                            ("LM (Bulan Lalu)", lm_col),
                            ("L2M", l2m_col),
                            ("L3M", l3m_col),
                            ("Average / AVG L3M", avg_col)
                        ]
                        for label, col in target_cols_gmv:
                            if col:
                                sum_val = sum(parse_number_general(r.get(col, 0)) for _, r in matched_reps_df.iterrows())
                                calculated_metrics.append(f"• **Total {label}**: Rp {sum_val:,.0f}".replace(",", "."))

                        calculated_metrics.append("\n**📅 Total Performa Per Week (Mingguan & Jumlah Outlet Transaksi):**")
                        for w in ['W1', 'W2', 'W3', 'W4']:
                            if w in week_cols_map:
                                col_name = week_cols_map[w]
                                sum_w = sum(parse_number_transaction(r.get(col_name, 0)) for _, r in matched_reps_df.iterrows())
                                active_outlets = sum(1 for _, r in matched_reps_df.iterrows() if parse_number_transaction(r.get(col_name, 0)) > 0)
                                calculated_metrics.append(f"• **Total {w}**: Rp {sum_w:,.0f} ({active_outlets} outlet transaksi)".replace(",", "."))

                    response_text = f"Rekap Total untuk Sales Rep **{str(matched_reps_name).title()}**:\n" + "\n".join(calculated_metrics)

                elif target_row is not None:
                    display_name = target_row.get(name_col, "Outlet Ditemukan")
                    calculated_metrics = []

                    if is_limit_query:
                        limit_cols = [c for c in raw_df.columns if any(term in c.lower() for term in ['limit', 'plafond', 'sisa', 'avail'])]
                        if limit_cols:
                            for col in limit_cols:
                                val_metric = target_row.get(col, "-")
                                val_parsed = parse_number_general(val_metric)
                                val_formatted = f"Rp {val_parsed:,.0f}".replace(",", ".") if val_parsed > 0 else val_metric
                                calculated_metrics.append(f"• **{col}**: {val_formatted}")
                        else:
                            calculated_metrics.append("• Kolom limit/sisa limit tidak ditemukan pada sheet.")
                    elif is_mission_query:
                        mission_cols = [c for c in raw_df.columns if any(term in c.lower() for term in ['misi', 'gold', 'mission', 'campaign'])]
                        if mission_cols:
                            calculated_metrics.append("**🎯 Informasi Campaign Misi:**")
                            for col in mission_cols:
                                c_lower = col.lower()
                                val_metric = str(target_row.get(col, "-")).strip()
                                val_parsed = parse_number_general(val_metric)
                                if val_parsed > 0 and any(kw in c_lower for kw in ['target', 'gmv', 'gap', 'hna']):
                                    val_formatted = f"Rp {val_parsed:,.0f}".replace(",", ".")
                                else:
                                    val_formatted = val_metric

                                if 'gold' in c_lower and len(calculated_metrics) > 0 and "**🏆 Target & Pencapaian Gold Misi:**" not in calculated_metrics:
                                    calculated_metrics.append("\n**🏆 Target & Pencapaian Gold Misi:**")
                                
                                calculated_metrics.append(f"• **{col}**: {val_formatted}")
                        else:
                            calculated_metrics.append("• Kolom misi/gold tidak ditemukan pada sheet.")
                    elif is_wtu_query:
                        wtu_cols = [c for c in raw_df.columns if any(term in c.lower() for term in ['wtu', 'visit', 'kunjungan'])]
                        if wtu_cols:
                            for col in wtu_cols:
                                val_metric = target_row.get(col, "-")
                                calculated_metrics.append(f"• **{col}**: {val_metric}")
                        else:
                            calculated_metrics.append("• Kolom WTU / visit tidak ditemukan pada sheet.")
                    else:
                        metric_requested = None
                        if 'dpd' in prompt_lower:
                            metric_requested = next((c for c in raw_df.columns if 'dpd' in c.lower()), None)
                        elif any(k in prompt_lower for k in ['visit', 'kunjungan']):
                            metric_requested = next((c for c in raw_df.columns if 'visit' in c.lower() or 'kunjungan' in c.lower()), None)

                        if metric_requested:
                            val_metric = target_row.get(metric_requested, "-")
                            val_parsed = parse_number_general(val_metric)
                            val_formatted = f"Rp {val_parsed:,.0f}".replace(",", ".") if val_parsed > 0 and any(k in metric_requested.lower() for k in ['amount', 'rp']) else val_metric
                            calculated_metrics.append(f"• **{metric_requested}**: {val_formatted}")
                        else:
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

                    response_text = f"Data untuk **{str(display_name).title()}**:\n" + "\n".join(calculated_metrics)
                else:
                    response_text = f"Data untuk pencarian tersebut tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
