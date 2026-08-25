import re


def parse_number_general(val):
  """Helper untuk parsing angka dari string/angka."""
  if val is None:
    return 0
  val_str = str(val).replace(".", "").replace(",", ".").strip()
  match = re.search(r"-?\d+(\.\d+)?", val_str)
  if match:
    try:
      return float(match.group(0))
    except ValueError:
      return 0
  return 0


# Asumsi bagian ini ada di dalam logic query handler Streamlit kamu (misal: is_mission_query)
def process_and_display_mission_data(target_row, mission_cols):
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
        val_str_fmt = f"-Rp {abs(val_parsed):,.0f}".replace(",", ".")

      if "gap" in col_lower:
        if "-" in val_str_raw:
          val_str_fmt += " *(Belum Tercapai / Minus)*"
        else:
          val_str_fmt += " *(Tercapai / Surplus!)*"
    else:
      val_str_fmt = val_str_raw

    # DI SINI BAGIAN UTAMA: Ukuran font diperbesar & dibuat bold (font-weight 700)
    styled_val_str = (
        f"<span style='font-size: 1.1rem; font-weight: 700;'>{val_str_fmt}</span>"
    )

    if any(k in col_lower for k in ["type", "start date", "end date", "duration"]):
      campaign_info.append(f"👉 **{col}**: {styled_val_str}")
    elif "gold" in col_lower:
      gold_target.append(f"⭐ **{col}**: {styled_val_str}")
    elif any(k in col_lower for k in ["target", "gmv", "gap"]):
      reguler_target.append(f"🎯 **{col}**: {styled_val_str}")
    else:
      other_mission.append(f"📌 **{col}**: {styled_val_str}")

  # Contoh merakit kembali teks markdown/HTML untuk ditampilkan di st.markdown(...)
  final_output_parts = []
  if campaign_info:
    final_output_parts.append("📌 **Status Misi / Campaign:**\n" + "\n".join([f"- {item}" for item in campaign_info]))
  if reguler_target:
    final_output_parts.append("📊 **Target & Pencapaian Reguler:**\n" + "\n".join([f"- {item}" for item in reguler_target]))
  if gold_target:
    final_output_parts.append("✨ **Target & Pencapaian Gold Misi:**\n" + "\n".join([f"- {item}" for item in gold_target]))
  
  full_response_text = "\n\n".join(final_output_parts)
  
  # Jangan lupa render pakai unsafe_allow_html=True agar tag span-nya berfungsi!
  # st.markdown(full_response_text, unsafe_allow_html=True)
  return full_response_text
