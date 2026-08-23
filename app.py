import streamlit as st
import pandas as pd
from openai import OpenAI
import re

OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
SHEET_URL = st.secrets["SHEET_URL"]

st.set_page_config(page_title="Chatbot Universe SPV Happy", page_icon="🤖", layout="centered")

def convert_to_csv_url(url):
    sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if not sheet_id_match: return None
    sheet_id = sheet_id_match.group(1)
    gid_match = re.search(r'[#&?]gid=([0-9]+)', url)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

def parse_number_exact(val):
    if pd.isna(val) or val is None: return 0.0
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'null', 'none', '-', '']: return 0.0
    cleaned = re.sub(r'[^0-9\,\.-]', '', val_str)
    if not cleaned: return 0.0
    try:
        if '.' in cleaned and ',' in cleaned:
            if cleaned.rfind('.') < cleaned.rfind(','):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned and '.' not in cleaned:
            parts = cleaned.split(',')
            cleaned = cleaned.replace(',', '.') if len(parts) == 2 and len(parts[1]) <= 2 else cleaned.replace(',', '')
        elif '.' in cleaned and ',' not in cleaned:
            parts = cleaned.split('.')
            if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) != 2):
                cleaned = cleaned.replace('.', '')
        return float(cleaned)
    except Exception:
        return 0.0

try:
    csv_url = convert_to_csv_url(SHEET_URL)
    df = pd.read_csv(csv_url, dtype=str)
    df.columns = df.columns.str.strip()
    df_clean_text = df.fillna("").astype(str)

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

    with st.sidebar:
        st.write("### 📊 Status Data Master")
        st.write(f"Total Baris: {len(df)}")
        st.write("### 📋 Daftar Kolom Sheet:")
        for idx, col in enumerate(df.columns):
            st.text(f"{idx+1}. {col}")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    if prompt := st.chat_input("Tanyakan sesuatu terkait data universe..."):
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # --- 1. AI EKSTRAKSI NAMABERSIH & KATEGORI ---
        extraction_prompt = f"""
Saring pertanyaan user dan kembalikan format JSON:
{{"entity": "<nama entitas bersih>", "category": "<REPS|APOTEK|GENERAL>"}}

Aturan:
- "entity": Ambil HANYA kata kunci utama nama (misal: "gebang farma", "rizki", "afrianto"). Hapus kata "apotek", "reps", "gmv", "pencapaian", "bulan ini", dll.
- "category": Jika tanyakan reps/sales -> "REPS". Jika toko/apotek -> "APOTEK". Selain itu -> "GENERAL".

Input: "{prompt}"
JSON:"""

        extracted_entity = ""
        category = "GENERAL"
        try:
            ext_res = client.chat.completions.create(
                model="google/gemini-2.0-flash-lite-001:free",
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.0
            )
            raw_out = ext_res.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', raw_out, re.DOTALL)
            if json_match:
                import json
                parsed_json = json.loads(json_match.group(0))
                extracted_entity = parsed_json.get("entity", "").lower().strip()
                category = parsed_json.get("category", "GENERAL").upper()
        except Exception:
            extracted_entity = ""

        if not extracted_entity:
            clean_prompt = re.sub(r'[^\w\s]', ' ', prompt.lower())
            stop_words = set(['berapa', 'total', 'gmv', 'pencapaian', 'pencapian', 'capaian', 'target', 'data', 'untuk', 'bulan', 'ini', 'reps', 'sales', 'apotek', 'apotik', 'toko', 'outlet', 'pt', 'cv'])
            extracted_entity = " ".join([w for w in clean_prompt.split() if w not in stop_words and len(w) > 1])

        entity_tokens = extracted_entity.split()
        sub_df = pd.DataFrame()

        if entity_tokens:
            # Tentukan kolom acuan pencarian
            search_cols = []
            if category == "APOTEK":
                search_cols = [c for c in df.columns if any(k in c.lower() for k in ['apotek', 'apotik', 'toko', 'outlet', 'customer', 'pelanggan', 'nama'])]
            elif category == "REPS":
                search_cols = [c for c in df.columns if any(k in c.lower() for k in ['reps', 'sales', 'salesman', 'nama reps'])]

            # Pencarian spesifik ke kolom acuan jika ditemukan
            if search_cols:
                series_check = df_clean_text[search_cols].apply(lambda row: " ".join(row.values).lower(), axis=1)
                sub_df = df[series_check.apply(lambda x: all(t in x for t in entity_tokens))]

            # Fallback ke seluruh baris jika kolom acuan tidak spesifik
            if len(sub_df) == 0:
                row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
                sub_df = df[row_combined.apply(lambda x: all(t in x for t in entity_tokens))]

        with st.chat_message("assistant", avatar="🤖"):
            if len(sub_df) > 0:
                # Tampilkan tabel rincian data mentah yang terfilter agar user bisa langsung verifikasi
                st.write(f"🔎 **Ditemukan {len(sub_df)} baris data match di Google Sheet:**")
                st.dataframe(sub_df.head(10))

                # Perhitungan Otomatis Seluruh Kolom Angka
                calc_details = []
                for col in sub_df.columns:
                    # Ambil hanya kolom numeric (mengandung angka/GMV/Sales)
                    num_series = sub_df[col].apply(parse_number_exact)
                    total_val = num_series.sum()
                    if total_val > 0 and not any(k in col.lower() for k in ['id', 'code', 'zip', 'telepon', 'phone', '%', 'pct']):
                        calc_details.append(f"- **{col}**: Rp {total_val:,.0f}".replace(",", "."))

                summary_txt = "\n".join(calc_details) if calc_details else "Tidak ada nominal angka terdeteksi di kolom ini."
                response_text = f"Berikut adalah total penjumlahan untuk **'{extracted_entity}'** dari {len(sub_df)} baris data terfilter:\n\n{summary_txt}"
                st.markdown(response_text)
            else:
                response_text = f"Maaf, kata kunci **'{extracted_entity}'** tidak ditemukan pada kolom {category.lower()} di Google Sheet."
                st.markdown(response_text)

        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
