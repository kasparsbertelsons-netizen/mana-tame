import os
import json
from datetime import date

import streamlit as st
import pandas as pd

# PDF: izmanto fpdf2 (requirements.txt: fpdf2)
from fpdf import FPDF


# -------------------------
# Lapas uzstādījumi
# -------------------------
st.set_page_config(page_title="MLK House Tāmētājs", layout="wide")


# -------------------------
# 1) PAROLES PĀRBAUDE
# -------------------------
def check_password() -> bool:
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("### MLK House Sistēma")
        pwd = st.text_input("Ievadiet paroli", type="password")
        if st.button("Ieiet", use_container_width=True):
            real_pwd = st.secrets.get("APP_PASSWORD", "mlk")  # secrets ir ieteicams
            if pwd == real_pwd:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Nepareiza parole!")
    return False


# -------------------------
# 2) KATALOGA IELĀDE (cache)
# -------------------------
@st.cache_data(show_spinner=False)
def load_catalog(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Materials", "Cena"])

    df = pd.read_excel(path)

    # Elastīgi pret kolonnu nosaukumiem (trim + tieši Materials/Cena)
    cols = {c.strip(): c for c in df.columns}
    if "Materials" not in cols or "Cena" not in cols:
        raise ValueError("Excel failā jābūt kolonnām: 'Materials' un 'Cena'.")

    df = df[[cols["Materials"], cols["Cena"]]].copy()
    df.columns = ["Materials", "Cena"]
    df["Materials"] = df["Materials"].astype(str).str.strip()
    df["Cena"] = pd.to_numeric(df["Cena"], errors="coerce").fillna(0.0)
    df = df[df["Materials"] != ""].drop_duplicates(subset=["Materials"], keep="last")

    return df


def to_catalog_dict(df: pd.DataFrame) -> dict:
    return dict(zip(df["Materials"], df["Cena"]))


# -------------------------
# 3) PDF helpers
# -------------------------
def safe_text_latin1(text: str) -> str:
    """Drošs teksts vecajiem core fontiem (ja nav TTF Unicode fonta)."""
    return (
        str(text)
        .replace("€", "EUR")
        .replace("–", "-")
        .replace("—", "-")
        .replace("×", "x")
        .replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .encode("latin-1", errors="ignore")
        .decode("latin-1")
    )


def create_pdf(
    df: pd.DataFrame,
    pamatsumma: float,
    uzcenojums_pct: float,
    pvn_pct: float,
    kopa_ar_pvn: float,
) -> bytes:
    """
    Ja ir DejaVuSans.ttf blakus app.py -> taisa Unicode PDF.
    Ja nav -> izmanto core fontus (Arial) ar safe_text_latin1().
    """
    pdf = FPDF()
    pdf.add_page()

    # mēģinam Unicode fontu
    font_path = os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")
    use_unicode = os.path.exists(font_path)

    if use_unicode:
        pdf.add_font("DejaVu", "", font_path, uni=True)
        pdf.add_font("DejaVu", "B", font_path, uni=True)
        pdf.set_font("DejaVu", "B", 16)
        title = "BUVNIECĪBAS TĀME"
    else:
        # Core fonts (Latin-1)
        pdf.set_font("Arial", "B", 16)
        title = safe_text_latin1("BUVNIECĪBAS TĀME")

    pdf.cell(0, 10, txt=title, ln=True, align="C")
    pdf.ln(6)

    # galvene
    if use_unicode:
        pdf.set_font("DejaVu", "B", 11)
        h_materials, h_qty, h_price, h_sum = "Materials", "Daudz.", "Cena", "Summa"
    else:
        pdf.set_font("Arial", "B", 11)
        h_materials = safe_text_latin1("Materials")
        h_qty = safe_text_latin1("Daudz.")
        h_price = safe_text_latin1("Cena")
        h_sum = safe_text_latin1("Summa")

    pdf.cell(90, 8, h_materials, 1)
    pdf.cell(25, 8, h_qty, 1, align="R")
    pdf.cell(35, 8, h_price, 1, align="R")
    pdf.cell(40, 8, h_sum, 1, align="R")
    pdf.ln()

    # rindas
    if use_unicode:
        pdf.set_font("DejaVu", "", 11)
    else:
        pdf.set_font("Arial", "", 11)

    for _, row in df.iterrows():
        mat = str(row["Materials"])
        if not use_unicode:
            mat = safe_text_latin1(mat)

        qty = float(row["Daudzums"])
        price = float(row["Cena"])
        s = qty * price

        pdf.cell(90, 8, mat[:45], 1)
        pdf.cell(25, 8, f"{qty:.2f}", 1, align="R")
        pdf.cell(35, 8, f"{price:.2f}", 1, align="R")
        pdf.cell(40, 8, f"{s:.2f}", 1, align="R")
        pdf.ln()

    pdf.ln(4)

    # kopsummas
    if use_unicode:
        pdf.set_font("DejaVu", "B", 12)
        l1 = "Pamatsumma:"
        l2 = f"Uzcenojums ({uzcenojums_pct:.2f}%):"
        l3 = f"PVN ({pvn_pct:.2f}%):"
        l4 = "KOPĀ ar PVN:"
    else:
        pdf.set_font("Arial", "B", 12)
        l1 = safe_text_latin1("Pamatsumma:")
        l2 = safe_text_latin1(f"Uzcenojums ({uzcenojums_pct:.2f}%):")
        l3 = safe_text_latin1(f"PVN ({pvn_pct:.2f}%):")
        l4 = safe_text_latin1("KOPĀ ar PVN:")

    ar_uzcen = pamatsumma * (1 + uzcenojums_pct / 100)
    pvn_sum = ar_uzcen * (pvn_pct / 100)

    pdf.cell(150, 8, l1, 0, align="R")
    pdf.cell(40, 8, f"{pamatsumma:.2f} EUR", 0, align="R")
    pdf.ln()

    pdf.cell(150, 8, l2, 0, align="R")
    pdf.cell(40, 8, f"{(ar_uzcen - pamatsumma):.2f} EUR", 0, align="R")
    pdf.ln()

    pdf.cell(150, 8, l3, 0, align="R")
    pdf.cell(40, 8, f"{pvn_sum:.2f} EUR", 0, align="R")
    pdf.ln()

    pdf.cell(150, 10, l4, 0, align="R")
    pdf.cell(40, 10, f"{kopa_ar_pvn:.2f} EUR", 0, align="R")

    # fpdf2 var atgriezt bytearray -> pārvēršam uz bytes
    return bytes(pdf.output(dest="S"))


# -------------------------
# 4) App UI
# -------------------------
if not check_password():
    st.stop()

# Logo
if os.path.exists("mlkhouse.jpg"):
    st.image("mlkhouse.jpg", use_container_width=True)

st.title("🏠 MLK House Tāmētājs")

# Sidebar aprēķini + darbības
st.sidebar.header("Aprēķini")
uzcenojums_pct = st.sidebar.number_input("Uzcenojums %", 0.0, 200.0, 10.0, 1.0)
pvn_pct = st.sidebar.number_input("PVN %", 0.0, 25.0, 21.0, 0.5)

st.sidebar.divider()

catalog_path = "katalogs.xlsx"
try:
    df_kat = load_catalog(catalog_path)
except Exception as e:
    st.error(f"Kļūda katalogā: {e}")
    st.stop()

if st.sidebar.button("🔄 Pārlasīt katalogu", use_container_width=True):
    load_catalog.clear()
    st.rerun()

KATALOGS = to_catalog_dict(df_kat)

if "tame" not in st.session_state:
    st.session_state.tame = pd.DataFrame(columns=["Materials", "Daudzums", "Cena"])

# Ielādēt/Saglabāt JSON
st.sidebar.subheader("Projekts")
up = st.sidebar.file_uploader("Ielādēt tāmi (JSON)", type=["json"])
if up:
    try:
        records = json.loads(up.read().decode("utf-8"))
        st.session_state.tame = pd.DataFrame(records)[["Materials", "Daudzums", "Cena"]]
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Neizdevās ielādēt JSON: {e}")

if not st.session_state.tame.empty:
    data = st.session_state.tame.to_dict(orient="records")
    st.sidebar.download_button(
        "💾 Saglabāt tāmi (JSON)",
        data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        file_name=f"tame_{date.today().isoformat()}.json",
        mime="application/json",
        use_container_width=True,
    )

if st.sidebar.button("🗑️ Notīrīt visu", use_container_width=True):
    st.session_state.tame = pd.DataFrame(columns=["Materials", "Daudzums", "Cena"])
    st.rerun()

# -------------------------
# Pievienot materiālu
# -------------------------
with st.expander("Pievienot materiālu", expanded=True):
    if len(KATALOGS) == 0:
        st.warning("Katalogs ir tukšs vai nav atrasts.")
        st.stop()

    q = st.text_input("Meklēt materiālu (daļa no nosaukuma)")
    keys = list(KATALOGS.keys())
    if q:
        keys = [k for k in keys if q.lower() in k.lower()]
        if not keys:
            st.info("Nekas nav atrasts pēc meklēšanas.")
            keys = list(KATALOGS.keys())

    izvele = st.selectbox("Izvēlies materiālu:", keys)
    cena = float(KATALOGS[izvele])
    st.write(f"Cena: **{cena:.2f} EUR**")

    daudz = st.number_input("Daudzums:", min_value=0.0, step=1.0, value=1.0)

    c1, c2 = st.columns([1, 1])
    with c1:
        add_clicked = st.button("➕ Pievienot sarakstam", use_container_width=True)
    with c2:
        merge_clicked = st.button("🧹 Apvienot vienādos", use_container_width=True)

    if add_clicked:
        if float(daudz) <= 0:
            st.warning("Daudzumam jābūt > 0.")
        else:
            df = st.session_state.tame.copy()
            if (df["Materials"] == izvele).any():
                idx = df.index[df["Materials"] == izvele][0]
                df.loc[idx, "Daudzums"] = float(df.loc[idx, "Daudzums"]) + float(daudz)
                df.loc[idx, "Cena"] = cena
            else:
                jauns = pd.DataFrame({"Materials": [izvele], "Daudzums": [daudz], "Cena": [cena]})
                df = pd.concat([df, jauns], ignore_index=True)

            # apvieno (drošībai)
            df["Daudzums"] = pd.to_numeric(df["Daudzums"], errors="coerce").fillna(0.0)
            df["Cena"] = pd.to_numeric(df["Cena"], errors="coerce").fillna(0.0)
            df = df.groupby("Materials", as_index=False).agg({"Daudzums": "sum", "Cena": "last"})

            st.session_state.tame = df
            st.rerun()

    if merge_clicked and not st.session_state.tame.empty:
        df = st.session_state.tame.copy()
        df["Daudzums"] = pd.to_numeric(df["Daudzums"], errors="coerce").fillna(0.0)
        df["Cena"] = pd.to_numeric(df["Cena"], errors="coerce").fillna(0.0)
        df = df.groupby("Materials", as_index=False).agg({"Daudzums": "sum", "Cena": "last"})
        st.session_state.tame = df
        st.rerun()


# -------------------------
# Tāmes kopsavilkums + rediģēšana
# -------------------------
df = st.session_state.tame.copy()

if df.empty:
    st.info("Pievieno materiālus, lai izveidotu tāmi.")
    st.stop()

df["Daudzums"] = pd.to_numeric(df["Daudzums"], errors="coerce").fillna(0.0)
df["Cena"] = pd.to_numeric(df["Cena"], errors="coerce").fillna(0.0)
df["Summa"] = df["Daudzums"] * df["Cena"]

st.subheader("Tāmes kopsavilkums (rediģējams)")

edited = st.data_editor(
    df,
    use_container_width=True,
    num_rows="dynamic",  # ļauj dzēst/ pielikt rindas
    column_config={
        "Materials": st.column_config.TextColumn("Materials"),
        "Daudzums": st.column_config.NumberColumn("Daudzums", min_value=0.0, step=1.0),
        "Cena": st.column_config.NumberColumn("Cena", min_value=0.0, step=0.01, format="%.2f"),
        "Summa": st.column_config.NumberColumn("Summa", disabled=True, format="%.2f"),
    },
    disabled=["Summa"],
    key="tame_editor",
)

# saglabā atpakaļ (bez Summa)
save_back = edited.drop(columns=["Summa"], errors="ignore").copy()
save_back["Daudzums"] = pd.to_numeric(save_back["Daudzums"], errors="coerce").fillna(0.0)
save_back["Cena"] = pd.to_numeric(save_back["Cena"], errors="coerce").fillna(0.0)
save_back = save_back[save_back["Daudzums"] > 0].copy()

# apvieno vienādos pēc editora
save_back = save_back.groupby("Materials", as_index=False).agg({"Daudzums": "sum", "Cena": "last"})
st.session_state.tame = save_back

# pārrēķins metrikām
df2 = save_back.copy()
df2["Summa"] = df2["Daudzums"] * df2["Cena"]

pamatsumma = float(df2["Summa"].sum())
ar_uzcen = pamatsumma * (1 + uzcenojums_pct / 100)
kopa_ar_pvn = ar_uzcen * (1 + pvn_pct / 100)

m1, m2, m3 = st.columns(3)
m1.metric("Pamatsumma", f"{pamatsumma:.2f} EUR")
m2.metric("Ar uzcenojumu", f"{ar_uzcen:.2f} EUR")
m3.metric("Kopā ar PVN", f"{kopa_ar_pvn:.2f} EUR")

# PDF lejupielāde
st.divider()
c1, c2 = st.columns([1, 1])

with c1:
    try:
        pdf_data = create_pdf(df2, pamatsumma, uzcenojums_pct, pvn_pct, kopa_ar_pvn)
        st.download_button(
            "📥 Lejupielādēt PDF",
            data=pdf_data,
            file_name=f"tame_{date.today().isoformat()}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"PDF kļūda: {e}")

with c2:
    st.caption("PDF Unicode režīms ieslēdzas automātiski, ja repo ir 'DejaVuSans.ttf'.")
    st.caption("Ja fonta nav, PDF izmantos parastos fontus un droši aizvietos € / – / × utt.")
