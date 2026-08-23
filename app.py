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

# Kustomisasi Tampilan Visual Streamlit
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
    """Membersihkan nilai uang/angka string ke float presisi"""
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
        
        # Kata dasar pertanyaan yang dibuang untuk mencari nama entitas (Reps / Apotek)
        stop_words = [
            'berapa', 'total', 'gmv', 'pencapaian', 'capaian', 'misi', 'reguler', 'gold', 
            'target', 'data', 'untuk', 'bulan', 'ini', 'kemarin', 'di', 'dan', 'yang', 
            'dari', 'tentang', 'tim', 'gw', 'saya', 'tolong', 'coba', 'reps', 'sales', 'apotek'
        ]
        
        entity_tokens = [w for w in prompt_lower.split() if w not in stop_words and len(w) > 1]
        if not entity_tokens:
            entity_tokens = [w for w in prompt_lower.split() if len(w) > 2]

        sub_df = pd.DataFrame()
        if entity_tokens:
            row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
            
            # Cari baris yang mengandung nama toko / reps
            mask_all = row_combined.apply(lambda x: all(t in x for t in entity_tokens))
            sub_df = df[mask_all]
            
            if len(sub_df) == 0:
                mask_any = row_combined.apply(lambda x: any(t in x for t in entity_tokens))
                sub_df = df[mask_any]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menghitung data secara presisi..."):
                if len(sub_df) > 0:
                    # KALKULASI PYTHON MUTLAK (Hitung 100% Seluruh Baris Tanpa Terpotong)
                    calculated_metrics = []
                    for col in sub_df.columns:
                        col_lower = col.lower()
                        # Ambil kolom metrik finansial/penjualan saja
                        if any(k in col_lower for k in ['gmv', 'cm', 'lm', 'sales', 'target', 'misi', 'pencapaian']):
                            if not any(ignore in col_lower for ignore in ['date', 'tanggal', 'id', 'code', 'durasi', 'duration']):
                                num_series = sub_df[col].apply(parse_number)
                                total_val = num_series.sum()
                                if total_val > 0:
                                    calculated_metrics.append(f"- **{col}**: Rp {total_val:,.0f}".replace(",", "."))

                    calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Tidak ada kolom nominal angka rupiah yang terhitung."
                    
                    # Ringkasan sampel tabel untuk dikirim ke Gemini
                    sub_df_sample = sub_df.dropna(how='all', axis=1).head(10)
                    data_table_md = sub_df_sample.to_markdown(index=False)

                    system_prompt = f"""
Kamu adalah Senior Data Analyst SPV.

DITEMUKAN TOTAL **{len(sub_df)} BARIS DATA** UNTUK ENTITAS YANG DICARI.

HASIL KALKULASI PRESISI PYTHON UNTUK **SELURUH {len(sub_df)} BARIS DATA** TERSEBUT:
{calc_summary_str}

SAMPEL RINCIAN TABEL (Max 10 baris):
{data_table_md}

Pertanyaan User: "{prompt}"

Instruksi Sangat Penting:
1. GUNAKAN HASIL KALKULASI PYTHON DI ATAS UNTUK MENJAWAB TOTAL ANGKA/GMV! JANGAN MENAMBAHKAN/MENJUMLAHKAN MANUAL LAGI PAKAI AI.
2. Jika user bertanya "bulan ini", utamakan mengambil angka dari kolom CM (Current Month) atau MTD. Jika tidak ada kolom CM, baru jelaskan bahwa yang tersedia adalah angka LM (Last Month).
3. Sebutkan nama entitas (Reps/Apotek) dan jawaban total angkanya secara eksplisit di kalimat pertama.
4. JANGAN PERNAH menampilkan rincian penjumlahan tambah-tambahan manual `(a + b + c)` yang dipotong-potong di jawaban.
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
                        response_text = f"Ditemukan **{len(sub_df)} baris data** untuk pencarian tersebut. Berikut hasil total angkanya:\n\n{calc_summary_str}"

                else:
                    search_kw = ' '.join(entity_tokens) if entity_tokens else prompt
                    response_text = f"Maaf bro, data untuk **'{search_kw}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
