import streamlit as st
import pandas as pd
from google import genai
import re

st.set_page_config(
    page_title="Chatbot Universe SPV Happy", 
    page_icon="🤖", 
    layout="centered"
)

# CSS Sapu Bersih + Cover Overlay Pojok Kanan Bawah
st.markdown("""
    <style>
    /* Sembunyikan Elemen Bawaan Aplikasi */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stAppHeader {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    
    /* Overlay untuk Menutupi Badge Streamlit Cloud di Kanan Bawah */
    .stAppViewContainer::after {
        content: "";
        position: fixed;
        bottom: 0;
        right: 0;
        width: 380px; /* Lebar penutup badge */
        height: 50px;  /* Tinggi penutup badge */
        background-color: #f8fafc; /* Disamakan dengan warna background app */
        z-index: 999999;
        pointer-events: none;
    }

    /* Background Utama */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Header Container */
    .main-header {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        padding: 2.5rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.2);
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white !important;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 0.5rem;
    }
    .main-header p {
        color: #e0e7ff !important;
        font-size: 1rem;
        margin: 0;
    }

    /* Chat Styling */
    .stChatMessage {
        border-radius: 16px !important;
        padding: 1rem 1.2rem !important;
        margin-bottom: 0.8rem !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03) !important;
    }
    .stChatInputContainer {
        border-radius: 15px !important;
    }
    </style>
""", unsafe_allow_html=True)
