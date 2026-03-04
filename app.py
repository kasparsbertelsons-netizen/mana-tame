import streamlit as st
import pandas as pd
import os

from fpdf import FPDF  # fpdf2

# -------------------------
# 1) PAROLES PĀRBAUDE
# -------------------------
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("### MLK House Sistēma")
        pwd = st.text_input("Ievadiet paroli", type="password")
        if st.button("Ieiet"):
            real_pwd = st.secrets.get("APP_PASSWORD", "buve2024")  # fallback lokāli
            if pwd == real_pwd:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Nepareiza parole!")
    return False


# -------------------------
# 2) DATU IELĀDE NO EXCEL (ar cache + validāciju)
# -------------------------
@st.cache_data(show_spinner=False)
def ieladet_katalogu(faila_vards: str):
    if not os.path.exists(faila_vards):
        return pd.DataFrame(columns=["Materials", "Cena"])

    df = pd.read_excel(faila_vards)

    # Kolonu normalizācija (ja kāds uzraksta citādi)
    cols = {c.strip(): c for c in df.columns}
    if "Materials" not in cols or "Cena" not in cols:
        raise ValueError("Excel failā jābūt kolonnām: 'Materials' un 'Cena'.")

    df = df[[cols["Materials"], cols["Cena"]]].copy()
    df.columns = ["Materials", "Cena"]
    df["Materials"] = df["Materials"].astype(str).str.strip()
    df["Cena"] = pd.to_numeric(df["Cena"], errors="coerce").fillna(0.0)

    # Izmetam tukšos nosaukumus
    df = df[df["Materials"] != ""].drop_duplicates(subset=["Materials"], keep="last")
    return df


def katalogs_dict(df_kat: pd.DataFrame) -> dict:
    return dict(zip(df_kat["Materials"], df_kat["Cena"]))


# -------------------------
# 3) PDF (Unicode + latviešu burti)
# -------------------------
def create_pdf(df: pd.DataFrame, kopa: float):
    pdf = FPDF()
    pdf.add_page()

    # Unicode fonts (pārliecinies, ka fails eksistē)
    font_path = "DejaVuSans.ttf"
    if not os.path.exists(font_path):
        raise FileNotFoundError("Nav atrasts fonts 'DejaVuSans.ttf'. Ieliec to blakus app.py.")

    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.add_font("DejaVu", "B", font_path, uni=True)
    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, txt="BUVNIECĪBAS TĀME", ln=True, align="C")
    pdf.ln(6)

    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(90, 8, "Materials", 1)
    pdf.cell(25, 8, "Daudz.", 1, align="R")
    pdf.cell(35, 8, "Cena", 1, align="R")
    pdf.cell(40, 8, "Summa", 1, align="R")
    pdf.ln()

    pdf.set_font("DejaVu", "", 11)
    for _, row in df.iterrows():
        s = float(row["Daudzums"]) * float(row["Cena"])
        pdf.cell(90, 8, str(row["Materials"])[:40], 1)   # apgriež garus nosaukumus
        pdf.cell(25, 8, f"{row['Daudzums']:.2f}", 1, align="R")
        pdf.cell(35, 8, f"{row['Cena']:.2f}", 1, align="R")
        pdf.cell(40, 8, f"{s:.2f}", 1, align="R")
        pdf.ln()

    pdf.ln(4)
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(150, 10, "KOPĀ:", 0, align="R")
    pdf.cell(40, 10, f"{kopa:.2f} EUR", 0, align="R")

    # fpdf2 atgriež bytes ar dest="S"
    return pdf.output(dest="S")


# -------------------------
# 4) GALVENĀ PROGRAMMA
# -------------------------
st.set_page_config(page_title="MLK House Tāmētājs", layout="wide")

if check_password():
    if os.path.exists("mlkhouse.jpg"):
        st.image("mlkhouse.jpg", use_container_width=True)

    st.title("🏠 MLK House Tāmētājs")

    faila_vards = "katalogs.xlsx"
    try:
        df_kat = ieladet_katalogu(faila_vards)
    except Exception as e:
        st.error(f"Kļūda katalogā: {e}")
        st.stop()

    KATALOGS = katalogs_dict(df_kat)

    if "tame" not in st.session_state:
        st.session_state.tame = pd.DataFrame(columns=["Materials", "Daudzums", "Cena"])

    # Ievade
    with st.expander("Pievienot materiālu", expanded=True):
        if len(KATALOGS) == 0:
            st.warning("Katalogs ir tukšs.")
            st.stop()

        izvele = st.selectbox("Izvēlies materiālu:", list(KATALOGS.keys()))
        cena = float(KATALOGS[izvele])
        st.write(f"Cena: **{cena:.2f} EUR**")

        daudz = st.number_input("Daudzums:", min_value=0.0, step=1.0, value=1.0)

        if st.button("Pievienot sarakstam"):
            df = st.session_state.tame.copy()

            # Ja materiāls jau ir sarakstā → pieskaitām daudzumu (LEAN: mazāk rindas, vairāk skaidrība)
            if (df["Materials"] == izvele).any():
                idx = df.index[df["Materials"] == izvele][0]
                df.loc[idx, "Daudzums"] = float(df.loc[idx, "Daudzums"]) + float(daudz)
                df.loc[idx, "Cena"] = cena
            else:
                jauns = pd.DataFrame({"Materials": [izvele], "Daudzums": [daudz], "Cena": [cena]})
                df = pd.concat([df, jauns], ignore_index=True)

            st.session_state.tame = df
            st.rerun()

    # Rezultāti
    df = st.session_state.tame.copy()
    if not df.empty:
        st.subheader("Tāmes kopsavilkums")
        df["Daudzums"] = pd.to_numeric(df["Daudzums"], errors="coerce").fillna(0.0)
        df["Cena"] = pd.to_numeric(df["Cena"], errors="coerce").fillna(0.0)
        df["Summa"] = df["Daudzums"] * df["Cena"]

        st.dataframe(df, use_container_width=True)

        kopa = float(df["Summa"].sum())
        st.metric("KOPĒJĀ SUMMA", f"{kopa:.2f} EUR")

        c1, c2 = st.columns(2)
        with c1:
            try:
                pdf_data = create_pdf(df, kopa)
                st.download_button("📥 Lejupielādēt PDF", data=pdf_data, file_name="tame.pdf")
            except Exception as e:
                st.error(f"PDF kļūda: {e}")

        with c2:
            if st.button("Notīrīt visu"):
                st.session_state.tame = pd.DataFrame(columns=["Materials", "Daudzums", "Cena"])
                st.rerun()
    else:
        st.info("Pievieno materiālus, lai izveidotu tāmi.")
