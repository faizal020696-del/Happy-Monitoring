import io
import re
import pandas as pd
import requests
import streamlit as st

SHEET_URL = st.secrets.get("SHEET_URL", "")

# --- KONFIGURASI HALAMAN (WIDE MODE BIAR LEBIH LUAS & ELEGAN) ---
st.set_page_config(
    page_title="Chatbot Universe SPV Happy", page_icon="🤖", layout="wide"
)

# --- CUSTOM CSS: TAMPILAN EYE-CATCHING & MODERN ---
st.markdown(
    """
    <style>
    /* Menyembunyikan Toolbar / Tombol Fork & GitHub bawaan Streamlit */
    [data-testid="stToolbar"] {
        display: none !important;
    }
    .stAppDeployButton {
        display: none !important;
    }
    header {
        visibility: hidden !important;
        display: none !important;
    }

    /* Style Tampilan Utama & Background Soft */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Header Banner Custom yang Gradient & Cantik */
    .main-header {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        padding: 22px 28px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 10px 20px -5px rgba(59, 130, 246, 0.3);
    }
    .main-header h1 {
        font-size: 1.7rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        color: white !important;
    }
    .main-header p {
        font-size: 0.95rem !important;
        margin: 6px 0 0 0 !important;
        opacity: 0.95;
        color: #eff6ff !important;
    }

    /* Kotak Chat Input Modern dengan Efek Melengkung */
    .stChatInputContainer {
        padding-bottom: 0.5rem;
        border-radius: 16px !important;
        border: 2px solid #cbd5e1 !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
        background-color: white;
    }

    /* Bubble Chat Styling Lebih Clean & Ber-border Tipis */
    .stChatMessage {
        padding: 1.2rem;
        border-radius: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        margin-bottom: 1rem;
        border: 1px solid #f1f5f9;
        background-color: #ffffff;
    }
    .stChatMessage h3 {
        font-size: 1.15rem !important;
        font-weight: 600 !important;
        line-height: 1.4 !important;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }
    .stChatMessage h4 {
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: #334155;
    }

    /* Styling Sidebar Biar Lebih Rapi */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    </style>
""",
    unsafe_allow_html=True,
)


def convert_to_csv_url(url):
  sheet_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
  if not sheet_id_match:
    return None
  sheet_id = sheet_id_match.group(1)
  gid_match = re.search(r"[#&?]gid=([0-9]+)", url)
  gid = gid_match.group(1) if gid_match else "0"
  return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def parse_number_transaction(val):
  if pd.isna(val) or val is None:
    return 0.0
  val_str = str(val).strip()
  if not val_str or val_str.lower() in [
      "nan",
      "null",
      "none",
      "",
      "-",
      " - ",
      "0",
  ]:
    return 0.0
  cleaned = re.sub(r"[^0-9]", "", val_str)
  if not cleaned:
    return 0.0
  try:
    return float(cleaned)
  except Exception:
    return 0.0


def parse_number_general(val):
  if pd.isna(val) or val is None:
    return 0.0
  val_str = str(val).strip()
  if not val_str or val_str.lower() in ["nan", "null", "none", "", "-", " - "]:
    return 0.0

  cleaned = re.sub(r"[^0-9\,\.\-]", "", val_str)
  if not cleaned:
    return 0.0

  try:
    if "." in cleaned and "," in cleaned:
      if cleaned.rfind(".") < cleaned.rfind(","):
        cleaned = cleaned.replace(".", "").replace(",", ".")
      else:
        cleaned = cleaned.replace(",", "")
    elif "." in cleaned:
      parts = cleaned.split(".")
      if len(parts) > 2:
        cleaned = "".join(parts)
      elif len(parts) == 2 and len(parts[1]) == 3:
        cleaned = "".join(parts)
    elif "," in cleaned:
      parts = cleaned.split(",")
      if len(parts) > 2:
        cleaned = "".join(parts)
      elif len(parts) == 2 and len(parts[1]) <= 2:
        cleaned = cleaned.replace(",", ".")
      else:
        cleaned = cleaned.replace(",", "")

    val_float = float(cleaned)
    return val_float
  except Exception:
    digits_only = re.sub(r"[^0-9\-]", "", val_str)
    if digits_only:
      return float(digits_only)
    return 0.0


