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
    """Konversi string rupiah/angka ke float secara aman"""
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
        
        # Filtering Baris Data
        sub_df = pd.DataFrame()
        if search_tokens:
            # Cari baris yang mengandung SEMUA token penting (misal: "k24", "mutiara", "palem")
            row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
            mask = row_combined.apply(lambda x: any(token in x for token in search_tokens))
            sub_df = df[mask]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menganalisis data..."):
                if len(sub_df) > 0:
                    # 1. HITUNG SEMUA KOLOM METRIK PAKAI PYTHON (100% Presisi)
                    calculated_results = []
                    for col in sub_df.columns:
                        # Cari kolom yang berisikan angka metrik
                        if any(k in col.lower() for k in ['gmv', 'target', 'sales', 'value', 'amount', 'cm', 'lm', 'misi', 'gold', 'reguler']):
                            numeric_series = sub_df[col].apply(parse_currency)
                            total_val = numeric_series.sum()
                            if total_val > 0:
                                calculated_results.append(f"Total {col}: Rp {total_val:,.0f}".replace(",", "."))

                    calc_summary_str = "\n".join(calculated_results) if calculated_results else "Data berupa teks/bukan angka nominal."
                    data_table_md = sub_df.dropna(how='all', axis=1).to_markdown(index=False)

                    # 2. PROMPT UNTUK GEMINI
                    system_prompt = f"""
Kamu adalah asisten SPV yang handal dan informatif.

BERIKUT HASIL KALKULASI PRESISI PYTHON DARI DATA YANG DITEMUKAN (Gunakan angka ini):
{calc_summary_str}

DETAIL TABEL BARIS RELEVAN ({len(sub_df)} Baris Ditemukan):
{data_table_md}

Pertanyaan User: "{prompt}"

Instruksi:
- Jawab pertanyaan user dengan ramah dan ringkas.
- Sebutkan angka total nominal yang relevan berdasarkan hasil kalkulasi di atas.
- Jika ada detail tambahan yang perlu disampaikan, jelaskan secara singkat.
"""
                    response_text = ""
                    try:
                        completion = client.chat.completions.create(
                            model="google/gemini-2.0-flash-lite-001:free",
                            messages=[{"role": "user", "content": system_prompt}],
                            temperature=0.1
                        )
                        if completion.choices and len(completion.choices) > 0:
                            response_text = completion.choices[0].message.content
                    except Exception:
                        pass

                    # 3. FALLBACK DETEKSI ERROR (Jika AI Gagal/Error/Kosong, Pakai Tampilan Python Langsung)
                    invalid_responses = ["user safety", "safe", "none", "null", "kendala", ""]
                    if not response_text or any(bad in response_text.lower() for bad in invalid_responses) or len(response_text.strip()) < 5:
                        response_text = f" Ditemukan **{len(sub_df)} baris data** untuk pencarian tersebut. Berikut rincian angkanya:\n\n"
                        if calculated_results:
                            response_text += "\n".join([f"- **{res}**" for res in calculated_results])
                        else:
                            response_text += "```markdown\n" + data_table_md + "\n```"

                else:
                    response_text = f"Maaf bro, data untuk **'{' '.join(search_tokens)}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
