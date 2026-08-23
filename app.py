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

def parse_number_exact(val):
    """
    Parser murni aman untuk Rupiah Indonesia.
    Mengubah 'Rp 585.409.626,00' atau '20.000.000' menjadi float 20000000.0 murni tanpa kehilangan digit.
    """
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'null', 'none', '-', '']:
        return 0.0

    # Hilangkan tulisan Rp, spasi, dan karakter non-numerik selain titik dan koma
    cleaned = re.sub(r'[^0-9\,\.-]', '', val_str)
    if not cleaned:
        return 0.0

    try:
        # Jika ada koma sebagai desimal di ujung akhir (misal ,00 atau ,50), buang desimal sen-nya
        if ',' in cleaned:
            parts = cleaned.split(',')
            if len(parts[-1]) <= 2: # Asumsi 2 digit desimal sen
                cleaned = "".join(parts[:-1])
            else:
                cleaned = cleaned.replace(',', '')

        # Hapus semua titik pemisah ribuan
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
        
        # Daftar kata pencarian
        stop_words = [
            'berapa', 'total', 'gmv', 'pencapaian', 'capaian', 'misi', 'reguler', 'gold', 
            'target', 'data', 'untuk', 'bulan', 'ini', 'kemarin', 'di', 'dan', 'yang', 
            'dari', 'tentang', 'tim', 'gw', 'saya', 'tolong', 'coba', 'reps', 'sales', 'apotek', 'apotik'
        ]
        
        entity_tokens = [w for w in prompt_lower.split() if w not in stop_words and len(w) > 1]
        if not entity_tokens:
            entity_tokens = [w for w in prompt_lower.split() if len(w) > 2]

        sub_df = pd.DataFrame()
        if entity_tokens:
            row_combined = df_clean_text.apply(lambda row: " ".join(row.values).lower(), axis=1)
            
            # Cari baris yang mengandung token kata kunci
            mask_all = row_combined.apply(lambda x: all(t in x for t in entity_tokens))
            sub_df = df[mask_all]
            
            if len(sub_df) == 0:
                mask_any = row_combined.apply(lambda x: any(t in x for t in entity_tokens))
                sub_df = df[mask_any]

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Menghitung data dengan presisi 100%..."):
                if len(sub_df) > 0:
                    calculated_metrics = []
                    
                    # Targetkan hanya kolom yang relevan
                    target_cols = [c for c in sub_df.columns if any(k in c.lower() for k in ['gmv ach', 'gmv cm', 'pencapaian cm', 'total gmv', 'ach gmv', 'gmv'])]
                    # Filter buang kolom target/persen/id
                    filtered_cols = [c for c in target_cols if not any(ignore in c.lower() for ignore in ['target', '%', 'pct', 'status', 'id', 'date', 'tanggal'])]

                    cols_to_use = filtered_cols if filtered_cols else target_cols

                    for col in cols_to_use:
                        num_series = sub_df[col].apply(parse_number_exact)
                        total_val = num_series.sum()
                        if total_val > 0:
                            # Format Rupiah Indonesia murni
                            formatted_num = f"Rp {total_val:,.0f}".replace(",", ".")
                            calculated_metrics.append(f"- **{col}**: {formatted_num}")

                    calc_summary_str = "\n".join(calculated_metrics) if calculated_metrics else "Tidak ada kolom angka nominal yang terhitung."
                    
                    system_prompt = f"""
Kamu adalah Senior Data Analyst SPV.

DITEMUKAN HASIL HITUNG PRESISI DARI PYTHON:
{calc_summary_str}

Pertanyaan User: "{prompt}"

Instruksi SANGAT KETAT:
1. Jawab LANGSUNG menyebutkan entitas dan ANGKA HASIL KALKULASI PYTHON DI ATAS SECARA PERSIS TANPA DIUBAH ATAU DITAMBAH SEPERAK PUN!
2. Jika ada beberapa kolom yang terhitung, tampilkan rincian list kolom tersebut.
3. DILARANG membuat perkiraan atau mengubah format angka dari string hasil Python.
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
                        response_text = f"Berikut total pencapaian presisi terhitung dari data:\n\n{calc_summary_str}"

                    if not response_text:
                        response_text = f"Berikut total pencapaian presisi terhitung:\n\n{calc_summary_str}"

                else:
                    search_kw = ' '.join(entity_tokens) if entity_tokens else prompt
                    response_text = f"Maaf bro, data untuk **'{search_kw}'** tidak ditemukan di Google Sheet."

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
