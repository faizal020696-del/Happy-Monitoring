# --- 1. CEK PENCARIAN BERDASARKAN SPV ---
        is_spv_query = 'spv' in prompt_lower or 'supervisor' in prompt_lower
        if not is_spv_query and spv_col:
            unique_spvs = raw_df[spv_col].dropna().astype(str).unique()
            for s in unique_spvs:
                s_clean = s.strip().lower()
                if s_clean and len(s_clean) > 2 and s_clean in prompt_lower and not any(kw in prompt_lower for kw in ['apotek', 'toko']):
                    is_spv_query = True
                    break

        if is_spv_query and spv_col:
            unique_spvs = raw_df[spv_col].dropna().astype(str).unique()
            for s in unique_spvs:
                s_clean = s.strip().lower()
                if s_clean and s_clean in prompt_lower:
                    matched_spv_name = s
                    matched_spv_df = raw_df[raw_df[spv_col].astype(str).str.strip().str.lower() == s_clean]
                    break
            
            if matched_spv_df is None or matched_spv_df.empty:
                for s in unique_spvs:
                    s_clean = s.strip().lower()
                    if s_clean and len(s_clean) > 2 and s_clean in prompt_lower:
                        matched_spv_name = s
                        matched_spv_df = raw_df[raw_df[spv_col].astype(str).str.strip().str.lower() == s_clean]
                        break

        # --- 2. CEK PENCARIAN BERDASARKAN SALES REPS (Jika bukan SPV) ---
        if matched_spv_df is None or matched_spv_df.empty:
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

        # --- 3. CEK PENCARIAN OUTLET / ID ---
        if (matched_spv_df is None or matched_spv_df.empty) and (matched_reps_df is None or matched_reps_df.empty):
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
                # --- JIKA YANG KETEMU SPV ---
                if matched_spv_df is not None and not matched_spv_df.empty:
                    total_outlets = len(matched_spv_df)
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
                            sum_val = sum(parse_number_general(r.get(col, 0)) for _, r in matched_spv_df.iterrows())
                            calculated_metrics.append(f"• **Total {col}**: Rp {sum_val:,.0f}".replace(",", "."))
                    elif is_wtu_query:
                        calculated_metrics.append("\n**📅 Total Performa Per Week (Mingguan & Jumlah Outlet Transaksi):**")
                        for w in ['W1', 'W2', 'W3', 'W4']:
                            if w in week_cols_map:
                                col_name = week_cols_map[w]
                                sum_w = sum(parse_number_transaction(r.get(col_name, 0)) for _, r in matched_spv_df.iterrows())
                                active_outlets = sum(1 for _, r in matched_spv_df.iterrows() if parse_number_transaction(r.get(col_name, 0)) > 0)
                                calculated_metrics.append(f"• **Total {w}**: Rp {sum_w:,.0f} ({active_outlets} outlet transaksi)".replace(",", "."))
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
                                sum_val = sum(parse_number_general(r.get(col, 0)) for _, r in matched_spv_df.iterrows())
                                calculated_metrics.append(f"• **Total {label}**: Rp {sum_val:,.0f}".replace(",", "."))

                        calculated_metrics.append("\n**📅 Total Performa Per Week (Mingguan & Jumlah Outlet Transaksi):**")
                        for w in ['W1', 'W2', 'W3', 'W4']:
                            if w in week_cols_map:
                                col_name = week_cols_map[w]
                                sum_w = sum(parse_number_transaction(r.get(col_name, 0)) for _, r in matched_spv_df.iterrows())
                                active_outlets = sum(1 for _, r in matched_spv_df.iterrows() if parse_number_transaction(r.get(col_name, 0)) > 0)
                                calculated_metrics.append(f"• **Total {w}**: Rp {sum_w:,.0f} ({active_outlets} outlet transaksi)".replace(",", "."))

                    response_text = f"Rekap Total untuk SPV **{str(matched_spv_name).title()}**:\n" + "\n".join(calculated_metrics)

                # --- JIKA YANG KETEMU SALES REPS ---
                elif matched_reps_df is not None and not matched_reps_df.empty:
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
                    elif is_wtu_query:
                        calculated_metrics.append("\n**📅 Total Performa Per Week (Mingguan & Jumlah Outlet Transaksi):**")
                        for w in ['W1', 'W2', 'W3', 'W4']:
                            if w in week_cols_map:
                                col_name = week_cols_map[w]
                                sum_w = sum(parse_number_transaction(r.get(col_name, 0)) for _, r in matched_reps_df.iterrows())
                                active_outlets = sum(1 for _, r in matched_reps_df.iterrows() if parse_number_transaction(r.get(col_name, 0)) > 0)
                                calculated_metrics.append(f"• **Total {w}**: Rp {sum_w:,.0f} ({active_outlets} outlet transaksi)".replace(",", "."))
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

                # --- JIKA YANG KETEMU OUTLET TUNGGAL ---
                elif target_row is not None:
                    display_name = target_row.get(name_col, "Outlet Ditemukan")
                    calculated_metrics = []

                    if is_limit_query:
                        limit_cols = [c for c in raw_df.columns if any(term in c.lower() for term in ['limit', 'plafond', 'sisa', 'avail'])]
                        for col in limit_cols:
                            val_metric = target_row.get(col, "-")
                            val_parsed = parse_number_general(val_metric)
                            val_formatted = f"Rp {val_parsed:,.0f}".replace(",", ".") if val_parsed > 0 else val_metric
                            calculated_metrics.append(f"• **{col}**: {val_formatted}")
                    elif is_mission_query:
                        mission_cols = [c for c in raw_df.columns if any(term in c.lower() for term in ['misi', 'gold', 'mission', 'campaign'])]
                        if not mission_cols:
                            mission_cols = [c for c in raw_df.columns if 'misi' in c.lower() or 'mission' in c.lower()]
                        
                        if mission_cols:
                            calculated_metrics.append("**🎯 Status Misi / Campaign:**")
                            for col in mission_cols:
                                val_misi = target_row.get(col, "-")
                                calculated_metrics.append(f"• **{col}**: {val_misi}")
                        else:
                            calculated_metrics.append("Data kolom misi tidak ditemukan di sheet.")
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

                    response_text = f"Data untuk **{str(display_name).title()}**:\n\n" + "\n".join(calculated_metrics)
                else:
                    response_text = f"Data untuk pencarian tersebut tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})
