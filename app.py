prompt_lower = prompt.lower()

        # --- 1. DETEKSI INTENT PERTANYAAN (PRESISI) ---
        detected_intents = []
        
        is_cm = any(k in prompt_lower for k in ['bulan ini', 'cm', 'current month', 'bln ini'])
        is_lm = any(k in prompt_lower for k in ['bulan lalu', 'lm', 'last month', 'bln lalu'])
        is_misi = any(k in prompt_lower for k in ['misi', 'mission', 'reguler', 'gold', 'campaign'])
        
        if is_cm:
            detected_intents.append('cm')
        elif is_lm:
            detected_intents.append('lm')
            
        if is_misi:
            detected_intents.append('misi')
        elif 'dpd' in prompt_lower:
            detected_intents.append('dpd')
        elif any(k in prompt_lower for k in ['limit', 'plafon', 'kredit', 'avaibility']):
            detected_intents.append('limit')
        elif any(k in prompt_lower for k in ['visit', 'kunjungan']):
            detected_intents.append('visit')
        elif any(k in prompt_lower for k in ['gmv', 'omset', 'sales', 'penjualan', 'pencapaian', 'capaian']) and not is_misi:
            detected_intents.append('gmv')

        # --- 2. EXTRACTION NAMA TOKO / REPS (DENGAN TAMBAHAN KATA SAPU BERSIH) ---
        clean_prompt = prompt_lower

        # Hapus imbuhan "di" di awal kata (misal: "diapotek" -> "apotek", "dibulan" -> "bulan")
        clean_prompt = re.sub(r'\bdi([a-z]+)', r'\1', clean_prompt)
        
        # Tambahkan 'pencapaian', 'capaian', 'performa', 'hasil' ke junk words
        junk_patterns = [
            r'\bberapa\b', r'\btotal\b', r'\bjumlah\b', r'\byang\b', r'\btersedia\b', r'\bada\b', 
            r'\bkunjungan\b', r'\breps\b', r'\bsales\b', r'\bsalesman\b', r'\blimit\b', r'\bplafon\b',
            r'\bdpd\b', r'\bmisi\b', r'\bmission\b', r'\bgmv\b', r'\bomset\b', r'\bdi\b', r'\bapotek\b', 
            r'\bapotik\b', r'\btoko\b', r'\boutlet\b', r'\bpt\b', r'\bcv\b', r'\bdata\b', r'\buntuk\b', 
            r'\bbulan\b', r'\bini\b', r'\blalu\b', r'\bni\b', r'\binih\b', r'\bkah\b', r'\bdong\b', 
            r'\bcek\b', r'\binfo\b', r'\bpencapaian\b', r'\bcapaian\b', r'\bperforma\b', r'\bhasil\b'
        ]
        
        for junk in junk_patterns:
            clean_prompt = re.sub(junk, ' ', clean_prompt)
            
        clean_prompt = re.sub(r'[^\w\s]', ' ', clean_prompt)
        extracted_entity = " ".join(clean_prompt.split()).strip()

        entity_tokens = extracted_entity.split()
        sub_df = pd.DataFrame()

        if entity_tokens:
            ignored_cols = [c for c in df.columns if any(k in c.lower() for k in ['alamat', 'address', 'jalan', 'kota'])]
            searchable_cols = [c for c in df.columns if c not in ignored_cols]

            pattern = r'\b' + r'\b.*\b'.join([re.escape(t) for t in entity_tokens]) + r'\b'
            series_clean = df_clean_text[searchable_cols].apply(lambda row: " ".join(row.values).lower(), axis=1)
            sub_df = df[series_clean.str.contains(pattern, regex=True, na=False)]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Mengecek data..."):
                if len(sub_df) > 0:
                    target_columns = []

                    # --- 3. FILTERING KOLOM KHUSUS (ON-POINT KUNCI MISI) ---
                    if 'misi' in detected_intents:
                        # Hanya ambil kolom yang ADA KATA "MISI"
                        target_columns = [c for c in sub_df.columns if 'misi' in c.lower()]
                    elif 'cm' in detected_intents:
                        target_columns = [c for c in sub_df.columns if c.lower() == 'cm' or 'cm' in c.lower()]
                    elif 'lm' in detected_intents:
                        target_columns = [c for c in sub_df.columns if c.lower() == 'lm' or 'lm' in c.lower()]
                    elif 'dpd' in detected_intents:
                        target_columns = [c for c in sub_df.columns if 'dpd' in c.lower()]
                    elif 'limit' in detected_intents:
                        target_columns = [c for c in sub_df.columns if 'limit' in c.lower()]
                    elif 'visit' in detected_intents:
                        target_columns = [c for c in sub_df.columns if 'visit' in c.lower() or 'kunjungan' in c.lower()]
                    elif 'gmv' in detected_intents:
                        target_columns = [c for c in sub_df.columns if any(k in c.lower() for k in ['gmv', 'sales'])]

                    # Fallback jika user hanya minta data umum tanpa kata kunci metrik
                    if not target_columns:
                        important_keys = ['gmv', 'cm', 'lm', 'sales', 'limit', 'dpd', 'misi']
                        target_columns = [c for c in sub_df.columns if any(k in c.lower() for k in important_keys)]

                    calculated_metrics = []
                    for col in target_columns:
                        col_lower = col.lower()
                        if any(ignore in col_lower for ignore in ['id', 'code', 'telepon', '%', 'nama', 'toko', 'apotek', 'address']):
                            continue

                        num_series = sub_df[col].apply(parse_number_exact)
                        total_val = num_series.sum()

                        if 'dpd' in col_lower:
                            calculated_metrics.append(f"• **{col}**: {num_series.mean():.0f} hari")
                        elif any(k in col_lower for k in ['visit', 'kunjungan', 'count']):
                            calculated_metrics.append(f"• **{col}**: {total_val:,.0f} kali".replace(",", "."))
                        else:
                            calculated_metrics.append(f"• **{col}**: Rp {total_val:,.0f}".replace(",", "."))

                    calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Metrik misi tidak terdeteksi di sheet."

                    system_prompt = f"""
Kamu adalah Assistant Data SPV.

DATA UNTUK: '{extracted_entity.title()}'.
PERTANYAAN USER: "{prompt}"

HASIL KALKULASI PRESISI:
{calc_summary_str}

Instruksi Ringkas & Direct:
1. Jawab LANGSUNG ke inti pertanyaan tanpa salam berbelit-belit.
2. Tampilkan HANYA angka metrik yang diminta user. JANGAN menampilkan data yang tidak berhubungan dengan intent pertanyaan!
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
