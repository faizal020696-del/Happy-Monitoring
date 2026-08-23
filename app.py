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
        
        # Kata pendukung/pertanyaan yang dibuang dari kata kunci pencarian toko
        stop_words = [
            'berapa', 'pencapaian', 'capaian', 'misi', 'reguler', 'gold', 'gmv', 'total', 
            'totalin', 'target', 'data', 'untuk', 'bulan', 'ini', 'kemarin', 'di', 'dan', 
            'yang', 'dari', 'tentang', 'tim', 'gw', 'saya', 'tolong', 'coba', 'apotek'
        ]
        
        # Ekstrak kata kunci nama toko/orang (contoh: ['k24', 'mutiara', 'palem'])
        store_tokens = [w for w in prompt_lower.split() if w not in stop_words and len(w) > 1]
        
        sub_df = pd.DataFrame()
        if store_tokens:
            row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
            # Filter KETAT: Baris HARUS mengandung SEMUA kata kunci nama toko/sales (ALL)
            mask = row_combined.apply(lambda x: all(token in x for token in store_tokens))
            sub_df = df[mask]
            
            # Fallback jika filter ALL terlalu ketat (0 hasil), coba cari yang minimal mengandung kata kunci utama
            if len(sub_df) == 0 and len(store_tokens) > 1:
                mask = row_combined.apply(lambda x: any(token in x for token in store_tokens))
                sub_df = df[mask]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Gemini sedang menganalisis baris data toko..."):
                if len(sub_df) > 0:
                    # Ambil maksimal 15 baris teratas jika ada banyak baris terfilter
                    sub_df_clean = sub_df.dropna(how='all', axis=1).head(15)
                    data_table_md = sub_df_clean.to_markdown(index=False)

                    system_prompt = f"""
Kamu adalah Senior Data Analyst SPV.
Berikut adalah data mentah dari Google Sheet khusus untuk toko/outlet yang dicari user:

{data_table_md}

Pertanyaan User: "{prompt}"

Instruksi Menjawab:
1. Cari baris dan kolom yang spesifik relevan dengan pertanyaan user (contoh: Pencapaian/GMV Misi Reguler, Target Misi Reguler, dll).
2. Jika ada beberapa baris data untuk toko ini, jumlahkan HANYA angka nominal pencapaian/GMV yang relevan tersebut. JANGAN MENJUMLAHKAN tanggal, ID, duration, atau target visit!
3. Jawab pertanyaan user secara langsung di kalimat pertama dengan menyebutkan nama toko dan angka nominal rupiah yang akurat.
4. Tampilkan rincian singkat dalam bentuk poin/tabel jika ada informasi target vs pencapaiannya.
"""
                    response_text = ""
                    try:
                        completion = client.chat.completions.create(
                            model="google/gemini-2.0-flash-lite-001:free",
                            messages=[{"role": "user", "content": system_prompt}],
                            temperature=0.0
                        )
                        if completion.choices and len(completion.choices) > 0:
                            response_text = completion.choices[0].message.content
                    except Exception:
                        try:
                            completion = client.chat.completions.create(
                                model="google/gemini-flash-1.5:free",
                                messages=[{"role": "user", "content": system_prompt}],
                                temperature=0.0
                            )
                            if completion.choices and len(completion.choices) > 0:
                                response_text = completion.choices[0].message.content
                        except Exception as err:
                            response_text = f"Gagal mendapatkan respon API: {err}"

                    if not response_text or len(response_text.strip()) < 5:
                        response_text = f"Ditemukan {len(sub_df)} baris data toko. Berikut datanya:\n\n```markdown\n{data_table_md}\n```"

                else:
                    response_text = f"Maaf bro, data untuk **'{' '.join(store_tokens)}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
