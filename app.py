import streamlit as st
import pandas as pd
from openai import OpenAI
import re

OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
SHEET_URL = st.secrets["SHEET_URL"]

st.set_page_config(
    page_title="Chatbot Universe SPV Happy", 
    page_icon="🤖", 
    layout="wide"
)

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
        margin-bottom: 2rem;
    }
    .main-header h1 { color: white !important; font-weight: 800; font-size: 2.2rem; margin-bottom: 0.5rem; }
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

def parse_number_exact(val):
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'null', 'none', '-', '']:
        return 0.0

    cleaned = re.sub(r'[^0-9\,\.-]', '', val_str)
    if not cleaned:
        return 0.0

    try:
        if '.' in cleaned and ',' in cleaned:
            if cleaned.rfind('.') < cleaned.rfind(','):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned and '.' not in cleaned:
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif '.' in cleaned and ',' not in cleaned:
            parts = cleaned.split('.')
            if len(parts) > 2:
                cleaned = cleaned.replace('.', '')
            elif len(parts) == 2:
                if len(parts[1]) == 3:
                    cleaned = cleaned.replace('.', '')
                elif len(parts[1]) != 2:
                    cleaned = cleaned.replace('.', '')

        return float(cleaned)
    except Exception:
        return 0.0

try:
    csv_url = convert_to_csv_url(SHEET_URL)
    df = pd.read_csv(csv_url, dtype=str)
    df.columns = df.columns.str.strip()
    df_clean_text = df.fillna("").astype(str)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    with st.sidebar:
        st.write("### 📊 Panel Kontrol Data")
        st.write(f"Total Baris: {len(df)}")
        st.write(f"Total Kolom: {len(df.columns)}")
        st.write("**Daftar Kolom:**")
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

        # Deteksi Nama Reps Utama
        target_name = None
        for name in ['sulistiana', 'afrianto', 'rizki', 'gde', 'mulyanto', 'happy']:
            if name in prompt_lower:
                target_name = name
                break

        # Cari Kolom
        reps_cols = [c for c in df.columns if any(k in c.lower() for k in ['reps', 'sales', 'nama', 'spv'])]
        gmv_cols = [c for c in df.columns if any(k in c.lower() for k in ['gmv', 'ach', 'total', 'nominal', 'sales', 'pencapaian'])]

        # Filter DataFrame
        sub_df = pd.DataFrame()
        if target_name and target_name != 'happy':
            if reps_cols:
                # Filter tepat di kolom Reps
                r_col = reps_cols[0]
                sub_df = df[df[r_col].fillna("").astype(str).str.lower().str.contains(target_name)]
            else:
                # Fallback ke seluruh teks
                row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
                sub_df = df[row_combined.str.contains(target_name)]
        else:
            # Jika 'happy' atau tanya total team
            sub_df = df.copy()

        with st.chat_message("assistant", avatar="🤖"):
            # Fitur Debugging: Tampilkan Baris & Kolom Terfilter di Expander
            with st.expander("🔍 Lihat Hasil Filter Data (Debug)"):
                st.write(f"Entitas Dicari: **{target_name}**")
                st.write(f"Jumlah Baris Ditemukan: **{len(sub_df)}**")
                st.dataframe(sub_df.head(20))

            if len(sub_df) > 0:
                calculated_metrics = []
                for g_col in gmv_cols:
                    if not any(ignore in g_col.lower() for ignore in ['date', 'tanggal', 'id', 'code', 'durasi', 'no', 'phone']):
                        total_val = sub_df[g_col].apply(parse_number_exact).sum()
                        if total_val > 0:
                            calculated_metrics.append(f"- **{g_col}**: Rp {total_val:,.0f}".replace(",", "."))

                calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Tidak ada angka terhitung dari kolom nominal."

                system_prompt = f"""
Kamu adalah Senior Data Analyst SPV.

DITEMUKAN HASIL KALKULASI PYTHON DARI DATA SHEET:
{calc_summary_str}

Pertanyaan User: "{prompt}"

Instruksi Menjawab:
1. GUNAKAN ANGKA TOTAL DARI HASIL DI ATAS UNTUK MENJAWAB.
2. Sebutkan secara langsung nama entitas dan angkanya di kalimat pertama.
3. JANGAN MENAMBAHKAN/MENGHITUNG MANUALLAGI.
"""
                response_text = ""
                try:
                    completion = client.chat.completions.create(
                        model="google/gemini-2.0-flash-lite-001:free",
                        messages=[{"role": "user", "content": system_prompt}],
                        temperature=0.0
                    )
                    if completion.choices:
                        response_text = completion.choices[0].message.content
                except Exception:
                    response_text = f"Berikut total pencapaian yang terhitung:\n\n{calc_summary_str}"

                if not response_text:
                    response_text = f"Berikut total pencapaian:\n\n{calc_summary_str}"

                st.markdown(response_text)
            else:
                st.markdown(f"Data untuk **{target_name}** tidak ditemukan.")

        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
