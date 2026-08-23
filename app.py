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
        ignore_words = ['berapa', 'data', 'untuk', 'bulan', 'ini', 'kemarin', 'di', 'dan', 'yang', 'dari', 'tentang', 'pencapaian', 'capaian', 'misi', 'gold', 'gmv', 'total', 'totalin', 'tim', 'gw', 'saya', 'tolong', 'coba']
        search_tokens = [word for word in prompt_lower.split() if word not in ignore_words and len(word) > 2]
        
        sub_df = pd.DataFrame()
        if search_tokens:
            row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
            mask = row_combined.apply(lambda x: any(token in x for token in search_tokens))
            sub_df = df[mask]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Gemini sedang menganalisis data..."):
                if len(sub_df) > 0:
                    data_markdown = sub_df.to_csv(index=False)
                    
                    system_prompt = f"""
Kamu adalah asisten analitik SPV yang cerdas, teliti, dan komunikatif.
Berikut adalah data mentah dari Google Sheet yang relevan dengan pertanyaan user (format CSV):

{data_markdown}

Pertanyaan User: "{prompt}"

Instruksi Analisis:
1. Pahami nama-nama kolom pada data di atas (misal: GMV CM = Bulan ini, GMV LM = Bulan lalu, Target, dll).
2. Lakukan kalkulasi/penjumlahan secara akurat dari baris data yang ada jika user meminta total.
3. Jawab pertanyaan user secara langsung di kalimat pertama dengan angka Rupiah yang benar.
4. Berikan analisis singkat yang logis (misal: perbandingan GMV terhadap Target, apakah sudah mencapai target atau belum, dan berapa gap pastinya jika ada).
5. Jangan asal menghitung selisih/gap, pastikan matematika kamu (GMV - Target) benar.
"""
                    try:
                        completion = client.chat.completions.create(
                            model="google/gemini-2.0-flash-lite-001:free",
                            messages=[
                                {"role": "user", "content": system_prompt}
                            ]
                        )
                        response_text = completion.choices[0].message.content
                    except Exception as e:
                        try:
                            completion = client.chat.completions.create(
                                model="openrouter/free",
                                messages=[{"role": "user", "content": system_prompt}]
                            )
                            response_text = completion.choices[0].message.content
                        except Exception as err:
                            response_text = f"Error dari API: {err}"
                else:
                    response_text = f"Maaf bro, data untuk **'{' '.join(search_tokens)}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
