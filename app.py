import streamlit as st
import pandas as pd
from openai import OpenAI
import re
import json

OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
SHEET_URL = st.secrets["SHEET_URL"]

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
    if not val_str or val_str.lower() in ['nan', 'null', 'none', '-', '']:
        return 0.0

    cleaned = re.sub(r'[^0-9\,\.-]', '', val_str)
    if not cleaned:
        return 0.0

    try:
        if '.' in cleaned and ',' in cleaned:
            if cleaned.rfind('.') < cleaned.rfind(','):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned and '.' not in cleaned:
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif '.' in cleaned and ',' not in cleaned:
            parts = cleaned.split('.')
            if len(parts) > 2:
                cleaned = cleaned.replace('.', '')
            elif len(parts) == 2:
                if len(parts[1]) == 3 or len(parts[1]) != 2:
                    cleaned = cleaned.replace('.', '')

        return float(cleaned)
    except Exception:
        return 0.0

try:
    csv_url = convert_to_csv_url(SHEET_URL)
    df = pd.read_csv(csv_url, dtype=str)
    df.columns = df.columns.str.strip()
    df_clean_text = df.fillna("").astype(str)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

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

        # --- 1. GUNAKAN AI UNTUK EKSTRAKSI NAMA PURE & INTENT ---
        ner_prompt = f"""
Tugasmu adalah menganalisis pertanyaan user dan mengembalikan JSON dengan format murni.

Kolom yang tersedia di Sheet: {list(df.columns)}
Pertanyaan User: "{prompt}"

Keluarkan format JSON persis seperti ini (tanpa markdown ```json):
{{
    "target_name": "NAMA_TOKO_ATAU_REPS_SAJA",
    "target_type": "apotek" atau "reps" atau "unknown",
    "requested_metrics": ["kata_kunci_kolom_yang_diminta"],
    "is_filter_query": true/false
}}

Aturan:
- `target_name`: Hanya ambil MURNI nama apotek atau nama reps. BUANG semua kata tanya, kata depan (di, diapotek), kata minggu (W1, W2, W4), dan nama metrik (target, visit, gmv, pencapaian, transaksi).
- Contoh 1: "berapa target visit diapotek gebang farma?" -> target_name: "gebang farma", requested_metrics: ["visit"]
- Contoh 2: "berapa pencapaian gmv apotek gebang farma w4?" -> target_name: "gebang farma", requested_metrics: ["gmv", "w4"]
- Contoh 3: "area Reps Afrianto apotek mana yg sudah transaksi di W4?" -> target_name: "afrianto", target_type: "reps", requested_metrics: ["w4", "transaksi"], is_filter_query: true
"""

        extracted_entity = ""
        requested_metrics = []
        is_filter_query = False

        try:
            ner_res = client.chat.completions.create(
                model="google/gemini-2.0-flash-lite-001:free",
                messages=[{"role": "user", "content": ner_prompt}],
                temperature=0.0
            )
            raw_json = ner_res.choices[0].message.content.strip()
            raw_json = re.sub(r'```json\s*|\s*```', '', raw_json)
            parsed_data = json.loads(raw_json)
            
            extracted_entity = parsed_data.get("target_name", "").strip()
            requested_metrics = parsed_data.get("requested_metrics", [])
            is_filter_query = parsed_data.get("is_filter_query", False)
        except Exception:
            extracted_entity = prompt

        # --- 2. PENULUSURAN DATA BERDASARKAN HASIL EKSTRAKSI AI ---
        sub_df = pd.DataFrame()
        if extracted_entity:
            entity_tokens = extracted_entity.lower().split()
            ignored_cols = [c for c in df.columns if any(k in c.lower() for k in ['alamat', 'address', 'jalan', 'kota'])]
            searchable_cols = [c for c in df.columns if c not in ignored_cols]

            pattern = r'\b' + r'\b.*\b'.join([re.escape(t) for t in entity_tokens]) + r'\b'
            series_clean = df_clean_text[searchable_cols].apply(lambda row: " ".join(row.values).lower(), axis=1)
            sub_df = df[series_clean.str.contains(pattern, regex=True, na=False)]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Mengecek data..."):
                if len(sub_df) > 0:
                    
                    # CASE A: Pertanyaan berbentuk Filter/List (Misal: "Apotek mana aja yg udah transaksi di W4")
                    if is_filter_query and any(k in c.lower() for c in df.columns for k in requested_metrics):
                        # Cari kolom metrik transaksi W4
                        target_col = [c for c in df.columns if any(m.lower() in c.lower() for m in requested_metrics)]
                        name_col = [c for c in df.columns if any(k in c.lower() for k in ['toko', 'apotek', 'outlet', 'customer'])][0]
                        
                        sub_df['val_check'] = sub_df[target_col[0]].apply(parse_number_exact)
                        transacted_outlets = sub_df[sub_df['val_check'] > 0][name_col].tolist()

                        if transacted_outlets:
                            outlets_formatted = "\n".join([f"{i+1}. {out}" for i, out in enumerate(transacted_outlets)])
                            response_text = f"Berikut daftar apotek under **{extracted_entity.title()}** yang sudah bertransaksi di {target_col[0]}:\n\n{outlets_formatted}"
                        else:
                            response_text = f"Belum ada apotek under **{extracted_entity.title()}** yang bertransaksi di {target_col[0]}."

                    # CASE B: Pertanyaan Angka / Metrik Biasa
                    else:
                        target_columns = []
                        if requested_metrics:
                            for col in sub_df.columns:
                                if any(m.lower() in col.lower() for m in requested_metrics):
                                    target_columns.append(col)

                        if not target_columns:
                            target_columns = [c for c in sub_df.columns if any(k in c.lower() for k in ['gmv', 'cm', 'lm', 'sales', 'limit', 'dpd', 'visit', 'target'])]

                        calculated_metrics = []
                        for col in target_columns:
                            col_lower = col.lower()
                            if any(ignore in col_lower for ignore in ['id', 'code', 'telepon', '%', 'nama', 'toko', 'apotek', 'address']):
                                continue

                            num_series = sub_df[col].apply(parse_number_exact)
                            total_val = num_series.sum()

                            if 'dpd' in col_lower:
                                calculated_metrics.append(f"• **{col}**: {num_series.mean():.0f} hari")
                            elif any(k in col_lower for k in ['visit', 'kunjungan', 'count', 'target visit']):
                                calculated_metrics.append(f"• **{col}**: {total_val:,.0f} kali".replace(",", "."))
                            else:
                                calculated_metrics.append(f"• **{col}**: Rp {total_val:,.0f}".replace(",", "."))

                        calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Metrik tidak ditemukan di sheet."

                        system_prompt = f"""
Kamu adalah Assistant Data SPV.

DATA UNTUK: '{extracted_entity.title()}'.
PERTANYAAN USER: "{prompt}"

HASIL KALKULASI PRESISI:
{calc_summary_str}

Instruksi Direct:
1. Jawab LANGSUNG ke inti pertanyaan tanpa salam berbelit-belit.
2. Tampilkan HANYA angka metrik yang relevan dengan pertanyaan user.
"""
                        try:
                            completion = client.chat.completions.create(
                                model="google/gemini-2.0-flash-lite-001:free",
                                messages=[{"role": "user", "content": system_prompt}],
                                temperature=0.0
                            )
                            response_text = completion.choices[0].message.content.strip()
                        except Exception:
                            response_text = f"Data **{extracted_entity.title()}**:\n{calc_summary_str}"

                else:
                    searched_name = extracted_entity.title() if extracted_entity else prompt
                    response_text = f"Waduh, data untuk **'{searched_name}'** tidak ditemukan di Google Sheet. Cek ejaan nama toko/reps ya bro."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