try:
  csv_url = convert_to_csv_url(SHEET_URL)
  res = requests.get(csv_url)
  csv_text = res.text
  lines = csv_text.splitlines()

  header_idx = 0
  for idx, line in enumerate(lines[:25]):
    line_lower = line.lower()
    if (
        "w1" in line_lower
        or "week 1" in line_lower
        or "dpd" in line_lower
        or "limit" in line_lower
        or "gmv" in line_lower
        or "cm" in line_lower
        or "target" in line_lower
        or "visit" in line_lower
        or "misi" in line_lower
        or "wtu" in line_lower
        or "daily" in line_lower
    ) and (
        "name" in line_lower
        or "nama" in line_lower
        or "apotek" in line_lower
        or "toko" in line_lower
        or "sales" in line_lower
        or "spv" in line_lower
    ):
      header_idx = idx
      break

  raw_df = pd.read_csv(io.StringIO(csv_text), skiprows=header_idx, dtype=str)
  raw_df.columns = [str(c).strip() for c in raw_df.columns]


  def is_row_lead(row):
    for c in raw_df.columns:
      val_str = str(row.get(c, "")).strip().lower()
      if "lead" in val_str or "prospek" in val_str:
        if val_str in ["lead", "prospek", "status: lead"]:
          return True
    return False


  week_cols_map = {}
  for col in raw_df.columns:
    col_lower = col.lower()
    if (
        re.search(r"\bw[,\s_-]*1\b", col_lower)
        or "week1" in col_lower
        or "week 1" in col_lower
        or "minggu1" in col_lower
        or "minggu 1" in col_lower
    ):
      week_cols_map["W1"] = col
    elif (
        re.search(r"\bw[,\s_-]*2\b", col_lower)
        or "week2" in col_lower
        or "week 2" in col_lower
        or "minggu2" in col_lower
        or "minggu 2" in col_lower
    ):
      week_cols_map["W2"] = col
    elif (
        re.search(r"\bw[,\s_-]*3\b", col_lower)
        or "week3" in col_lower
        or "week 3" in col_lower
        or "minggu3" in col_lower
        or "minggu 3" in col_lower
    ):
      week_cols_map["W3"] = col
    elif (
        re.search(r"\bw[,\s_-]*4\b", col_lower)
        or "week4" in col_lower
        or "week 4" in col_lower
        or "minggu4" in col_lower
        or "minggu 4" in col_lower
    ):
      week_cols_map["W4"] = col

  cm_col = next((c for c in raw_df.columns if c.strip().lower() == "cm"), None)
  lm_col = next((c for c in raw_df.columns if c.strip().lower() == "lm"), None)
  l2m_col = next(
      (c for c in raw_df.columns if c.strip().lower() == "l2m"), None
  )
  l3m_col = next(
      (c for c in raw_df.columns if c.strip().lower() == "l3m"), None
  )
  avg_col = next(
      (
          c
          for c in raw_df.columns
          if ("average" in c.lower() or "avg" in c.lower())
          and "l3m" in c.lower()
      ),
      None,
  )
  if not avg_col:
    avg_col = next(
        (
            c
            for c in raw_df.columns
            if "average" in c.lower() or "avg" in c.lower()
        ),
        None,
    )

  daily_gmv_col = next(
      (
          c
          for c in raw_df.columns
          if any(
              term in c.lower()
              for term in [
                  "daily gmv",
                  "daily",
                  "hari ini",
                  "today",
                  "harian",
                  "gmv hari",
              ]
          )
      ),
      None,
  )

  name_cols = [
      c
      for c in raw_df.columns
      if any(k in c.lower() for k in ["name", "nama", "pharmacy", "toko", "apotek"])
  ]
  name_col = name_cols[0] if name_cols else raw_df.columns[0]
  id_cols = [c for c in raw_df.columns if "id" in c.lower()]

  reps_cols = [
      c
      for c in raw_df.columns
      if c.lower()
      in ["sales rep", "salesrep", "sales reps", "reps", "sales", "pic"]
  ]
  if not reps_cols:
    reps_cols = [
        c
        for c in raw_df.columns
        if "sales" in c.lower() or "reps" in c.lower() or "pic" in c.lower()
    ]
  reps_col = reps_cols[0] if reps_cols else None

  spv_cols = [
      c
      for c in raw_df.columns
      if c.lower() in ["spv happy", "spv", "supervisor"]
  ]
  if not spv_cols:
    spv_cols = [
        c for c in raw_df.columns if "spv" in c.lower() or "supervisor" in c.lower()
    ]
  spv_col = spv_cols[0] if spv_cols else None

  # --- SESSION STATE INITIALIZATION ---
  if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": (
            "### Halo, Kawan! 👋\nAda data outlet, sales rep, atau SPV yang mau"
            " dicek hari ini? tapi sebelumnya sapa halo dulu dong ke gw"
        ),
    }]

  if "active_scope_type" not in st.session_state:
    st.session_state.active_scope_type = None
  if "active_scope_name" not in st.session_state:
    st.session_state.active_scope_name = None
  if "awaiting_daily_scope" not in st.session_state:
    st.session_state.awaiting_daily_scope = False
  if "current_rep" not in st.session_state:
    st.session_state.current_rep = None
  if "awaiting_rep_name" not in st.session_state:
    st.session_state.awaiting_rep_name = False

  # --- SIDEBAR PANEL (DIBUNGKUS KARTU BIAR RAPI & ELEGAN) ---
  with st.sidebar:
    st.markdown("### 🎛️ Panel Kontrol SPV")
    st.markdown("---")

    current_rep_display = (
        st.session_state.current_rep
        if st.session_state.current_rep
        else "Belum diset (Mode Umum)"
    )
    active_scope_display = (
        f"{st.session_state.active_scope_type.upper()}:"
        f" {st.session_state.active_scope_name}"
        if st.session_state.active_scope_type
        else "Semua Area / Global"
    )

    with st.container(border=True):
      st.markdown(f"**👤 Active Rep:**\n`{current_rep_display}`")
      st.markdown(f"**📍 Active Scope:**\n`{active_scope_display}`")

    st.markdown("")

    # Tombol Reset Sesi
    if st.button("🔄 Reset Sesi & Chat", use_container_width=True):
      st.session_state.messages = [{
          "role": "assistant",
          "content": (
              "### Halo, SPV! 👋\nSesi telah direset. Ada data outlet, sales"
              " rep, atau SPV yang mau dicek hari ini?"
          ),
      }]
      st.session_state.active_scope_type = None
      st.session_state.active_scope_name = None
      st.session_state.awaiting_daily_scope = False
      st.session_state.current_rep = None
      st.session_state.awaiting_rep_name = False
      st.rerun()

    st.markdown("---")
    with st.container(border=True):
      st.markdown(
          "💡 **Tips Cepat:**\n"
          "- Ketik nama outlet / ID untuk detail.\n"
          "- Ketik *'Top 10'* untuk leaderboard.\n"
          "- Ketik *'transaksi hari ini'*\n"
          "- Ketik *'belum ada mtu'"
      )

  # --- BANNER HEADER UTAMA DI HALAMAN CHAT ---
  st.markdown(
      """
      <div class="main-header">
          <h1>🚀 Chatbot Universe SPV Happy</h1>
          <p>Asisten intelijen Kapten Happy.</p>
      </div>
  """,
      unsafe_allow_html=True,
  )

  for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
      st.markdown(message["content"], unsafe_allow_html=True)

  if prompt := st.chat_input("Tulis pertanyaan atau nama outlet di sini..."):
    with st.chat_message("user", avatar="👤"):
      st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    prompt_lower = prompt.lower()

    # --- HANDLE GREETING & REP IDENTITY FLOW ---
    greeting_words = [
        "halo",
        "hai",
        "pagi",
        "siang",
        "sore",
        "malam",
        "assalamualaikum",
        "hallo",
        "hey",
    ]
    is_greeting = len(prompt_lower.split()) <= 4 and any(
        g in prompt_lower for g in greeting_words
    )

    if is_greeting and not st.session_state.current_rep:
      st.session_state.awaiting_rep_name = True
      with st.chat_message("assistant", avatar="🤖"):
        response_text = (
            "Halo juga, Bro! 👋 Biar gw tahu, lu lagi ngobrol sebagai Sales"
            " Rep siapa nih? (Sebutkan nama rep-nya ya, contoh: *nama"
            " sales-nya*)"
        )
        st.markdown(response_text, unsafe_allow_html=True)
        st.session_state.messages.append(
            {"role": "assistant", "content": response_text}
        )
    elif st.session_state.get("awaiting_rep_name", False):
      matched_rep = None
      if reps_col:
        unique_reps = raw_df[reps_col].dropna().astype(str).unique()
        for r in unique_reps:
          r_clean = r.strip().lower()
          if r_clean and (
              r_clean in prompt_lower
              or any(p in prompt_lower for p in r_clean.split() if len(p) > 2)
          ):
            matched_rep = r
            break

      if matched_rep:
        st.session_state.current_rep = matched_rep
        st.session_state.awaiting_rep_name = False
        st.session_state.active_scope_type = "reps"
        st.session_state.active_scope_name = matched_rep
        with st.chat_message("assistant", avatar="🤖"):
          response_text = (
              f"Sip, tercatat! 🚀 Sesi ini diset untuk Sales Rep"
              f" **{matched_rep.title()}**. Sekarang semua pertanyaan lu bakal"
              " otomatis ngecek data dari rep tersebut. Mau cek data apa nih,"
              " Bro?"
          )
          st.markdown(response_text, unsafe_allow_html=True)
          st.session_state.messages.append(
              {"role": "assistant", "content": response_text}
          )
      else:
        with st.chat_message("assistant", avatar="🤖"):
          response_text = (
              f"Hmm, nama Sales Rep **'{prompt}'** tidak ditemukan di data"
              " sheet gw. Coba sebutkan nama Sales Rep dengan benar ya, Bro!"
          )
          st.markdown(response_text, unsafe_allow_html=True)
          st.session_state.messages.append(
              {"role": "assistant", "content": response_text}
          )
    else:
      affirmative_words = [
          "boleh",
          "mau",
          "boleh dong",
          "iya",
          "boleh banget",
          "lanjut",
          "oke",
          "ok",
          "siap",
      ]
      is_affirmative = (
          len(prompt_lower.split()) <= 3
          and any(w in prompt_lower for w in affirmative_words)
      )

      last_assistant_msg = ""
      for m in reversed(st.session_state.messages[:-1]):
        if m["role"] == "assistant":
          last_assistant_msg = m["content"].lower()
          break

      is_agreeing_to_untransacted = is_affirmative and (
          "outlet yang belum ada mtu" in last_assistant_msg
          or "belum mtu" in last_assistant_msg
      )

      is_agreeing_to_wtu_untransacted = is_affirmative and (
          "wtu" in last_assistant_msg
          or "minggu" in last_assistant_msg
          or "transaksi mingguan" in last_assistant_msg
      )

      weeks_requested = []
      if re.search(
          r"\b(w1|week\s*1|week1|minggu\s*1|minggu1|ke\s*1)\b", prompt_lower
      ):
        weeks_requested.append("W1")
      if re.search(
          r"\b(w2|week\s*2|week2|minggu\s*2|minggu2|ke\s*2)\b", prompt_lower
      ):
        weeks_requested.append("W2")
      if re.search(
          r"\b(w3|week\s*3|week3|minggu\s*3|minggu3|ke\s*3)\b", prompt_lower
      ):
        weeks_requested.append("W3")
      if re.search(
          r"\b(w4|week\s*4|week4|minggu\s*4|minggu4|ke\s*4)\b", prompt_lower
      ):
        weeks_requested.append("W4")

      has_negative = any(
          k in prompt_lower for k in ["belum", "kosong", "nol", "tidak", "minus"]
      )
      has_trx_or_wtu = any(
          k in prompt_lower
          for k in ["transaksi", "trx", "ambil", "wtu", "minggu", "week"]
      )
      is_untransacted_query = (
          (has_negative and has_trx_or_wtu)
          or is_agreeing_to_untransacted
          or "outlet yang belum ada mtu" in prompt_lower
      )

      is_daily_query = (
          any(
              k in prompt_lower
              for k in [
                  "hari ini",
                  "today",
                  "daily",
                  "harian",
                  "transaksi hari ini",
              ]
          )
          and not weeks_requested
          and not is_untransacted_query
      ) or st.session_state.get("awaiting_daily_scope", False)

      is_mtu_query = (
          any(k in prompt_lower for k in ["mtu", "monthly transactional"])
          or (
              has_negative
              and ("mtu" in prompt_lower or "bulan ini" in prompt_lower)
          )
          or (
              "bulan ini" in prompt_lower
              and any(k in prompt_lower for k in ["transaksi", "trx", "aktif"])
          )
      ) and not is_agreeing_to_untransacted and not is_daily_query

      is_cm_untransacted_query = (
          has_negative
          and (
              "bulan ini" in prompt_lower
              or "cm" in prompt_lower
              or "gmv" in prompt_lower
              or "mtu" in prompt_lower
          )
      ) or is_agreeing_to_untransacted

      is_leaderboard_query = any(
          k in prompt_lower
          for k in [
              "top",
              "tertinggi",
              "terbesar",
              "ranking",
              "peringkat",
              "juara",
              "best",
          ]
      )

      is_limit_query = (
          any(
              k in prompt_lower
              for k in [
                  "limit",
                  "plafond",
                  "sisa",
                  "ssisa",
                  "avaiability",
                  "availability",
                  "avail",
              ]
          )
          and not weeks_requested
          and not is_untransacted_query
          and not is_cm_untransacted_query
          and not is_mtu_query
          and not is_daily_query
          and not is_leaderboard_query
      )
      is_mission_query = (
          any(
              k in prompt_lower
              for k in ["misi", "gold", "mission", "campaign", "pencapaian misi"]
          )
          and not weeks_requested
          and not is_untransacted_query
          and not is_cm_untransacted_query
          and not is_mtu_query
          and not is_daily_query
          and not is_leaderboard_query
      )
      is_visit_query = (
          any(k in prompt_lower for k in ["visit", "kunjungan"])
          and not weeks_requested
          and not is_untransacted_query
          and not is_cm_untransacted_query
          and not is_mtu_query
          and not is_daily_query
          and not is_leaderboard_query
      )
      is_wtu_query = (
          any(k in prompt_lower for k in ["wtu"])
          and not weeks_requested
          and not is_untransacted_query
          and not is_cm_untransacted_query
          and not is_mtu_query
          and not is_daily_query
          and not is_leaderboard_query
      )
      is_dpd_query = (
          any(k in prompt_lower for k in ["dpd", "jatuh tempo", "overdue"])
          and not weeks_requested
          and not is_untransacted_query
          and not is_cm_untransacted_query
          and not is_mtu_query
          and not is_daily_query
          and not is_leaderboard_query
      )
      is_trx_date_query = any(
          k in prompt_lower
          for k in [
              "trx date",
              "tanggal transaksi",
              "1st trx",
              "last trx",
              "transaksi terakhir",
              "transaksi pertama",
          ]
      )

      command_words = {
          "cek",
          "data",
          "id",
          "berapa",
          "total",
          "jumlah",
          "w1",
          "w2",
          "w3",
          "w4",
          "transaksi",
          "bertransaksi",
          "tolong",
          "visit",
          "kunjungan",
          "misi",
          "gold",
          "mission",
          "campaign",
          "type",
          "start",
          "date",
          "duration",
          "target",
          "level",
          "gmv",
          "ppn",
          "gap",
          "hna",
          "pencapaian",
          "kekurangan",
          "info",
          "apotek",
          "toko",
          "wtu",
          "sisa",
          "limit",
          "avg",
          "l3m",
          "reps",
          "sales",
          "pic",
          "bulan",
          "ini",
          "dpd",
          "plafond",
          "spv",
          "jatuh",
          "tempo",
          "1st",
          "last",
          "belum",
          "mana",
          "saja",
          "ambil",
          "list",
          "yg",
          "yang",
          "ke",
          "mtu",
          "boleh",
          "mau",
          "iya",
          "ok",
          "oke",
          "hari",
          "ini",
          "today",
          "daily",
          "top",
          "tertinggi",
          "ranking",
      }

      target_row = None
      matched_reps_df = None
      matched_reps_name = None
      matched_spv_df = None
      matched_spv_name = None

      if reps_col:
        for r in raw_df[reps_col].dropna().astype(str).unique():
          if r.strip().lower() in prompt_lower:
            matched_reps_name = r
            matched_reps_df = raw_df[
                raw_df[reps_col].astype(str).str.strip().str.lower()
                == r.strip().lower()
            ]
            break

      if spv_col:
        for s in raw_df[spv_col].dropna().astype(str).unique():
          if s.strip().lower() in prompt_lower:
            matched_spv_name = s
            matched_spv_df = raw_df[
                raw_df[spv_col].astype(str).str.strip().str.lower()
                == s.strip().lower()
            ]
            break

      if (
          st.session_state.current_rep
          and not matched_reps_name
          and not matched_spv_name
      ):
        matched_reps_name = st.session_state.current_rep
        matched_reps_df = raw_df[
            raw_df[reps_col].astype(str).str.strip().str.lower()
            == str(matched_reps_name).strip().lower()
        ]

      if is_leaderboard_query:
        scope_df = raw_df
        scope_name = "Semua Area"
        if matched_spv_name:
          scope_df = matched_spv_df
          scope_name = f"SPV {matched_spv_name.title()}"
        elif matched_reps_name:
          scope_df = matched_reps_df
          scope_name = f"Sales Rep {matched_reps_name.title()}"

        with st.chat_message("assistant", avatar="🤖"):
          with st.spinner("Menyusun peringkat (Leaderboard) outlet..."):
            scored_outlets = []
            for _, r in scope_df.iterrows():
              if is_row_lead(r):
                continue
              o_name = r.get(name_col, "Unknown")
              o_sales = r.get(reps_col, "-") if reps_col else "-"
              val_cm = parse_number_general(r.get(cm_col, 0)) if cm_col else 0
              if val_cm > 0:
                scored_outlets.append((str(o_name).strip(), o_sales, val_cm))

            scored_outlets.sort(key=lambda x: x[2], reverse=True)
            top_10 = scored_outlets[:10]

            res_lines = [
                (
                    f"### 🏆 Top 10 Outlet GMV Tertinggi (CM)\n*Lingkup:"
                    f" {scope_name}*\n---"
                ),
            ]
            if top_10:
              for rank, (o_name, o_sales, o_val) in enumerate(top_10, 1):
                fmt_val = f"Rp {o_val:,.0f}".replace(",", ".")
                medal = (
                    "🥇"
                    if rank == 1
                    else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
                )
                res_lines.append(
                    f"{medal} **{o_name.title()}**\n"
                    f"   * 👤 Sales: <span style='color: #000000; font-weight: bold;'>{o_sales}</span>\n"
                    f"   * 💰 CM: <span style='color: #000000; font-weight: bold;'>{fmt_val}</span>\n"
                )

              df_export = pd.DataFrame(
                  top_10, columns=["Nama Outlet", "Sales", "CM GMV"]
              )
              csv_data = df_export.to_csv(index=False).encode("utf-8")
              st.download_button(
                  label="📥 Download Top 10 Leaderboard (CSV)",
                  data=csv_data,
                  file_name="top_10_outlet_gmv.csv",
                  mime="text/csv",
              )
            else:
              res_lines.append(
                  "Belum ada data outlet dengan transaksi CM > 0 pada lingkup"
                  " ini."
              )

            response_text = "\n".join(res_lines)
            st.markdown(response_text, unsafe_allow_html=True)
            st.session_state.messages.append(
                {"role": "assistant", "content": response_text}
            )

      elif is_daily_query:
        if (
            (matched_spv_df is None or matched_spv_df.empty)
            and (matched_reps_df is None or matched_reps_df.empty)
            and not st.session_state.current_rep
        ):
          st.session_state.awaiting_daily_scope = True
          with st.chat_message("assistant", avatar="🤖"):
            response_text = (
                "Boleh, Bro! Mau dicek untuk area (SPV) atau sales"
                " representative (rep) siapa datanya untuk transaksi hari"
                " ini?"
            )
            st.markdown(response_text, unsafe_allow_html=True)
            st.session_state.messages.append(
                {"role": "assistant", "content": response_text}
            )
        else:
          st.session_state.awaiting_daily_scope = False

          scope_df = raw_df
          scope_name = "Semua Area"
          if matched_spv_df is not None and not matched_spv_df.empty:
            scope_df = matched_spv_df
            scope_name = f"SPV {str(matched_spv_name).title()}"
            st.session_state.active_scope_type = "spv"
            st.session_state.active_scope_name = matched_spv_name
          elif matched_reps_df is not None and not matched_reps_df.empty:
            scope_df = matched_reps_df
            scope_name = f"Sales Rep {str(matched_reps_name).title()}"
            st.session_state.active_scope_type = "reps"
            st.session_state.active_scope_name = matched_reps_name

          daily_outlets = []
          if daily_gmv_col:
            for _, r in scope_df.iterrows():
              if is_row_lead(r):
                continue
              out_name = r.get(name_col, None)
              if pd.isna(out_name) or not str(out_name).strip():
                continue
              out_name_str = str(out_name).strip()
              val_daily = parse_number_general(r.get(daily_gmv_col, 0))
              out_sales = r.get(reps_col, "-") if reps_col else "-"

              if val_daily > 0:
                daily_outlets.append((out_name_str, out_sales, val_daily))

            with st.chat_message("assistant", avatar="🤖"):
              with st.spinner("Mengecek data transaksi hari ini..."):
                total_count = len(daily_outlets)
                total_gmv = sum(item[2] for item in daily_outlets)
                formatted_total_gmv = f"Rp {total_gmv:,.0f}".replace(",", ".")

                res_lines = [
                    (
                        f"### ☀️ Ringkasan Transaksi Hari Ini\n*Lingkup:"
                        f" {scope_name}*\n---"
                    ),
                    (
                        f"- **Total Outlet Transaksi Hari Ini**: <span"
                        f" style='color: #000000; font-weight:"
                        f" bold;'>{total_count} outlet</span>"
                    ),
                    (
                        f"- **Total Akumulasi GMV Hari Ini**: <span"
                        f" style='color: #000000; font-weight:"
                        f" bold;'>{formatted_total_gmv}</span>\n"
                    ),
                    (
                        "#### 📋 Daftar Outlet yang Sudah Transaksi Hari Ini:"
                    ),
                ]

                if daily_outlets:
                  for idx_out, (o_name, o_sales, o_daily) in enumerate(
                      daily_outlets, 1
                  ):
                    formatted_daily = f"Rp {o_daily:,.0f}".replace(",", ".")
                    res_lines.append(
                        f"**{idx_out}. {str(o_name).title()}**\n"
                        f"   * 👤 Sales: <span style='color: #000000; font-weight: bold;'>{o_sales}</span>\n"
                        f"   * 💰 Daily GMV: <span style='color: #000000; font-weight: bold;'>{formatted_daily}</span>\n"
                    )

                  df_daily_export = pd.DataFrame(
                      daily_outlets, columns=["Nama Outlet", "Sales", "Daily GMV"]
                  )
                  csv_data_daily = df_daily_export.to_csv(index=False).encode(
                      "utf-8"
                  )
                  st.download_button(
                      label="📥 Download Data Transaksi Hari Ini (CSV)",
                      data=csv_data_daily,
                      file_name="transaksi_hari_ini.csv",
                      mime="text/csv",
                  )
                else:
                  res_lines.append(
                      "Belum ada outlet yang tercatat transaksi hari ini."
                  )

                response_text = "\n".join(res_lines)
                st.markdown(response_text, unsafe_allow_html=True)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response_text}
                )
          else:
            with st.chat_message("assistant", avatar="🤖"):
              response_text = (
                  "⚠️ Kolom untuk **Daily GMV** (atau transaksi hari ini)"
                  " belum terdeteksi di Google Sheet. Pastikan di GSheet kamu"
                  " ada kolom dengan nama yang mengandung kata 'daily',"
                  " 'hari ini', atau 'today'."
              )
              st.markdown(response_text, unsafe_allow_html=True)
              st.session_state.messages.append(
                  {"role": "assistant", "content": response_text}
              )

      elif is_cm_untransacted_query or is_mtu_query:
        scope_df = raw_df
        scope_name = "Semua Area"
        if matched_spv_df is not None and not matched_spv_df.empty:
          scope_df = matched_spv_df
          scope_name = f"SPV {str(matched_spv_name).title()}"
        elif matched_reps_df is not None and not matched_reps_df.empty:
          scope_df = matched_reps_df
          scope_name = f"Sales Rep {str(matched_reps_name).title()}"

        mtu_outlets = []
        untransacted_cm_outlets = []
        if cm_col:
          for _, r in scope_df.iterrows():
            if is_row_lead(r):
              continue

            out_name = r.get(name_col, None)
            if pd.isna(out_name):
              continue

            out_name_str = str(out_name).strip()
            if not out_name_str or out_name_str.lower() in [
                "nan",
                "none",
                "-",
                "",
                "nat",
            ]:
              continue

            val_cm = parse_number_general(r.get(cm_col, 0))
            out_sales = r.get(reps_col, "-") if reps_col else "-"
            val_avg = parse_number_general(r.get(avg_col, 0)) if avg_col else 0

            if val_cm > 0:
              mtu_outlets.append((out_name_str, out_sales, val_cm))
            else:
              untransacted_cm_outlets.append(
                  (out_name_str, out_sales, val_cm, val_avg)
              )

        with st.chat_message("assistant", avatar="🤖"):
          with st.spinner("Mengecek data MTU dan outlet bulan ini..."):
            if cm_col:
              if (
                  has_negative
                  or "belum" in prompt_lower
                  or is_agreeing_to_untransacted
              ):
                res_lines = [
                    (
                        "### 📋 Daftar Outlet Belum Ada MTU / Belum Transaksi"
                        " Bulan Ini (CM = 0)"
                    ),
                    f"*Lingkup: {scope_name}*\n---",
                    (
                        f"**Total Outlet Belum Transaksi:**"
                        f" **{len(untransacted_cm_outlets)} outlet** *(Lead"
                        " disingkirkan)*\n"
                    ),
                ]
                if untransacted_cm_outlets:
                  for idx_out, (o_name, o_sales, o_cm, o_avg) in enumerate(
                      untransacted_cm_outlets, 1
                  ):
                    formatted_cm = f"Rp {o_cm:,.0f}".replace(",", ".")
                    formatted_avg = (
                        f"Rp {o_avg:,.0f}".replace(",", ".")
                        if o_avg > 0
                        else "Rp 0"
                    )

                    res_lines.append(
                        f"**{idx_out}. {str(o_name).title()}**\n"
                        f"   * 👤 Sales: <span style='color: #000000; font-weight: bold;'>{o_sales}</span>\n"
                        f"   * 📊 CM: <span style='color: #000000; font-weight: bold;'>{formatted_cm}</span>\n"
                        f"   * 💡 AVG L3M: <span style='color: #000000; font-weight: bold;'>{formatted_avg}</span>\n\n"
                    )

                  df_untrans_export = pd.DataFrame(
                      untransacted_cm_outlets,
                      columns=["Nama Outlet", "Sales", "CM", "AVG L3M"],
                  )
                  csv_untrans_data = df_untrans_export.to_csv(
                      index=False
                  ).encode("utf-8")
                  st.download_button(
                      label="📥 Download Daftar Outlet Belum MTU (CSV)",
                      data=csv_untrans_data,
                      file_name="outlet_belum_mtu.csv",
                      mime="text/csv",
                  )
                else:
                  res_lines.append(
                      "🔥 **Luar Biasa!** Semua outlet aktif sudah tercatat"
                      " transaksi di bulan ini."
                  )
                response_text = "\n".join(res_lines)
              else:
                total_mtu_count = len(mtu_outlets)
                total_mtu_gmv = sum(item[2] for item in mtu_outlets)
                formatted_total_gmv = f"Rp {total_mtu_gmv:,.0f}".replace(
                    ",", "."
                )

                res_lines = [
                    (
                        f"### 📊 Ringkasan MTU Bulan Ini\n*Lingkup:"
                        f" {scope_name}*\n---"
                    ),
                    (
                        f"- **Total Outlet MTU (Sudah Transaksi)**: <span"
                        f" style='color: #000000; font-weight:"
                        f" bold;'>{total_mtu_count} outlet</span>"
                    ),
                    (
                        f"- **Total Akumulasi GMV CM**: <span"
                        f" style='color: #000000; font-weight:"
                        f" bold;'>{formatted_total_gmv}</span>"
                    ),
                    (
                        f"- **Total Outlet Belum MTU (CM = 0)**: <span"
                        f" style='color: #000000; font-weight:"
                        f" bold;'>{len(untransacted_cm_outlets)} outlet</span>\n"
                    ),
                    (
                        "#### 💡 Ingin melihat daftar detail outlet yang belum"
                        " ada MTU? Ketik saja: *'outlet yang belum ada MTU'*"
                        " atau jawab *'boleh'*."
                    ),
                ]
                response_text = "\n".join(res_lines)
            else:
              response_text = (
                  "Kolom **CM** (Current Month) tidak ditemukan di sheet."
              )

            st.markdown(response_text, unsafe_allow_html=True)
            st.session_state.messages.append(
                {"role": "assistant", "content": response_text}
            )

      elif is_agreeing_to_wtu_untransacted:
        scope_df = raw_df
        scope_name = "Semua Area"
        if (
            st.session_state.active_scope_type == "spv"
            and st.session_state.active_scope_name
        ):
          scope_name = f"SPV {str(st.session_state.active_scope_name).title()}"
          scope_df = raw_df[
              raw_df[spv_col].astype(str).str.strip().str.lower()
              == str(st.session_state.active_scope_name).strip().lower()
          ]
        elif (
            st.session_state.active_scope_type == "reps"
            and st.session_state.active_scope_name
        ):
          scope_name = (
              f"Sales Rep {str(st.session_state.active_scope_name).title()}"
          )
          scope_df = raw_df[
              raw_df[reps_col].astype(str).str.strip().str.lower()
              == str(st.session_state.active_scope_name).strip().lower()
          ]

        target_week_col = None
        target_week_label = None

        for w_key, col_val in week_cols_map.items():
          if w_key.lower() in prompt_lower or w_key.lower() in last_assistant_msg:
            if w_key.lower() in prompt_lower:
              target_week_col = col_val
              target_week_label = w_key
              break

        if not target_week_col:
          with st.chat_message("assistant", avatar="🤖"):
            response_text = (
                "### 📅 Pilih Minggu WTU\n"
                f"*Lingkup: {scope_name}*\n---\n"
                "Mau cek daftar outlet belum transaksi di minggu ke berapa,"
                " bro?\n\nSilakan ketik pilihan minggunya:\n* **'W1'** atau"
                " **'Minggu 1'**\n* **'W2'** atau **'Minggu 2'**\n* **'W3'**"
                " atau **'Minggu 3'**\n* **'W4'** atau **'Minggu 4'**"
            )
            st.markdown(response_text, unsafe_allow_html=True)
            st.session_state.messages.append(
                {"role": "assistant", "content": response_text}
            )
        else:
          with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(f"Mengecek daftar outlet belum transaksi di {target_week_label}..."):
              untransacted_wtu = []
              for _, r in scope_df.iterrows():
                if is_row_lead(r):
                  continue
                out_name = r.get(name_col, "")
                if pd.isna(out_name) or not str(out_name).strip():
                  continue
                val_w = parse_number_transaction(r.get(target_week_col, 0))
                if val_w == 0:
                  out_sales = r.get(reps_col, "-") if reps_col else "-"
                  w_vals = {}
                  for wk in ["W1", "W2", "W3", "W4"]:
                    if wk in week_cols_map:
                      w_vals[wk] = parse_number_transaction(
                          r.get(week_cols_map[wk], 0)
                      )
                    else:
                      w_vals[wk] = 0.0
                  untransacted_wtu.append(
                      (str(out_name).strip(), out_sales, w_vals)
                  )

              res_lines = [
                  (
                      f"### 📋 Daftar Outlet Belum Transaksi di"
                      f" **{target_week_label}**"
                  ),
                  f"*Lingkup: {scope_name}*\n---",
                  (
                      f"**Total Outlet Belum Transaksi:**"
                      f" **{len(untransacted_wtu)} outlet** *(Lead"
                      " disingkirkan)*\n"
                  ),
              ]
              if untransacted_wtu:
                for idx_w, (o_name, o_sales, w_vals) in enumerate(
                    untransacted_wtu, 1
                ):
                  hist_str = f"W1: Rp {w_vals.get('W1', 0):,.0f} | W2: Rp {w_vals.get('W2', 0):,.0f} | W3: Rp {w_vals.get('W3', 0):,.0f} | W4: Rp {w_vals.get('W4', 0):,.0f}".replace(
                      ",", "."
                  )
                  res_lines.append(
                      f"**{idx_w}. {o_name.title()}**\n"
                      f"   * 👤 Sales: <span style='color: #000000; font-weight: bold;'>{o_sales}</span>\n"
                      f"   * 📊 Histori: {hist_str}\n\n"
                  )

                df_wtu_export = pd.DataFrame(
                    [
                        (n, s, w["W1"], w["W2"], w["W3"], w["W4"])
                        for n, s, w in untransacted_wtu
                    ],
                    columns=["Nama Outlet", "Sales", "W1", "W2", "W3", "W4"],
                )
                csv_wtu_data = df_wtu_export.to_csv(index=False).encode(
                    "utf-8"
                )
                st.download_button(
                    label=f"📥 Download Outlet Belum Transaksi {target_week_label} (CSV)",
                    data=csv_wtu_data,
                    file_name=f"outlet_belum_trx_{target_week_label.lower()}.csv",
                    mime="text/csv",
                )
              else:
                res_lines.append(
                    "🔥 Mantap! Semua outlet sudah ada transaksi di minggu"
                    " ini."
                )

              response_text = "\n".join(res_lines)
              st.markdown(response_text, unsafe_allow_html=True)
              st.session_state.messages.append(
                  {"role": "assistant", "content": response_text}
              )

      elif weeks_requested:
        scope_df = raw_df
        scope_name = "Semua Area"
        if (
            st.session_state.active_scope_type == "spv"
            and st.session_state.active_scope_name
        ):
          scope_name = f"SPV {str(st.session_state.active_scope_name).title()}"
          scope_df = raw_df[
              raw_df[spv_col].astype(str).str.strip().str.lower()
              == str(st.session_state.active_scope_name).strip().lower()
          ]
        elif (
            st.session_state.active_scope_type == "reps"
            and st.session_state.active_scope_name
        ):
          scope_name = (
              f"Sales Rep {str(st.session_state.active_scope_name).title()}"
          )
          scope_df = raw_df[
              raw_df[reps_col].astype(str).str.strip().str.lower()
              == str(st.session_state.active_scope_name).strip().lower()
          ]

        w_key = weeks_requested[0]
        target_week_col = week_cols_map.get(w_key, None)

        with st.chat_message("assistant", avatar="🤖"):
          with st.spinner(f"Mengecek daftar outlet belum transaksi di {w_key}..."):
            untransacted_wtu = []
            if target_week_col:
              for _, r in scope_df.iterrows():
                if is_row_lead(r):
                  continue
                out_name = r.get(name_col, "")
                if pd.isna(out_name) or not str(out_name).strip():
                  continue
                val_w = parse_number_transaction(r.get(target_week_col, 0))
                if val_w == 0:
                  out_sales = r.get(reps_col, "-") if reps_col else "-"
                  w_vals = {}
                  for wk in ["W1", "W2", "W3", "W4"]:
                    if wk in week_cols_map:
                      w_vals[wk] = parse_number_transaction(
                          r.get(week_cols_map[wk], 0)
                      )
                    else:
                      w_vals[wk] = 0.0
                  untransacted_wtu.append(
                      (str(out_name).strip(), out_sales, w_vals)
                  )

            res_lines = [
                f"### 📋 Daftar Outlet Belum Transaksi di **{w_key}**",
                f"*Lingkup: {scope_name}*\n---",
                (
                    f"**Total Outlet Belum Transaksi:** **{len(untransacted_wtu)}"
                    " outlet** *(Lead disingkirkan)*\n"
                ),
            ]
            if untransacted_wtu:
              for idx_w, (o_name, o_sales, w_vals) in enumerate(
                  untransacted_wtu, 1
              ):
                hist_str = f"W1: Rp {w_vals.get('W1', 0):,.0f} | W2: Rp {w_vals.get('W2', 0):,.0f} | W3: Rp {w_vals.get('W3', 0):,.0f} | W4: Rp {w_vals.get('W4', 0):,.0f}".replace(
                    ",", "."
                )
                res_lines.append(
                    f"**{idx_w}. {o_name.title()}**\n"
                    f"   * 👤 Sales: <span style='color: #000000; font-weight: bold;'>{o_sales}</span>\n"
                    f"   * 📊 Histori: {hist_str}\n\n"
                )
            else:
              res_lines.append(
                  "🔥 Mantap! Semua outlet sudah ada transaksi di minggu ini."
              )

            response_text = "\n".join(res_lines)
            st.markdown(response_text, unsafe_allow_html=True)
            st.session_state.messages.append(
                {"role": "assistant", "content": response_text}
            )

      else:
        is_spv_query = "spv" in prompt_lower or "supervisor" in prompt_lower
        if not is_spv_query and spv_col:
          unique_spvs = raw_df[spv_col].dropna().astype(str).unique()
          for s in unique_spvs:
            s_clean = s.strip().lower()
            if (
                s_clean
                and len(s_clean) > 2
                and s_clean in prompt_lower
                and not any(kw in prompt_lower for kw in ["apotek", "toko"])
            ):
              is_spv_query = True
              break

        if is_spv_query and spv_col:
          unique_spvs = raw_df[spv_col].dropna().astype(str).unique()
          for s in unique_spvs:
            s_clean = s.strip().lower()
            if s_clean and s_clean in prompt_lower:
              matched_spv_name = s
              matched_spv_df = raw_df[
                  raw_df[spv_col].astype(str).str.strip().str.lower() == s_clean
              ]
              break

          if matched_spv_df is None or matched_spv_df.empty:
            for s in unique_spvs:
              s_clean = s.strip().lower()
              if s_clean and len(s_clean) > 2:
                parts = s_clean.split()
                if any(p in prompt_lower for p in parts if len(p) > 2):
                  matched_spv_name = s
                  matched_spv_df = raw_df[
                      raw_df[spv_col].astype(str).str.strip().str.lower()
                      == s_clean
                  ]
                  break

        if matched_spv_df is None or matched_spv_df.empty:
          is_sales_query = (
              "reps" in prompt_lower
              or "sales" in prompt_lower
              or "pic" in prompt_lower
          )

          if not is_sales_query and reps_col:
            unique_reps = raw_df[reps_col].dropna().astype(str).unique()
            for r in unique_reps:
              r_clean = r.strip().lower()
              if (
                  r_clean
                  and len(r_clean) > 2
                  and r_clean in prompt_lower
                  and not any(kw in prompt_lower for kw in ["apotek", "toko"])
              ):
                is_sales_query = True
                break

          if is_sales_query and reps_col:
            unique_reps = raw_df[reps_col].dropna().astype(str).unique()
            for r in unique_reps:
              r_clean = r.strip().lower()
              if r_clean and r_clean in prompt_lower:
                matched_reps_name = r
                matched_reps_df = raw_df[
                    raw_df[reps_col].astype(str).str.strip().str.lower()
                    == r_clean
                ]
                break

            if matched_reps_df is None or matched_reps_df.empty:
              for r in unique_reps:
                r_clean = r.strip().lower()
                if r_clean and len(r_clean) > 2:
                  parts = r_clean.split()
                  if any(p in prompt_lower for p in parts if len(p) > 2):
                    matched_reps_name = r
                    matched_reps_df = raw_df[
                        raw_df[reps_col].astype(str).str.strip().str.lower()
                        == r_clean
                    ]
                    break

        search_df = (
            matched_reps_df
            if (matched_reps_df is not None and not matched_reps_df.empty)
            else raw_df
        )

        id_match_prompt = re.search(r"\b(\d{4,6})\b", prompt)
        if id_match_prompt and id_cols:
          search_id = id_match_prompt.group(1)
          for idx, row in search_df.iterrows():
            if is_row_lead(row):
              continue
            for col in id_cols:
              val_id = str(row.get(col, "")).strip()
              if val_id == search_id:
                target_row = row
                break
            if target_row is not None:
              break

        if target_row is None:
          clean_prompt = prompt_lower
          for kw in [
              "cek",
              "data",
              "tolong",
              "wtu",
              "apotek",
              "toko",
              "pengen",
              "lihat",
              "tampilkan",
              "untuk",
              "detail",
          ]:
            clean_prompt = clean_prompt.replace(kw, "")
          clean_prompt = clean_prompt.strip()

          if clean_prompt:
            name_series = search_df[name_col].fillna("").astype(str).str.lower()
            scores = []
            query_words = clean_prompt.split()
            for idx, name_val in name_series.items():
              row_item = search_df.loc[idx]
              if is_row_lead(row_item):
                continue
              score = sum(1 for qw in query_words if qw in name_val)
              if all(qw in name_val for qw in query_words):
                score += 20
              scores.append((score, idx))
            scores.sort(key=lambda x: x[0], reverse=True)
            if scores and scores[0][0] > 0:
              target_row = search_df.loc[scores[0][1]]

          if target_row is None:
            outlet_query_words = [
                w
                for w in re.findall(r"\b\w+\b", prompt_lower)
                if w not in command_words
                and w not in ["detail", "apotek", "toko"]
            ]
            if outlet_query_words:
              name_series = (
                  search_df[name_col].fillna("").astype(str).str.lower()
              )
              scores = []
              for idx, name_val in name_series.items():
                row_item = search_df.loc[idx]
                if is_row_lead(row_item):
                  continue
                score = sum(
                    1 for qw in outlet_query_words if qw in name_val
                )
                if all(qw in name_val for qw in outlet_query_words):
                  score += 10
                scores.append((score, idx))
              scores.sort(key=lambda x: x[0], reverse=True)
              if scores:
                best_score, best_idx = scores[0]
                if best_score > 0:
                  target_row = search_df.loc[best_idx]

        with st.chat_message("assistant", avatar="🤖"):
          with st.spinner("Mengecek data..."):
            if target_row is not None and not is_row_lead(target_row):
              display_name = target_row.get(name_col, "Outlet Ditemukan")
              calculated_metrics = []

              if is_limit_query:
                limit_cols = [
                    c
                    for c in raw_df.columns
                    if any(
                        term in c.lower()
                        for term in ["limit", "plafond", "sisa", "avail"]
                    )
                ]
                if limit_cols:
                  calculated_metrics.append(
                      f"### 💳 Data Limit: **{str(display_name).title()}**\n---"
                  )
                  for col in limit_cols:
                    val_metric = target_row.get(col, "-")
                    val_parsed = parse_number_general(val_metric)
                    val_formatted = (
                        f"Rp {val_parsed:,.0f}".replace(",", ".")
                        if val_parsed > 0
                        else val_metric
                    )
                    calculated_metrics.append(
                        f"- **{col}**: <span style='color: #000000;"
                        f" font-weight: bold;'>{val_formatted}</span>"
                    )
                  response_text = "\n".join(calculated_metrics)
                else:
                  response_text = (
                      f"Data Limit untuk **{str(display_name).title()}** tidak"
                      " ditemukan di sheet."
                  )
              elif is_dpd_query:
                dpd_cols = [c for c in raw_df.columns if "dpd" in c.lower()]
                if dpd_cols:
                  calculated_metrics.append(
                      f"### ⏳ Data DPD: **{str(display_name).title()}**\n---"
                  )
                  for col in dpd_cols:
                    val_dpd = target_row.get(col, "-")
                    calculated_metrics.append(
                        f"- **{col}**: <span style='color: #000000;"
                        f" font-weight: bold;'>{val_dpd}</span>"
                    )
                  response_text = "\n".join(calculated_metrics)
                else:
                  response_text = (
                      f"Data DPD untuk **{str(display_name).title()}** tidak"
                      " ditemukan di sheet."
                  )
              elif is_visit_query:
                visit_cols = [
                    c
                    for c in raw_df.columns
                    if "visit" in c.lower() or "kunjungan" in c.lower()
                ]
                if visit_cols:
                  calculated_metrics.append(
                      (
                          f"### 📍 Data Kunjungan:"
                          f" **{str(display_name).title()}**\n---"
                      )
                  )
                  for col in visit_cols:
                    val_visit = target_row.get(col, "-")
                    calculated_metrics.append(
                        f"- **{col}**: <span style='color: #000000;"
                        f" font-weight: bold;'>{val_visit}</span>"
                    )
                  response_text = "\n".join(calculated_metrics)
                else:
                  response_text = (
                      f"Data Visit untuk **{str(display_name).title()}** tidak"
                      " ditemukan di sheet."
                  )
              elif is_wtu_query:
                calculated_metrics.append(
                    f"### 📅 Performa WTU: **{str(display_name).title()}**\n---"
                )
                for w in ["W1", "W2", "W3", "W4"]:
                  if w in week_cols_map:
                    col_name = week_cols_map[w]
                    val_raw = target_row.get(col_name, 0)
                    val_parsed = parse_number_transaction(val_raw)
                    formatted_val = f"Rp {val_parsed:,.0f}".replace(",", ".")
                    calculated_metrics.append(
                        f"- **{w}**: <span style='color: #000000; font-weight:"
                        f" bold;'>{formatted_val}</span>"
                    )
                response_text = "\n".join(calculated_metrics)
              elif is_trx_date_query:
                trx_date_cols = [
                    c
                    for c in raw_df.columns
                    if "trx date" in c.lower()
                    or "transaksi" in c.lower()
                    and ("date" in c.lower() or "tanggal" in c.lower())
                    or "1st" in c.lower()
                    or "last" in c.lower()
                ]
                if not trx_date_cols:
                  trx_date_cols = [
                      c for c in raw_df.columns if "date" in c.lower()
                  ]

                if trx_date_cols:
                  calculated_metrics.append(
                      (
                          f"### 🗓️ Tanggal Transaksi:"
                          f" **{str(display_name).title()}**\n---"
                      )
                  )
                  for col in trx_date_cols:
                    val_date = target_row.get(col, "-")
                    calculated_metrics.append(
                        f"- **{col}**: <span style='color: #000000;"
                        f" font-weight: bold;'>{val_date}</span>"
                    )
                  response_text = "\n".join(calculated_metrics)
                else:
                  response_text = (
                      f"Data Tanggal Transaksi untuk"
                      f" **{str(display_name).title()}** tidak ditemukan di"
                      " sheet."
                  )
              elif is_mission_query:
                mission_cols = [
                    c
                    for c in raw_df.columns
                    if any(
                        term in c.lower()
                        for term in ["misi", "gold", "mission", "campaign"]
                    )
                ]
                if not mission_cols:
                  mission_cols = [
                      c
                      for c in raw_df.columns
                      if "misi" in c.lower() or "mission" in c.lower()
                  ]

                if mission_cols:
                  campaign_info = []
                  reguler_target = []
                  gold_target = []
                  other_mission = []

                  for col in mission_cols:
                    val_misi = target_row.get(col, "-")
                    val_str_raw = str(val_misi).strip()
                    col_lower = col.lower()

                    val_parsed = parse_number_general(val_misi)
                    if val_parsed != 0 and any(
                        kw in col_lower for kw in ["target", "gmv", "gap", "hna"]
                    ):
                      val_str_fmt = f"Rp {abs(val_parsed):,.0f}".replace(
                          ",", "."
                      )
                      if "-" in val_str_raw:
                        val_str_fmt = f"-Rp {abs(val_parsed):,.0f}".replace(
                            ",", "."
                        )

                      if "gap" in col_lower:
                        if "-" in val_str_raw:
                          val_str_fmt += " *(Belum Tercapai / Minus)*"
                        else:
                          val_str_fmt += " *(Tercapai / Surplus!)*"
                    else:
                      val_str_fmt = val_str_raw

                    styled_val_str = (
                        f"<span style='color: #000000; font-weight:"
                        f" bold;'>{val_str_fmt}</span>"
                    )

                    if any(
                        k in col_lower
                        for k in ["type", "start date", "end date", "duration"]
                    ):
                      campaign_info.append(
                          f"👉 **{col}**: {styled_val_str}"
                      )
                    elif "gold" in col_lower:
                      gold_target.append(f"⭐ **{col}**: {styled_val_str}")
                    elif any(k in col_lower for k in ["target", "gmv", "gap"]):
                      reguler_target.append(
                          f"🎯 **{col}**: {styled_val_str}"
                      )
                    else:
                      other_mission.append(f"📌 **{col}**: {styled_val_str}")

                  calculated_metrics.append(
                      f"### 🎯 Data Misi: **{str(display_name).title()}**\n---"
                  )

                  if campaign_info:
                    calculated_metrics.append(
                        "#### 📌 Status Misi / Campaign:"
                    )
                    calculated_metrics.extend(
                        [f"* {item}" for item in campaign_info]
                    )
                    calculated_metrics.append("")

                  if reguler_target:
                    calculated_metrics.append(
                        "#### 📊 Target & Pencapaian Reguler:"
                    )
                    calculated_metrics.extend(
                        [f"* {item}" for item in reguler_target]
                    )
                    calculated_metrics.append("")

                  if gold_target:
                    calculated_metrics.append(
                        "#### ✨ Target & Pencapaian Gold Misi:"
                    )
                    calculated_metrics.extend(
                        [f"* {item}" for item in gold_target]
                    )
                    calculated_metrics.append("")

                  if other_mission:
                    calculated_metrics.append(
                        "#### 📂 Informasi Misi Lainnya:"
                    )
                    calculated_metrics.extend(
                        [f"* {item}" for item in other_mission]
                    )

                  response_text = "\n".join(calculated_metrics)
                else:
                  response_text = (
                      f"Data untuk **{str(display_name).title()}**:\nData"
                      " kolom misi tidak ditemukan di sheet."
                  )
              else:
                calculated_metrics.append(
                    f"### 🏥 Outlet: **{str(display_name).title()}**\n---"
                )
                calculated_metrics.append("**📈 Performa Bulanan:**")
                target_cols_gmv = [
                    ("CM (Bulan Ini)", cm_col),
                    ("LM (Bulan Lalu)", lm_col),
                    ("L2M", l2m_col),
                    ("L3M", l3m_col),
                    ("Average / AVG L3M", avg_col),
                ]
                for label, col in target_cols_gmv:
                  if col:
                    val_parsed = parse_number_general(target_row.get(col, 0))
                    formatted_val = f"Rp {val_parsed:,.0f}".replace(",", ".")
                    calculated_metrics.append(
                        f"- **{label}**: <span style='color: #000000;"
                        f" font-weight: bold;'>{formatted_val}</span>"
                    )

                calculated_metrics.append("\n**📅 Performa Mingguan (W1 - W4):**")
                for w in ["W1", "W2", "W3", "W4"]:
                  if w in week_cols_map:
                    col_name = week_cols_map[w]
                    val_raw = target_row.get(col_name, 0)
                    val_parsed = parse_number_transaction(val_raw)
                    formatted_val = f"Rp {val_parsed:,.0f}".replace(",", ".")
                    calculated_metrics.append(
                        f"- **{w}**: <span style='color: #000000; font-weight:"
                        f" bold;'>{formatted_val}</span>"
                    )

                response_text = "\n".join(calculated_metrics)

              st.markdown(response_text, unsafe_allow_html=True)
              st.session_state.messages.append(
                  {"role": "assistant", "content": response_text}
              )

            elif matched_spv_df is not None and not matched_spv_df.empty:
              st.session_state.active_scope_type = "spv"
              st.session_state.active_scope_name = matched_spv_name

              active_spv_df = matched_spv_df[
                  ~matched_spv_df.apply(is_row_lead, axis=1)
              ]
              total_outlets = len(active_spv_df)

              mtu_count = 0
              if cm_col:
                for _, r in active_spv_df.iterrows():
                  if parse_number_general(r.get(cm_col, 0)) > 0:
                    mtu_count += 1

              calculated_metrics = [
                  (
                      f"### 📊 Rekap Total SPV:"
                      f" **{str(matched_spv_name).title()}**\n---"
                  )
              ]
              calculated_metrics.append(
                  f"- **Jumlah Outlet Aktif**: <span style='color: #000000;"
                  f" font-weight: bold;'>{total_outlets} outlet</span>"
              )
              if cm_col:
                calculated_metrics.append(
                    f"- **Outlet MTU (Sudah Transaksi)**: <span"
                    f" style='color: #000000; font-weight:"
                    f" bold;'>{mtu_count} outlet</span>"
                )

              if is_limit_query:
                limit_cols = [
                    c
                    for c in raw_df.columns
                    if any(
                        term in c.lower()
                        for term in ["limit", "plafond", "sisa", "avail"]
                    )
                ]
                for col in limit_cols:
                  sum_val = sum(
                      parse_number_general(r.get(col, 0))
                      for _, r in active_spv_df.iterrows()
                  )
                  formatted_val = f"Rp {sum_val:,.0f}".replace(",", ".")
                  calculated_metrics.append(
                      f"- **Total {col}**: <span style='color: #000000;"
                      f" font-weight: bold;'>{formatted_val}</span>"
                  )
              elif is_wtu_query:
                calculated_metrics.append(
                    "\n#### 📅 Performa WTU Per Week & Transaksi"
                )
                for w in ["W1", "W2", "W3", "W4"]:
                  if w in week_cols_map:
                    col_name = week_cols_map[w]
                    sum_w = sum(
                        parse_number_transaction(r.get(col_name, 0))
                        for _, r in active_spv_df.iterrows()
                    )
                    active_outlets = sum(
                        1
                        for _, r in active_spv_df.iterrows()
                        if parse_number_transaction(r.get(col_name, 0)) > 0
                    )
                    formatted_val = f"Rp {sum_w:,.0f}".replace(",", ".")
                    calculated_metrics.append(
                        f"- **{w}**: <span style='color: #000000; font-weight:"
                        f" bold;'>{formatted_val}</span> *({active_outlets}"
                        " outlet trx)*"
                    )
                calculated_metrics.append(
                    "\n#### 💡 Ingin melihat daftar outlet yang belum"
                    " transaksi/WTU? Jawab saja: *'boleh'*."
                )
              else:
                calculated_metrics.append("\n#### 📈 Performa Bulanan")
                target_cols_gmv = [
                    ("CM (Bulan Ini)", cm_col),
                    ("LM (Bulan Lalu)", lm_col),
                    ("L2M", l2m_col),
                    ("L3M", l3m_col),
                    ("Average / AVG L3M", avg_col),
                ]
                for label, col in target_cols_gmv:
                  if col:
                    sum_val = sum(
                        parse_number_general(r.get(col, 0))
                        for _, r in active_spv_df.iterrows()
                    )
                    formatted_val = f"Rp {sum_val:,.0f}".replace(",", ".")
                    calculated_metrics.append(
                        f"- **{label}**: <span style='color: #000000;"
                        f" font-weight: bold;'>{formatted_val}</span>"
                    )

                calculated_metrics.append(
                    "\n#### 📅 Performa Mingguan (W1 - W4)"
                )
                chart_data_dict = {}
                for w in ["W1", "W2", "W3", "W4"]:
                  if w in week_cols_map:
                    col_name = week_cols_map[w]
                    sum_w = sum(
                        parse_number_transaction(r.get(col_name, 0))
                        for _, r in active_spv_df.iterrows()
                    )
                    active_outlets = sum(
                        1
                        for _, r in active_spv_df.iterrows()
                        if parse_number_transaction(r.get(col_name, 0)) > 0
                    )
                    formatted_val = f"Rp {sum_w:,.0f}".replace(",", ".")
                    calculated_metrics.append(
                        f"- **{w}**: <span style='color: #000000; font-weight:"
                        f" bold;'>{formatted_val}</span> *({active_outlets}"
                        " outlet trx)*"
                    )
                    chart_data_dict[w] = sum_w
                calculated_metrics.append(
                    "\n#### 💡 Ingin melihat daftar outlet yang belum"
                    " transaksi/WTU? Jawab saja: *'boleh'*."
                )

              response_text = "\n".join(calculated_metrics)
              st.markdown(response_text, unsafe_allow_html=True)

              if not is_limit_query and not is_wtu_query and week_cols_map:
                chart_df = pd.DataFrame(
                    list(chart_data_dict.items()),
                    columns=["Minggu", "Total GMV"],
                ).set_index("Minggu")
                st.bar_chart(chart_df)

              st.session_state.messages.append(
                  {"role": "assistant", "content": response_text}
              )

            elif matched_reps_df is not None and not matched_reps_df.empty:
              st.session_state.active_scope_type = "reps"
              st.session_state.active_scope_name = matched_reps_name

              active_reps_df = matched_reps_df[
                  ~matched_reps_df.apply(is_row_lead, axis=1)
              ]
              total_outlets = len(active_reps_df)

              mtu_count = 0
              if cm_col:
                for _, r in active_reps_df.iterrows():
                  if parse_number_general(r.get(cm_col, 0)) > 0:
                    mtu_count += 1

              calculated_metrics = [
                  (
                      f"### 📊 Rekap Total Sales Rep:"
                      f" **{str(matched_reps_name).title()}**\n---"
                  )
              ]
              calculated_metrics.append(
                  f"- **Jumlah Outlet Aktif**: <span style='color: #000000;"
                  f" font-weight: bold;'>{total_outlets} outlet</span>"
              )
              if cm_col:
                calculated_metrics.append(
                    f"- **Outlet MTU (Sudah Transaksi)**: <span"
                    f" style='color: #000000; font-weight:"
                    f" bold;'>{mtu_count} outlet</span>"
                )

              if is_limit_query:
                limit_cols = [
                    c
                    for c in raw_df.columns
                    if any(
                        term in c.lower()
                        for term in ["limit", "plafond", "sisa", "avail"]
                    )
                ]
                for col in limit_cols:
                  sum_val = sum(
                      parse_number_general(r.get(col, 0))
                      for _, r in active_reps_df.iterrows()
                  )
                  formatted_val = f"Rp {sum_val:,.0f}".replace(",", ".")
                  calculated_metrics.append(
                      f"- **Total {col}**: <span style='color: #000000;"
                      f" font-weight: bold;'>{formatted_val}</span>"
                  )
              elif is_wtu_query:
                calculated_metrics.append(
                    "\n#### 📅 Performa WTU Per Week & Transaksi"
                )
                for w in ["W1", "W2", "W3", "W4"]:
                  if w in week_cols_map:
                    col_name = week_cols_map[w]
                    sum_w = sum(
                        parse_number_transaction(r.get(col_name, 0))
                        for _, r in active_reps_df.iterrows()
                    )
                    active_outlets = sum(
                        1
                        for _, r in active_reps_df.iterrows()
                        if parse_number_transaction(r.get(col_name, 0)) > 0
                    )
                    formatted_val = f"Rp {sum_w:,.0f}".replace(",", ".")
                    calculated_metrics.append(
                        f"- **{w}**: <span style='color: #000000; font-weight:"
                        f" bold;'>{formatted_val}</span> *({active_outlets}"
                        " outlet trx)*"
                    )
                calculated_metrics.append(
                    "\n#### 💡 Ingin melihat daftar outlet yang belum"
                    " transaksi/WTU? Jawab saja: *'boleh'*."
                )
              else:
                calculated_metrics.append("\n#### 📈 Performa Bulanan")
                target_cols_gmv = [
                    ("CM (Bulan Ini)", cm_col),
                    ("LM (Bulan Lalu)", lm_col),
                    ("L2M", l2m_col),
                    ("L3M", l3m_col),
                    ("Average / AVG L3M", avg_col),
                ]
                for label, col in target_cols_gmv:
                  if col:
                    sum_val = sum(
                        parse_number_general(r.get(col, 0))
                        for _, r in active_reps_df.iterrows()
                    )
                    formatted_val = f"Rp {sum_val:,.0f}".replace(",", ".")
                    calculated_metrics.append(
                        f"- **{label}**: <span style='color: #000000;"
                        f" font-weight: bold;'>{formatted_val}</span>"
                    )

                calculated_metrics.append(
                    "\n#### 📅 Performa Mingguan (W1 - W4)"
                )
                chart_data_dict = {}
                for w in ["W1", "W2", "W3", "W4"]:
                  if w in week_cols_map:
                    col_name = week_cols_map[w]
                    sum_w = sum(
                        parse_number_transaction(r.get(col_name, 0))
                        for _, r in active_reps_df.iterrows()
                    )
                    active_outlets = sum(
                        1
                        for _, r in active_reps_df.iterrows()
                        if parse_number_transaction(r.get(col_name, 0)) > 0
                    )
                    formatted_val = f"Rp {sum_w:,.0f}".replace(",", ".")
                    calculated_metrics.append(
                        f"- **{w}**: <span style='color: #000000; font-weight:"
                        f" bold;'>{formatted_val}</span> *({active_outlets}"
                        " outlet trx)*"
                    )
                    chart_data_dict[w] = sum_w
                calculated_metrics.append(
                    "\n#### 💡 Ingin melihat daftar outlet yang belum"
                    " transaksi/WTU? Jawab saja: *'boleh'*."
                )

              response_text = "\n".join(calculated_metrics)
              st.markdown(response_text, unsafe_allow_html=True)

              if not is_limit_query and not is_wtu_query and week_cols_map:
                chart_df = pd.DataFrame(
                    list(chart_data_dict.items()),
                    columns=["Minggu", "Total GMV"],
                ).set_index("Minggu")
                st.bar_chart(chart_df)

              st.session_state.messages.append(
                  {"role": "assistant", "content": response_text}
              )
            else:
              response_text = (
                  "⚠️ Maaf, data tidak ditemukan atau outlet tersebut"
                  " berstatus lead/prospek. Pastikan nama apotek, ID, sales rep,"
                  " atau SPV aktif yang kamu cari sudah benar."
              )
              st.markdown(response_text, unsafe_allow_html=True)
              st.session_state.messages.append(
                  {"role": "assistant", "content": response_text}
              )
except Exception as e:
  st.error(f"Terjadi kesalahan saat memuat data: {e}")
