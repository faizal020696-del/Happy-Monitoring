import io
import re
import pandas as pd
import requests
import streamlit as st

SHEET_URL = st.secrets.get("SHEET_URL", "")

st.set_page_config(
    page_title="Chatbot Universe SPV Happy", page_icon="🤖", layout="centered"
)

# --- CUSTOM CSS UNTUK MERAPIKAN TAMPILAN & UKURAN FONT ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8f9fa;
    }
    .stChatInputContainer {
        padding-bottom: 1rem;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 0.8rem;
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

  if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": (
            "### Halo, SPV! 👋\nAda data outlet, sales rep, atau SPV yang mau"
            " dicek hari ini?"
        ),
    }]

  if "active_scope_type" not in st.session_state:
    st.session_state.active_scope_type = None
  if "active_scope_name" not in st.session_state:
    st.session_state.active_scope_name = None

  for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
      st.markdown(message["content"], unsafe_allow_html=True)

  if prompt := st.chat_input("Tulis pertanyaan kamu di sini..."):
    with st.chat_message("user", avatar="👤"):
      st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    prompt_lower = prompt.lower()

    # DETEKSI PERSETUJUAN (affirmative words)
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

    # Cek pesan asisten terakhir
    last_assistant_msg = ""
    for m in reversed(st.session_state.messages[:-1]):
      if m["role"] == "assistant":
        last_assistant_msg = m["content"].lower()
        break

    is_agreeing_to_untransacted = is_affirmative and (
        "outlet yang belum ada mtu" in last_assistant_msg
        or "belum mtu" in last_assistant_msg
    )

    # Deteksi persetujuan khusus WTU / Belum Transaksi Mingguan
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
    ) and not is_agreeing_to_untransacted

    is_cm_untransacted_query = (has_negative and (
        "bulan ini" in prompt_lower
        or "cm" in prompt_lower
        or "gmv" in prompt_lower
        or "mtu" in prompt_lower
    )) or is_agreeing_to_untransacted

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
    )
    is_visit_query = (
        any(k in prompt_lower for k in ["visit", "kunjungan"])
        and not weeks_requested
        and not is_untransacted_query
        and not is_cm_untransacted_query
        and not is_mtu_query
    )
    is_wtu_query = (
        any(k in prompt_lower for k in ["wtu"])
        and not weeks_requested
        and not is_untransacted_query
        and not is_cm_untransacted_query
        and not is_mtu_query
    )
    is_dpd_query = (
        any(k in prompt_lower for k in ["dpd", "jatuh tempo", "overdue"])
        and not weeks_requested
        and not is_untransacted_query
        and not is_cm_untransacted_query
        and not is_mtu_query
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
    }

    target_row = None
    matched_reps_df = None
    matched_reps_name = None
    matched_spv_df = None
    matched_spv_name = None

    if is_cm_untransacted_query or is_mtu_query:
      if spv_col:
        unique_spvs = raw_df[spv_col].dropna().astype(str).unique()
        for s in unique_spvs:
          s_clean = s.strip().lower()
          if s_clean and s_clean in prompt_lower:
            matched_spv_name = s
            matched_spv_df = raw_df[
                raw_df[spv_col].astype(str).str.strip().str.lower() == s_clean
            ]
            break

      if reps_col and (matched_spv_df is None or matched_spv_df.empty):
        unique_reps = raw_df[reps_col].dropna().astype(str).unique()
        for r in unique_reps:
          r_clean = r.strip().lower()
          if r_clean and r_clean in prompt_lower:
            matched_reps_name = r
            matched_reps_df = raw_df[
                raw_df[reps_col].astype(str).str.strip().str.lower() == r_clean
            ]
            break

      if (
          (matched_spv_df is None or matched_spv_df.empty)
          and (matched_reps_df is None or matched_reps_df.empty)
          and st.session_state.active_scope_name
      ):
        if st.session_state.active_scope_type == "spv":
          matched_spv_name = st.session_state.active_scope_name
          matched_spv_df = raw_df[
              raw_df[spv_col].astype(str).str.strip().str.lower()
              == str(matched_spv_name).strip().lower()
          ]
        elif st.session_state.active_scope_type == "reps":
          matched_reps_name = st.session_state.active_scope_name
          matched_reps_df = raw_df[
              raw_df[reps_col].astype(str).str.strip().str.lower()
              == str(matched_reps_name).strip().lower()
          ]

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
            if has_negative or "belum" in prompt_lower or is_agreeing_to_untransacted:
              res_lines = [
                  f"### 📋 Daftar Outlet Belum Ada MTU / Belum Transaksi Bulan"
                  f" Ini (CM = 0)\n*Lingkup: {scope_name}*"
              ]
              res_lines.append(
                  f"---\n**Total Outlet Belum Transaksi:**"
                  f" **{len(untransacted_cm_outlets)} outlet** *(Lead"
                  " disingkirkan)*\n"
              )
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
                      "   * 👤 Sales:"
                      f" <span style='color: #000000; font-weight:"
                      f" bold;'>{o_sales}</span>\n"
                      f"   * 📊 CM: <span style='color: #000000; font-weight: bold;'>{formatted_cm}</span>\n"
                      f"   * 💡 AVG L3M: <span style='color: #000000; font-weight: bold;'>{formatted_avg}</span>\n"
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
              formatted_total_gmv = f"Rp {total_mtu_gmv:,.0f}".replace(",", ".")

              res_lines = [
                  f"### 📊 Ringkasan MTU Bulan Ini\n*Lingkup: {scope_name}*\n---",
                  f"- **Total Outlet MTU (Sudah Transaksi)**: <span style='color: #000000; font-weight: bold;'>{total_mtu_count} outlet</span>",
                  f"- **Total Akumulasi GMV CM**: <span style='color: #000000; font-weight: bold;'>{formatted_total_gmv}</span>",
                  f"- **Total Outlet Belum MTU (CM = 0)**: <span style='color: #000000; font-weight: bold;'>{len(untransacted_cm_outlets)} outlet</span>\n",
                  "#### 💡 Ingin melihat daftar detail outlet yang belum ada"
                  " MTU? Ketik saja: *'outlet yang belum ada MTU'* atau jawab"
                  " *'boleh'*.",
              ]
              response_text = "\n".join(res_lines)
          else:
            response_text = "Kolom **CM** (Current Month) tidak ditemukan di sheet."

          st.markdown(response_text, unsafe_allow_html=True)
          st.session_state.messages.append(
              {"role": "assistant", "content": response_text}
          )

    elif is_agreeing_to_wtu_untransacted:
      # Jika user menjawab "boleh" setelah bot nampilin rekap WTU
      scope_df = raw_df
      scope_name = "Semua Area"
      if st.session_state.active_scope_type == "spv" and st.session_state.active_scope_name:
        scope_name = f"SPV {str(st.session_state.active_scope_name).title()}"
        scope_df = raw_df[
            raw_df[spv_col].astype(str).str.strip().str.lower()
            == str(st.session_state.active_scope_name).strip().lower()
        ]
      elif st.session_state.active_scope_type == "reps" and st.session_state.active_scope_name:
        scope_name = f"Sales Rep {str(st.session_state.active_scope_name).title()}"
        scope_df = raw_df[
            raw_df[reps_col].astype(str).str.strip().str.lower()
            == str(st.session_state.active_scope_name).strip().lower()
        ]

      # Cek minggu mana yang disebut di pesan asisten sebelumnya, atau default ke W1-W4
      target_week_col = None
      target_week_label = "W1"
      for w_key, col_val in week_cols_map.items():
        if w_key.lower() in last_assistant_msg:
          target_week_col = col_val
          target_week_label = w_key
          break

      with st.chat_message("assistant", avatar="🤖"):
        with st.spinner(f"Mengecek daftar outlet belum transaksi di {target_week_label}..."):
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
                untransacted_wtu.append((str(out_name).strip(), out_sales))

          res_lines = [
              f"### 📋 Daftar Outlet Belum Transaksi di **{target_week_label}**\n*Lingkup: {scope_name}*\n---",
              f"**Total Outlet Belum Transaksi:** **{len(untransacted_wtu)} outlet** *(Lead disingkirkan)*\n",
          ]
          if untransacted_wtu:
            for idx_w, (o_name, o_sales) in enumerate(untransacted_wtu, 1):
              res_lines.append(
                  f"**{idx_w}. {o_name.title()}**\n"
                  f"   * 👤 Sales: <span style='color: #000000; font-weight: bold;'>{o_sales}</span>"
              )
          else:
            res_lines.append("🔥 Mantap! Semua outlet sudah ada transaksi di minggu ini.")

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
                  raw_df[reps_col].astype(str).str.strip().str.lower() == r_clean
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

      if (matched_spv_df is None or matched_spv_df.empty) and (
          matched_reps_df is None or matched_reps_df.empty
      ):
        id_match_prompt = re.search(r"\b(\d{4,6})\b", prompt)
        if id_match_prompt and id_cols:
          search_id = id_match_prompt.group(1)
          for idx, row in raw_df.iterrows():
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
          ]:
            clean_prompt = clean_prompt.replace(kw, "")
          clean_prompt = clean_prompt.strip()

          if clean_prompt:
            name_series = raw_df[name_col].fillna("").astype(str).str.lower()
            scores = []
            query_words = clean_prompt.split()
            for idx, name_val in name_series.items():
              row_item = raw_df.loc[idx]
              if is_row_lead(row_item):
                continue
              score = sum(1 for qw in query_words if qw in name_val)
              if all(qw in name_val for qw in query_words):
                score += 20
              scores.append((score, idx))
            scores.sort(key=lambda x: x[0], reverse=True)
            if scores and scores[0][0] > 0:
              target_row = raw_df.loc[scores[0][1]]

          if target_row is None:
            outlet_query_words = [
                w
                for w in re.findall(r"\b\w+\b", prompt_lower)
                if w not in command_words
            ]
            if outlet_query_words:
              name_series = raw_df[name_col].fillna("").astype(str).str.lower()
              scores = []
              for idx, name_val in name_series.items():
                row_item = raw_df.loc[idx]
                if is_row_lead(row_item):
                  continue
                score = sum(1 for qw in outlet_query_words if qw in name_val)
                if all(qw in name_val for qw in outlet_query_words):
                  score += 10
                scores.append((score, idx))
              scores.sort(key=lambda x: x[0], reverse=True)
              if scores:
                best_score, best_idx = scores[0]
                if best_score > 0:
                  target_row = raw_df.loc[best_idx]

      with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Mengecek data..."):
          if matched_spv_df is not None and not matched_spv_df.empty:
            st.session_state.active_scope_type = "spv"
            st.session_state.active_scope_name = matched_spv_name

            active_spv_df = matched_spv_df[
                ~matched_spv_df.apply(is_row_lead, axis=1)
            ]
            total_outlets = len(active_spv_df)
            calculated_metrics = [
                f"### 📊 Rekap Total SPV: **{str(matched_spv_name).title()}**\n---"
            ]
            calculated_metrics.append(
                f"- **Jumlah Outlet Aktif**: <span style='color: #000000;"
                f" font-weight: bold;'>{total_outlets} outlet</span>"
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

              calculated_metrics.append("\n#### 📅 Performa Mingguan (W1 - W4)")
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

            response_text = "\n".join(calculated_metrics)

          elif matched_reps_df is not None and not matched_reps_df.empty:
            st.session_state.active_scope_type = "reps"
            st.session_state.active_scope_name = matched_reps_name

            active_reps_df = matched_reps_df[
                ~matched_reps_df.apply(is_row_lead, axis=1)
            ]
            total_outlets = len(active_reps_df)
            calculated_metrics = [
                f"### 📊 Rekap Total Sales Rep: **{str(matched_reps_name).title()}**\n---"
            ]
            calculated_metrics.append(
                f"- **Jumlah Outlet Aktif**: <span style='color: #000000;"
                f" font-weight: bold;'>{total_outlets} outlet</span>"
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

              calculated_metrics.append("\n#### 📅 Performa Mingguan (W1 - W4)")
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

            response_text = "\n".join(calculated_metrics)

          elif target_row is not None and not is_row_lead(target_row):
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
                    f"### 📍 Data Kunjungan: **{str(display_name).title()}**\n---"
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
                trx_date_cols = [c for c in raw_df.columns if "date" in c.lower()]

              if trx_date_cols:
                calculated_metrics.append(
                    f"### 🗓️ Tanggal Transaksi:"
                    f" **{str(display_name).title()}**\n---"
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
                    f"Data Tanggal Transaksi untuk **{str(display_name).title()}**"
                    " tidak ditemukan di sheet."
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
                    val_str_fmt = f"Rp {abs(val_parsed):,.0f}".replace(",", ".")
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
                  calculated_metrics.extend([f"* {item}" for item in campaign_info])
                  calculated_metrics.append("")

                if reguler_target:
                  calculated_metrics.append(
                      "#### 📊 Target & Pencapaian Reguler:"
                  )
                  calculated_metrics.extend([f"* {item}" for item in reguler_target])
                  calculated_metrics.append("")

                if gold_target:
                  calculated_metrics.append(
                      "#### ✨ Target & Pencapaian Gold Misi:"
                  )
                  calculated_metrics.extend([f"* {item}" for item in gold_target])
                  calculated_metrics.append("")

                if other_mission:
                  calculated_metrics.append("#### 📂 Informasi Misi Lainnya:")
                  calculated_metrics.extend([f"* {item}" for item in other_mission])

                response_text = "\n".join(calculated_metrics)
              else:
                response_text = (
                    f"Data untuk **{str(display_name).title()}**:\nData kolom"
                    " misi tidak ditemukan di sheet."
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
          else:
            response_text = (
                "⚠️ Maaf, data tidak ditemukan atau outlet tersebut berstatus"
                " lead/prospek. Pastikan nama apotek, ID, sales rep, atau SPV"
                " aktif yang kamu cari sudah benar."
            )

          st.markdown(response_text, unsafe_allow_html=True)
          st.session_state.messages.append(
              {"role": "assistant", "content": response_text}
          )
except Exception as e:
  st.error(f"Terjadi kesalahan saat memuat data: {e}")
