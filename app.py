import streamlit as st
import pandas as pd
import re
import io
import requests

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
            if len(parts) > 1:
                cleaned = cleaned.replace('.', '')
        elif ',' in cleaned:
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')

        return float(cleaned)
    except Exception:
        return 0.0

try:
    csv_url = convert_to_csv_url(SHEET_URL)
    res = requests.get(csv_url)
    csv_text = res.text
    lines = csv_text.splitlines()
    
    header_idx = 0
    for idx, line in enumerate(lines[:10]):
        if any(k in line.lower() for k in ['pharmacy name', 'nama toko', 'nama apotek', 'swiperx id', 'assignment']):
            header_idx = idx
            break
            
    raw_df = pd.read_csv(io.StringIO(csv_text), skiprows=header_idx, dtype=str)
    
    # Normalisasi nama kolom
    new_cols = []
    for c in raw_df.columns:
        c_clean = str(c).strip()
        w_match = re.search(r'\b(w[1-4])\b', c_clean, re.IGNORECASE)
        if w_match:
            new_cols.append(w_match.group(1).upper())
        else:
            new_cols.append(c_clean)
    raw_df.columns = new_cols

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Halo SPV! 👋 Mode Debug Aktif. Kirim pertanyaan toko kamu."}
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
        weeks_requested = [w for w in ['W1', 'W2', 'W3', 'W4'] if re.search(r'\b' + w.lower() + r'\b', prompt_lower)]

        # Ekstraksi nama toko secara longgar (ambil semua kata selain perintah umum)
        clean_prompt = prompt_lower
        junk_words = [
            r'\bberapa\b', r'\btotal\b', r'\bjumlah\b', r'\byang\b', r'\btersedia\b', r'\bada\b', 
            r'\btarget\b', r'\bvisit\b', r'\bkunjungan\b', r'\breps\b', r'\bsales\b', r'\bsalesman\b', 
            r'\blimit\b', r'\bplafon\b', r'\bdpd\b', r'\bmisi\b', r'\bmission\b', r'\bgold\b', r'\breguler\b',
            r'\bgmv\b', r'\bomset\b', r'\bdi\b', r'\bapotek\b', r'\bapotik\b', r'\btoko\b', r'\boutlet\b', 
            r'\bpt\b', r'\bcv\b', r'\bdata\b', r'\buntuk\b', r'\bbulan\b', r'\bini\b', r'\blalu\b', 
            r'\bni\b', r'\binih\b', r'\bkah\b', r'\bdong\b', r'\bcek\b', r'\binfo\b', r'\bpencapaian\b', 
            r'\bcapaian\b', r'\bperforma\b', r'\bhasil\b', r'\barea\b', r'\bmana\b', r'\byg\b', 
            r'\bsudah\b', r'\btransaksi\b', r'\bw1\b', r'\bw2\b', r'\bw3\b', r'\bw4\b',
            r'\baverage\b', r'\bavg\b', r'\brata-rata\b', r'\bratarata\b', r'\b3\b', r'\bbln\b',
            r'\bl3m\b', r'\bl2m\b', r'\blm\b', r'\bcm\b', r'\bdan\b', r'\bkapan\b', r'\btgl\b'
        ]
        for junk in junk_words:
            clean_prompt = re.sub(junk, ' ', clean_prompt)

        clean_prompt = re.sub(r'[^\w\s]', ' ', clean_prompt)
        extracted_entity = " ".join(clean_prompt.split()).strip()
        if not extracted_entity:
            extracted_entity = prompt

        matched_indices = []
        entity_tokens = extracted_entity.split()

        # Cari di seluruh sel DataFrame untuk melihat baris mana saja yang mengandung token tersebut
        for idx, row in raw_df.iterrows():
            row_text = " ".join([str(val) for val in row.values if pd.notna(val)]).lower()
            # Cukup cocokkan salah satu token unik (misal: "gebang") agar tidak terlalu ketat
            if any(token in row_text for token in entity_tokens if len(token) > 3):
                matched_indices.append(idx)

        sub_df = raw_df.loc[matched_indices] if matched_indices else pd.DataFrame(columns=raw_df.columns)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menganalisis baris data..."):
                debug_info = f"**Query Mentah:** `{prompt}`\n"
                debug_info += f"**Entity Dicari:** `{extracted_entity}`\n"
                debug_info += f"**Token:** `{entity_tokens}`\n"
                debug_info += f"**Baris Ditemukan:** {len(sub_df)} baris\n\n"

                if len(sub_df) > 0:
                    # Ambil baris pertama yang cocok untuk dicek kolom namanya
                    first_row = sub_df.iloc[0]
                    debug_info += "**Contoh Baris Pertama yang Cocok:**\n"
                    for col in raw_df.columns[:5]: # Tampilkan 5 kolom pertama
                        debug_info += f"- {col}: {first_row.get(col, '-')}\n"
                    
                    # Ambil nilai W1-W4 di baris tersebut
                    debug_info += "\n**Nilai W1-W4 di Baris Ini:**\n"
                    for w in ['W1', 'W2', 'W3', 'W4']:
                        if w in sub_df.columns:
                            val = first_row.get(w, '0')
                            debug_info += f"- {w}: {val} (Parsed: {parse_number_exact(val):,.0f})\n"
                else:
                    debug_info += "❌ Tidak ada baris yang cocok sama sekali di CSV!"

                st.markdown(debug_info)
        
        st.session_state.messages.append({"role": "assistant", "content": debug_info})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
