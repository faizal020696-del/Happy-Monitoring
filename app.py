# --- EKSTRAKSI ENTITAS NAMA DENGAN AI (KEBAL TYPO) ---
        extraction_prompt = f"""
Ekstrak HANYA nama subjek/entitas utama (nama Reps/Sales/Apotek/Toko) dari pertanyaan user di bawah.
Abaikan kata tanya, kata kerja, typo/salah ketik, istilah metrik (seperti gmv, pencapian, pencapaian, total, target, dll), dan keterangan waktu (seperti bulan ini, kemarin, dll).

Contoh:
Input: "berapa total pencapian GMV reps rizki bulan ini?" -> Output: rizki
Input: "berapa total pencapian GMV reps afrianto bulan ini?" -> Output: afrianto
Input: "pencapaian sales afrianto" -> Output: afrianto

Kalimat Input: "{prompt}"
Output (HANYA NAMA ENTITAS):"""

        extracted_entity = ""
        try:
            ext_res = client.chat.completions.create(
                model="google/gemini-2.0-flash-lite-001:free",
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.0
            )
            extracted_entity = ext_res.choices[0].message.content.strip().lower()
            extracted_entity = re.sub(r'[^\w\s]', '', extracted_entity)
        except Exception:
            extracted_entity = ""

        # Fallback manual jika ekstraksi AI gagal / offline
        if not extracted_entity:
            clean_prompt = re.sub(r'[^\w\s]', ' ', prompt.lower())
            stop_words = set([
                'berapa', 'total', 'gmv', 'pencapaian', 'pencapian', 'capaian', 'misi', 'reguler', 'gold', 
                'target', 'data', 'untuk', 'bulan', 'ini', 'kemarin', 'di', 'dan', 'yang', 
                'dari', 'tentang', 'tim', 'gw', 'saya', 'tolong', 'coba', 'reps', 'sales', 
                'apotek', 'apotik', 'toko', 'outlet', 'seberapa', 'banyak', 'pt', 'cv'
            ])
            entity_tokens = [w for w in clean_prompt.split() if w not in stop_words and len(w) > 1]
            extracted_entity = " ".join(entity_tokens)
