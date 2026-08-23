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

# Style UI Streamlit
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
        ignore_words = ['berapa', 'data', 'untuk', 'bulan', 'ini', 'kemarin', 'di', 'dan', 'yang', 'dari', 'tentang', 'pencapaian', 'capaian', 'misi', 'gold', 'gmv', 'total', 'totalin', 'tim', 'gw', 'saya', 'tolong', 'coba']
        search_tokens = [word for word in prompt_lower.split() if word not in ignore_words and len(word) > 2]
        
        # Filtering Baris Data
        sub_df = pd.DataFrame()
        if search_tokens:
            row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
            mask = row_combined.apply(lambda x: any(token in x for token in search_tokens))
            sub_df = df[mask]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Gemini sedang menganalisis data secara presisi..."):
                if len(sub_df) > 0:
                    # 1. Buang kolom yang 100% kosong supaya prompt ringkas & fokus
                    sub_df_clean = sub_df.dropna(how='all', axis=1)
                    
                    # 2. Ubah format ke Markdown Table (Gemini SANGAT AHLI baca format ini)
                    data_table_md = sub_df_clean.to_markdown(index=False)
                    
                    # 3. System Prompt "Level Dewa" dengan Chain-of-Thought
                    system_prompt = f"""
Kamu adalah Senior Data Analyst & Asisten SPV yang sangat teliti, akurat, dan tidak pernah salah berhitung.

Berikut adalah TABEL DATA RELEVAN dari Google Sheet (Format Markdown Table):

{data_table_md}

Pertanyaan User: "{prompt}"

Instruksi Analisis Presisi Tinggi:
1. PERIKSA TABEL DI ATAS DENGAN TELITI baris demi baris.
2. Identifikasi kolom mana yang mewakili pertanyaan user (misal: "GMV", "Target", "Current Month/CM", dll).
3. Jika pertanyaan meminta TOTAL/PENJUMLAHAN:
   - Sebutkan baris mana saja yang kamu hitung.
   - Lakukan penjumlahan angka nominal rupiah dari baris-baris tersebut secara presisi.
4. Jawablah dengan format yang rapi:
   - **Jawaban Utama**: Sebutkan angka total secara langsung di awal (format Rupiah lengkap dengan titik ribuan, contoh: Rp 150.000.000).
   - **Rincian Data**: Tampilkan rincian singkat per baris yang ditemukan.
   - **Kesimpulan/Analisis**: 1-2 kalimat ringkas dari pencapaian tersebut.
5. JANGAN MEMPERKIRAKAN ATAU MENEBAK ANGKA. Gunakan hanya angka asli yang tertera pada tabel data di atas!
"""
                    response_text = ""
                    try:
                        # Pemanggilan Model Gemini dengan Temperature 0.0 (Akurasi Mutlak)
                        completion = client.chat.completions.create(
                            model="google/gemini-2.0-flash-lite-001:free",
                            messages=[{"role": "user", "content": system_prompt}],
                            temperature=0.0 # Wajib 0.0 agar jawaban selalu konsisten dan akurat!
                        )
                        if completion.choices and len(completion.choices) > 0:
                            response_text = completion.choices[0].message.content
                    except Exception as e:
                        try:
                            completion = client.chat.completions.create(
                                model="google/gemini-flash-1.5:free",
                                messages=[{"role": "user", "content": system_prompt}],
                                temperature=0.0
                            )
                            if completion.choices and len(completion.choices) > 0:
                                response_text = completion.choices[0].message.content
                        except Exception as err:
                            try:
                                completion = client.chat.completions.create(
                                    model="openrouter/free",
                                    messages=[{"role": "user", "content": system_prompt}],
                                    temperature=0.0
                                )
                                response_text = completion.choices[0].message.content
                            except Exception as final_err:
                                response_text = f"Gagal mendapatkan respon dari API: {final_err}"

                    # Validasi jika respon berisi pesan safety error atau None
                    invalid_patterns = ["user safety", "safe", "none", "null", ""]
                    if not response_text or any(bad in response_text.lower() for bad in invalid_patterns) or len(response_text.strip()) < 5:
                        response_text = "Maaf bro, AI mengalami kendala saat membaca data tersebut. Coba ulangi pertanyaannya lagi."

                else:
                    response_text = f"Maaf bro, data untuk **'{' '.join(search_tokens)}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
