import streamlit as st
import pandas as pd
from openai import OpenAI
import re

OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
SHEET_URL = st.secrets["SHEET_URL"]

st.set_page_config(
    page_title="Chatbot Universe SPV Happy", 
    page_icon="🤖", 
    layout="centered"
)

# Kustomisasi Tampilan Visual
st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stApp { background-color: #f8fafc; }
    .main-header {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        padding: 2.5rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.2);
        margin-bottom: 2rem;
    }
    .main-header h1 { color: white !important; font-weight: 800; font-size: 2.2rem; margin-bottom: 0.5rem; }
    .main-header p { color: #e0e7ff !important; font-size: 1rem; margin: 0; }
    .stChatMessage { border-radius: 16px !important; padding: 1rem 1.2rem !important; margin-bottom: 0.8rem !important; box-shadow: 0 2px 5px rgba(0,0,0,0.03) !important; }
    .stChatInputContainer { border-radius: 15px !important; bottom: 20px !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="main-header">
        <h1>🤖 Chatbot Universe SPV Happy</h1>
        <p>Tanyakan apa saja terkait data universe kalian.</p>
    </div>
""", unsafe_allow_html=True)

def convert_to_csv_url(url):
    sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if not sheet_id_match: 
        return None
    sheet_id = sheet_id_match.group(1)
    gid_match = re.search(r'[#&?]gid=([0-9]+)', url)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

def parse_number(val):
    """Konversi string rupiah/angka ke float presisi"""
    if pd.isna(val):
        return 0.0
    val_str = str(val).strip()
    cleaned = re.sub(r'[^0-9\,\.-]', '', val_str)
    if not cleaned:
        return 0.0
    if ',' in cleaned and '.' in cleaned:
        if cleaned.find('.') < cleaned.find(','):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned and '.' not in cleaned:
        cleaned = cleaned.replace(',', '.')
    elif '.' in cleaned and ',' not in cleaned:
        parts = cleaned.split('.')
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) != 2):
            cleaned = cleaned.replace('.', '')
    try:
        return float(cleaned)
    except:
        return 0.0

try:
    csv_url = convert_to_csv_url(SHEET_URL)
    df = pd.read_csv(csv_url)
    df.columns = df.columns.str.strip()
    df_clean_text = df.fillna("").astype(str)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    with st.sidebar:
        st.write("### 📊 Status Data")
        st.write(f"Total Baris: {len(df)}")
        st.write(f"Total Kolom: {len(df.columns)}")
        with st.expander("Lihat Daftar Kolom"):
            st.write(list(df.columns))

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

        prompt_lower = prompt.lower()
        
        # Kata dasar pertanyaan yang benar-benar tidak membantu pencarian
        pure_stop_words = ['berapa', 'tolong', 'coba', 'data', 'untuk', 'yang', 'dari', 'tentang', 'gw', 'saya', 'dong', 'cek']
        tokens = [w for w in prompt_lower.split() if w not in pure_stop_words and len(w) > 1]
        
        sub_df = pd.DataFrame()
        if tokens:
            row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
            # 1. Coba pencarian ketat (semua kata kunci cocok)
            mask_all = row_combined.apply(lambda x: all(t in x for t in tokens))
            sub_df = df[mask_all]
            
            # 2. Jika tidak ada hasil, cari berdasarkan token entitas utama (abaikan kata metrik jika perlu)
            if len(sub_df) == 0:
                entity_tokens = [t for t in tokens if t not in ['pencapaian', 'capaian', 'misi', 'reguler', 'gold', 'gmv', 'total', 'target']]
                if entity_tokens:
                    mask_entity = row_combined.apply(lambda x: all(t in x for t in entity_tokens))
                    sub_df = df[mask_entity]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Gemini sedang menganalisis data secara akurat..."):
                if len(sub_df) > 0:
                    # Ambil baris terfilter
                    sub_df_clean = sub_df.dropna(how='all', axis=1).head(10)
                    
                    # Cari kolom-kolom yang mengandung nilai metrik/angka untuk dihitung langsung oleh Python
                    python_calc_summary = []
                    for col in sub_df_clean.columns:
                        col_lower = col.lower()
                        # Jika nama kolom relevan dengan kata kunci di prompt
                        if any(t in col_lower for t in tokens if len(t) > 2) or any(m in col_lower for m in ['gmv', 'target', 'pencapaian', 'misi', 'cm', 'lm']):
                            # Abaikan kolom berisi tanggal/ID/durasi
                            if not any(ignore in col_lower for ignore in ['date', 'tanggal', 'id', 'code', 'durasi', 'duration']):
                                num_series = sub_df_clean[col].apply(parse_number)
                                total_val = num_series.sum()
                                if total_val > 0:
                                    python_calc_summary.append(f"- **{col}**: Rp {total_val:,.0f}".replace(",", "."))
                    
                    calc_text = "\n".join(python_calc_summary) if python_calc_summary else "Tidak ada penjumlahan angka otomatis yang terdeteksi."
                    data_table_md = sub_df_clean.to_markdown(index=False)

                    system_prompt = f"""
Kamu adalah Senior Data Analyst SPV yang sangat cermat.

DATA TERFILTER DARI GOOGLE SHEET ({len(sub_df_clean)} Baris Ditemukan):
{data_table_md}

HASIL HUKUM HITUNGAN DARI PYTHON (Gunakan nilai ini jika relevan):
{calc_text}

Pertanyaan User: "{prompt}"

Instruksi Penting:
1. Analisis pertanyaan user dengan teliti. Tentukan kolom mana pada tabel yang SESUAI DENGAN PERTANYAAN (misal: "Pencapaian Misi Reguler", "Target Misi", "GMV", dll).
2. Sebutkan nama toko/sales dan angka nominal spesifik yang dicari user pada kalimat pertama secara langsung.
3. JANGAN campur adukkan kolom "Misi Reguler" dengan "Misi Gold" atau "GMV Harian" jika user hanya bertanya salah satunya.
4. Tampilkan rincian singkat dalam bentuk poin yang rapi dan mudah dibaca oleh SPV.
"""
                    response_text = ""
                    models_to_try = [
                        "google/gemini-2.0-flash-lite-001:free",
                        "google/gemini-2.0-flash-exp:free",
                        "openrouter/free"
                    ]

                    for model_id in models_to_try:
                        try:
                            completion = client.chat.completions.create(
                                model=model_id,
                                messages=[{"role": "user", "content": system_prompt}],
                                temperature=0.0
                            )
                            if completion.choices and len(completion.choices) > 0:
                                res = completion.choices[0].message.content
                                if res and len(res.strip()) > 5:
                                    response_text = res
                                    break
                        except Exception:
                            continue

                    if not response_text or len(response_text.strip()) < 5:
                        response_text = f"Ditemukan data untuk pencarian tersebut. Berikut rincian dari tabel:\n\n{calc_text}\n\n```markdown\n{data_table_md}\n```"

                else:
                    search_keyword = ' '.join(tokens) if tokens else prompt
                    response_text = f"Maaf bro, data untuk **'{search_keyword}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
