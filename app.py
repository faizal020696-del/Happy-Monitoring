# Kunci kolom Reps dan Status Transaksi (sesuaikan string 'status' jika ada kolom status di sheet kamu)
reps_cols = [c for c in df.columns if any(k in c.lower() for k in ['reps', 'sales', 'nama reps'])]

if prompt := st.chat_input("Tanyakan sesuatu terkait data universe..."):
    # ... (bagian penanganan UI tetap sama) ...

    prompt_lower = prompt.lower()
    
    # 1. Tentukan Nama Reps yang Dicari
    target_reps = None
    for name in ['sulistiana', 'afrianto', 'rizki', 'gde', 'mulyanto']:
        if name in prompt_lower:
            target_reps = name
            break

    # 2. Filter Data Transaksi Valid
    filtered_df = df.copy()

    # Jika di sheet ada kolom Status (misal: Completed, Success, Paid), filter hanya yang valid:
    status_cols = [c for c in df.columns if 'status' in c.lower()]
    if status_cols:
        s_col = status_cols[0]
        # Hanya ambil transaksi yang BUKAN Canceled / Failed / Cancel
        filtered_df = filtered_df[~filtered_df[s_col].astype(str).str.lower().isin(['canceled', 'cancel', 'failed', 'batal'])]

    # Filter berdasarkan Reps
    if target_reps and reps_cols:
        r_col = reps_cols[0]
        # Filter HANYA pada kolom Reps (bukan cari di seluruh kolom apotek/catatan)
        filtered_df = filtered_df[filtered_df[r_col].astype(str).str.lower().str.contains(target_reps)]

    # 3. Hitung GMV ACH
    gmv_cols = [c for c in df.columns if any(k in c.lower() for k in ['gmv', 'ach', 'total harga', 'nominal'])]
    
    if len(filtered_df) > 0 and gmv_cols:
        gmv_col = gmv_cols[0]
        total_gmv = filtered_df[gmv_col].apply(parse_number_exact).sum()
        
        # Tampilkan langsung hasil kalkulasi yang sudah difilter
        response_text = f"Total pencapaian GMV **{target_reps.title() if target_reps else 'Team'}** adalah **Rp {total_gmv:,.0f}**.".replace(",", ".")
    else:
        response_text = "Data transaksi tidak ditemukan atau filter tidak cocok."
