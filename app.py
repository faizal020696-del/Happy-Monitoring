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

def parse_currency(value):
    if pd.isna(value):
        return 0.0
    val_str = str(value).strip()
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
        ignore_words = ['berapa', 'data', 'untuk', 'bulan', 'ini', 'kemarin', 'di', 'dan', 'yang', 'dari', 'tentang', 'pencapaian', 'capaian', 'misi', 'gold', 'gmv', 'total', 'totalin', 'tim', 'gw', 'saya', 'tolong', 'coba']
        search_tokens = [word for word in prompt_lower.split() if word not in ignore_words and len(word) > 2]
        
        sub_df = pd.DataFrame()
        if search_tokens:
            row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
            mask = row_combined.apply(lambda x: any(token in x for token in search_tokens))
            sub_df = df[mask]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menganalisis data..."):
                if len(sub_df) > 0:
                    summary_lines = []
                    for col in sub_df.columns:
                        if any(k in col.lower() for k in ['gmv', 'target', 'sales', 'value', 'amount', 'cm', 'lm', 'misi', 'gold']):
                            numeric_series = sub_df[col].apply(parse_currency)
                            total_val = numeric_series.sum()
                            if total_val > 0:
                                summary_lines.append(f"Total {col}: Rp {total_val:,.0f}".replace(",", "."))
                    
                    calc_summary = "\n".join(summary_lines)
                    data_csv = sub_df.to_csv(index=False)
                    
                    system_prompt = f"""
Kamu adalah asisten analitik SPV yang cerdas, akurat, dan ramah.

HASIL KALKULASI PASTI DARI PYTHON (GUNAKAN ANGKA INI UNTUK MENJAWAB):
{calc_summary if calc_summary else "Tidak ada angka metrik khusus yang dijumlahkan."}

DATA DETAIL BARIS RELEVAN (Format CSV):
{data_csv}

Pertanyaan User: "{prompt}"

Instruksi:
1. Jawab pertanyaan user secara langsung di kalimat pertama dengan menyebutkan angka Rupiah pasti dari hasil kalkulasi di atas.
2. Jelaskan detail jika ada perbandingan (misal GMV vs Target).
3. Buat bahasa yang singkat, jelas, dan ramah.
"""
                    response_text = None
                    try:
                        completion = client.chat.completions.create(
                            model="google/gemini-2.0-flash-lite-001:free",
                            messages=[{"role": "user", "content": system_prompt}],
                            temperature=0.1
                        )
                        if completion.choices and len(completion.choices) > 0:
                            response_text = completion.choices[0].message.content
                    except Exception as e:
                        pass

                    # Fallback jika model mengembalikan None atau error
                    if not response_text:
                        try:
                            completion = client.chat.completions.create(
                                model="google/gemini-flash-1.5:free",
                                messages=[{"role": "user", "content": system_prompt}],
                                temperature=0.1
                            )
                            if completion.choices and len(completion.choices) > 0:
                                response_text = completion.choices[0].message.content
                        except Exception as err:
                            pass
                    
                    # Jika AI masih gagal/kosong, tampilkan ringkasan kalkulasi Python langsung
                    if not response_text or response_text.strip() == "None":
                        response_text = f"Berikut adalah data pencapaian yang ditemukan:\n\n" + "\n".join([f"- **{item}**" for item in summary_lines])

                else:
                    response_text = f"Maaf bro, data untuk **'{' '.join(search_tokens)}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
