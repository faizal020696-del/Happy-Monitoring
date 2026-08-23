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
        
        # Kata-kata pertanyaan/metrik umum yang dibuang saat mencari nama toko/entitas
        metric_words = [
            'berapa', 'pencapaian', 'capaian', 'misi', 'reguler', 'gold', 'gmv', 'total', 
            'totalin', 'target', 'data', 'untuk', 'bulan', 'ini', 'kemarin', 'di', 'dan', 
            'yang', 'dari', 'tentang', 'tim', 'gw', 'saya', 'tolong', 'coba', 'apotek', 'apotik'
        ]
        
        # Ekstrak kata nama toko khusus (contoh: ['gebang', 'farma'])
        store_tokens = [w for w in prompt_lower.split() if w not in metric_words and len(w) > 1]
        
        # Fallback jika kata nama toko kosong
        if not store_tokens:
            store_tokens = [w for w in prompt_lower.split() if len(w) > 2]

        sub_df = pd.DataFrame()
        if store_tokens:
            row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
            
            # Tingkat 1: Cari yang mengandung SEMUA kata toko (contoh: "gebang" DAN "farma")
            mask_all = row_combined.apply(lambda x: all(t in x for t in store_tokens))
            sub_df = df[mask_all]
            
            # Tingkat 2: Jika 0 hasil, cari yang mengandung SALAH SATU kata nama unik (contoh: "gebang")
            if len(sub_df) == 0:
                # Ambil kata yang paling unik (panjang > 3 karakter)
                unique_tokens = [t for t in store_tokens if len(t) > 3]
                for token in unique_tokens:
                    mask_token = row_combined.apply(lambda x: token in x)
                    sub_df = df[mask_token]
                    if len(sub_df) > 0:
                        break

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Mencari dan menganalisis data..."):
                if len(sub_df) > 0:
                    # Ambil baris terfilter (max 15) dan buang kolom yang kosong total
                    sub_df_clean = sub_df.dropna(how='all', axis=1).head(15)
                    data_table_md = sub_df_clean.to_markdown(index=False)
                    all_columns_list = ", ".join(list(df.columns))

                    system_prompt = f"""
Kamu adalah Senior Data Analyst SPV.

DAFTAR SELURUH KOLOM DI GOOGLE SHEET:
[{all_columns_list}]

BERIKUT ADALAH TABEL BARIS DATA TERFILTER DARI HASIL PENCARIAN USER ({len(sub_df_clean)} Baris Ditemukan):
{data_table_md}

Pertanyaan User: "{prompt}"

Instruksi Menjawab:
1. Analisis tabel di atas. Perhatikan nama toko dan kolom yang berkaitan langsung dengan pertanyaan user.
2. Cari kolom yang mewakili topik pertanyaan (misalnya: "GMV Misi Gold", "Target Gold", "GMV HNA Gold", dll).
3. Sebutkan nama toko lengkap beserta angka nominal atau informasi spesifik yang ditemukan di sel tabel secara jelas dan akurat di kalimat pertama.
4. Jika kolom yang diminta user nilainya 0 atau kosong (NaN) di tabel, jelaskan secara jujur sesuai data di tabel.
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
                        response_text = f"Ditemukan {len(sub_df)} baris data toko. Berikut rincian tabelnya:\n\n```markdown\n{data_table_md}\n```"

                else:
                    search_kw = ' '.join(store_tokens) if store_tokens else prompt
                    response_text = f"Maaf bro, data untuk nama toko **'{search_kw}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
