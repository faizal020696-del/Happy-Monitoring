import streamlit as st
import pandas as pd
from google import genai
import re

st.set_page_config(page_title="Chatbot Monitoring Pekerjaan", page_icon="📊", layout="centered")
st.title("📊 Chatbot Monitoring Pekerjaan")
st.caption("Tanyakan apa saja terkait status pekerjaan/project tim berdasarkan data Google Sheets.")

st.sidebar.header("⚙️ Pengaturan Data & API")
api_key = st.sidebar.text_input("Gemini API Key:", type="password")
sheet_url = st.sidebar.text_input("Link Google Sheets (Public/Anyone with link):")

def convert_to_csv_url(url):
    sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if not sheet_id_match:
        return None
    
    sheet_id = sheet_id_match.group(1)
    gid_match = re.search(r'[#&?]gid=([0-9]+)', url)
    gid = gid_match.group(1) if gid_match else "0"
    
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

if api_key and sheet_url:
    try:
        csv_url = convert_to_csv_url(sheet_url)
        
        if not csv_url:
            st.error("Format link Google Sheets tidak valid. Pastikan menyalin link lengkap dari browser.")
        else:
            df = pd.read_csv(csv_url)
            
            if df.empty:
                st.warning("Data tabel kosong. Pastikan baris pertama Google Sheets berisi nama kolom (Header).")
            else:
                with st.sidebar.expander("👀 Lihat Data Google Sheets", expanded=True):
                    st.dataframe(df)

                client = genai.Client(api_key=api_key)

                if "messages" not in st.session_state:
                    st.session_state.messages = []

                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

                if prompt := st.chat_input("Contoh: Project apa aja yang deadline-nya minggu ini?"):
                    st.chat_message("user").markdown(prompt)
                    st.session_state.messages.append({"role": "user", "content": prompt})

                    data_str = df.to_csv(index=False)
                    system_prompt = f"""
                    Kamu adalah asisten monitoring pekerjaan/project tim yang cerdas dan ramah.
                    Berikut adalah data pekerjaan terbaru dalam format CSV:

                    {data_str}

                    Tugasmu:
                    1. Jawab pertanyaan user secara akurat HANYA berdasarkan data di atas.
                    2. Berikan jawaban dalam bahasa Indonesia yang ringkas, jelas, dan rapi.
                    3. Jika data tidak ada atau tidak ditemukan di tabel, katakan dengan jujur bahwa informasi tersebut tidak ada.
                    """

                    with st.chat_message("assistant"):
                        with st.spinner("Menganalisis data pekerjaan..."):
                            response = client.models.generate_content(
                                model='gemini-3.6-flash',
                                contents=f"{system_prompt}\n\nPertanyaan User: {prompt}"
                            )
                            st.markdown(response.text)
                    
                    st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"Gagal membaca data: {e}")
        st.info("Pastikan di Google Sheets baris pertama (Row 1) berisi Header Nama Kolom dan sheet tidak dalam keadaan kosong.")
else:
    st.info("💡 Silakan masukkan Gemini API Key dan Link Google Sheets di sidebar untuk mulai.")
