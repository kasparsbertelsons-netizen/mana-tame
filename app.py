import os
import re
from datetime import date
from urllib.parse import quote

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF

st.set_page_config(page_title="MLK House Tāmētājs", layout="wide")


# -------------------------
# 1) PAROLE
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
            real_pwd = st.secrets.get("APP_PASSWORD", "buve2024")
            if pwd == real_pwd:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Nepareiza parole!")
    return False


# -------------------------
# 2) LOGO
# -------------------------
def show_logo():
    candidates = [
        "mlkhouse.JPG",
        "mlkhouse.png",
        "logo.png",
        "logo.jpg",
        "logo.jpeg",
        "logo.webp",
        "logo.png.png",
        "images/logo.png",
        "images/mlkhouse.jpg",
    ]
    for p in candidates:
        if os.path.exists(p):
            st.image(p, use_container_width=True)
            return


# -------------------------
# 3) KATALOGS: Materials / Price / Unit / Image / Description / URL
# -------------------------
@st.cache_data(show_spinner=False)
def load_catalog(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Materials", "Price", "Unit", "Image", "Description", "URL"])

    df = pd.read_excel(path)

    for col in ["Materials", "Price"]:
        if col not in df.columns:
            raise ValueError(f"Excel failā trūkst kolonna: {col}")

    # optional kolonnas
    if "Unit" not in df.columns:
        df["Unit"] = ""
    if "Image" not in df.columns:
        df["Image"] = ""
    if "Description" not in df.columns:
        df["Description"] = ""
    if "URL" not in df.columns:
        df["URL"] = ""

    df = df[["Materials", "Price", "Unit", "Image", "Description", "URL"]].copy()

    df["Materials"] = df["Materials"].astype(str).str.strip()
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce").fillna(0.0)

    for c in ["Unit", "Image", "Description", "URL"]:
        df[c] = df[c].astype(str).fillna("").str.strip()
        df.loc[df[c].str.lower() == "nan", c] = ""

    df = df[df["Materials"] != ""].drop_duplicates(subset=["Materials"], keep="last")
    return df


def catalog_price_dict(df: pd.DataFrame) -> dict:
    return dict(zip(df["Materials"], df["Price"]))


# -------------------------
# 4) ATTĒLI
# -------------------------
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def is_direct_image_url(u: str) -> bool:
    u = (u or "").strip().lower()
    return u.startswith("http") and any(u.split("?")[0].endswith(ext) for ext in IMAGE_EXTS)


@st.cache_data(show_spinner=False)
def fetch_image_bytes(url: str) -> tuple[bytes | None, str]:
    try:
        safe_url = quote(url.strip(), safe=":/?&=%#.+-@~")
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }
        r = requests.get(safe_url, timeout=12, headers=headers, allow_redirects=True)
        info = f"HTTP {r.status_code}, content-type={r.headers.get('content-type')}, len={len(r.content)}"
        r.raise_for_status()
        return r.content, info
    except Exception as e:
        return None, f"ERROR: {e}"


def show_material_image(path_or_url: str, width: int = 350):
    if not path_or_url:
        return

    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        content, info = fetch_image_bytes(path_or_url)
        if content:
            st.image(content, caption="Materiāla attēls", width=width)
        else:
            st.warning(f"Neizdevās ielādēt attēlu. {info}")
        return

    if os.path.exists(path_or_url):
        st.image(path_or_url, caption="Materiāla attēls", width=width)
    else:
        st.warning(f"Attēla fails nav atrasts: {path_or_url}")


# -------------------------
# 5) AUTO APRAKSTS NO URL
# -------------------------
def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


@st.cache_data(show_spinner=False)
def generate_description_from_url(url: str) -> str:
    if not url:
        return ""

    try:
        safe_url = quote(url.strip(), safe=":/?&=%#.+-@~")
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        r = requests.get(safe_url, timeout=12, headers=headers, allow_redirects=True)
        r.raise_for_status()

        ct = (r.headers.get("content-type") or "").lower()
        if "text/html" not in ct and "application/xhtml" not in ct:
            return ""

        soup = BeautifulSoup(r.text, "html.parser")

        og_desc = soup.find("meta", property="og:description")
        meta_desc = soup.find("meta", attrs={"name": "description"})
        title_tag = soup.find("title")
        h1 = soup.find("h1")
        p = soup.find("p")

        headline = _clean_text(h1.get_text(" ", strip=True) if h1 else "")
        if not headline:
            headline = _clean_text(title_tag.get_text(" ", strip=True) if title_tag else "")
        headline = headline[:120]

        desc = _clean_text(og_desc.get("content", "") if og_desc else "")
        if not desc:
            desc = _clean_text(meta_desc.get("content", "") if meta_desc else "")
        if not desc and p:
            desc = _clean_text(p.get_text(" ", strip=True))
        desc = desc[:350]

        parts = [x for x in [headline, desc] if x]
        return "\n\n".join(parts).strip()
    except Exception:
        return ""


# -------------------------
# 6) PDF
# -------------------------
def safe_text_latin1(text: str) -> str:
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


def create_pdf(df: pd.DataFrame, pamatsumma: float, uzcenojums_pct: float, pvn_pct: float, kopa_ar_pvn: float) -> bytes:
    pdf = FPDF()
    pdf.add_page()

    font_path = os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")
    use_unicode = os.path.exists(font_path)

    if use_unicode:
        pdf.add_font("DejaVu", "", font_path, uni=True)
        pdf.add_font("DejaVu", "B", font_path, uni=True)
        pdf.set_font("DejaVu", "B", 16)
        title = "BUVNIECĪBAS TĀME"
    else:
        pdf.set_font("Arial", "B", 16)
        title = safe_text_latin1("BUVNIECĪBAS TĀME")

    pdf.cell(0, 10, txt=title, ln=True, align="C")
    pdf.ln(6)

    if use_unicode:
        pdf.set_font("DejaVu", "B", 11)
        h = ["Materials", "Mērv.", "Daudz.", "Cena", "Summa"]
    else:
        pdf.set_font("Arial", "B", 11)
        h = list(map(safe_text_latin1, ["Materials", "Mērv.", "Daudz.", "Cena", "Summa"]))

    pdf.cell(70, 8, h[0], 1)
    pdf.cell(20, 8, h[1], 1)
    pdf.cell(25, 8, h[2], 1, align="R")
    pdf.cell(35, 8, h[3], 1, align="R")
    pdf.cell(40, 8, h[4], 1, align="R")
    pdf.ln()

    pdf.set_font("DejaVu" if use_unicode else "Arial", "", 11)

    for _, row in df.iterrows():
        mat = str(row["Materials"])
        unit = str(row.get("Unit", ""))
        if not use_unicode:
            mat = safe_text_latin1(mat)
            unit = safe_text_latin1(unit)

        qty = float(row["Daudzums"])
        price = float(row["Cena"])
        s = qty * price

        pdf.cell(70, 8, mat[:35], 1)
        pdf.cell(20, 8, unit[:8], 1)
        pdf.cell(25, 8, f"{qty:.2f}", 1, align="R")
        pdf.cell(35, 8, f"{price:.2f}", 1, align="R")
        pdf.cell(40, 8, f"{s:.2f}", 1, align="R")
        pdf.ln()

    pdf.ln(4)

    ar_uzcen = pamatsumma * (1 + uzcenojums_pct / 100)
    pvn_sum = ar_uzcen * (pvn_pct / 100)

    pdf.set_font("DejaVu" if use_unicode else "Arial", "B", 12)

    labels = [
        ("Pamatsumma:", pamatsumma),
        (f"Uzcenojums ({uzcenojums_pct:.2f}%):", ar_uzcen - pamatsumma),
        (f"PVN ({pvn_pct:.2f}%):", pvn_sum),
        ("KOPĀ ar PVN:", kopa_ar_pvn),
    ]
    if not use_unicode:
        labels = [(safe_text_latin1(a), b) for a, b in labels]

    for i, (lab, val) in enumerate(labels):
        pdf.cell(150, 8 if i < 3 else 10, lab, 0, align="R")
        pdf.cell(40, 8 if i < 3 else 10, f"{val:.2f} EUR", 0, align="R")
        pdf.ln()

    return bytes(pdf.output(dest="S"))


# -------------------------
# 7) APP
# -------------------------
if not check_password():
    st.stop()

show_logo()
st.title("🏠 MLK House Tāmētājs")

st.sidebar.header("Aprēķini")
uzcenojums_pct = st.sidebar.number_input("Uzcenojums %", 0.0, 200.0, 10.0, 1.0)
pvn_pct = st.sidebar.number_input("PVN %", 0.0, 25.0, 21.0, 0.5)
st.sidebar.divider()

if st.sidebar.button("🗑️ Notīrīt visu", use_container_width=True):
    st.session_state.tame = pd.DataFrame(columns=["Materials", "Daudzums", "Cena", "Unit"])
    st.rerun()

catalog_path = "katalogs.xlsx"
df_kat = load_catalog(catalog_path)

if st.sidebar.button("🔄 Pārlasīt katalogu", use_container_width=True):
    load_catalog.clear()
    generate_description_from_url.clear()
    fetch_image_bytes.clear()
    st.rerun()

CAT_PRICE = catalog_price_dict(df_kat)
CAT_UNIT = dict(zip(df_kat["Materials"], df_kat["Unit"]))
CAT_IMG = dict(zip(df_kat["Materials"], df_kat["Image"]))
CAT_DESC = dict(zip(df_kat["Materials"], df_kat["Description"]))
CAT_URL = dict(zip(df_kat["Materials"], df_kat["URL"]))

if "tame" not in st.session_state:
    st.session_state.tame = pd.DataFrame(columns=["Materials", "Daudzums", "Cena", "Unit"])


with st.expander("Pievienot materiālu", expanded=True):
    if len(CAT_PRICE) == 0:
        st.warning("Katalogs ir tukšs vai nav atrasts.")
        st.stop()

    q = st.text_input("Meklēt materiālu (daļa no nosaukuma)")
    keys = list(CAT_PRICE.keys())
    if q:
        keys = [k for k in keys if q.lower() in k.lower()]
        if not keys:
            st.info("Nekas nav atrasts pēc meklēšanas.")
            keys = list(CAT_PRICE.keys())

    izvele = st.selectbox("Izvēlies materiālu:", keys)
    cena = float(CAT_PRICE[izvele])
    unit = str(CAT_UNIT.get(izvele, "")).strip()

    img = str(CAT_IMG.get(izvele, "")).strip()
    desc = str(CAT_DESC.get(izvele, "")).strip()
    url = str(CAT_URL.get(izvele, "")).strip()

    auto_desc = ""
    if (not desc) and url:
        auto_desc = generate_description_from_url(url)

    # Produkta kartīte
    if img or desc or auto_desc:
        c1, c2 = st.columns([1, 1])  # platāks tekstam
        with c1:
            if img and is_direct_image_url(img):
                show_material_image(img, width=350)
            elif img and img.startswith("http") and not is_direct_image_url(img):
                st.info("Kolonnā 'Image' vajag tiešo .jpg/.png linku.")
        with c2:
            st.markdown(f"## {izvele}")
            if unit:
                st.markdown(f"**Cena:** {cena:.2f} EUR / {unit}")
            else:
                st.markdown(f"**Cena:** {cena:.2f} EUR")
            st.divider()
            st.markdown("### Apraksts")
            if desc:
                st.write(desc)
            elif auto_desc:
                st.write(auto_desc)
            else:
                st.caption("Nav apraksta.")
            if url:
                st.link_button("🔗 Atvērt produkta lapu", url)

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
                df.loc[idx, "Unit"] = unit
            else:
                jauns = pd.DataFrame({"Materials": [izvele], "Daudzums": [daudz], "Cena": [cena], "Unit": [unit]})
                df = pd.concat([df, jauns], ignore_index=True)

            df["Daudzums"] = pd.to_numeric(df["Daudzums"], errors="coerce").fillna(0.0)
            df["Cena"] = pd.to_numeric(df["Cena"], errors="coerce").fillna(0.0)
            df = df.groupby("Materials", as_index=False).agg({"Daudzums": "sum", "Cena": "last", "Unit": "last"})
            st.session_state.tame = df
            st.rerun()

    if merge_clicked and not st.session_state.tame.empty:
        df = st.session_state.tame.copy()
        df["Daudzums"] = pd.to_numeric(df["Daudzums"], errors="coerce").fillna(0.0)
        df["Cena"] = pd.to_numeric(df["Cena"], errors="coerce").fillna(0.0)
        df = df.groupby("Materials", as_index=False).agg({"Daudzums": "sum", "Cena": "last", "Unit": "last"})
        st.session_state.tame = df
        st.rerun()


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
    num_rows="dynamic",
    column_config={
        "Materials": st.column_config.TextColumn("Materials"),
        "Unit": st.column_config.TextColumn("Unit"),
        "Daudzums": st.column_config.NumberColumn("Daudzums", min_value=0.0, step=1.0),
        "Cena": st.column_config.NumberColumn("Cena", min_value=0.0, step=0.01, format="%.2f"),
        "Summa": st.column_config.NumberColumn("Summa", disabled=True, format="%.2f"),
    },
    disabled=["Summa"],
    key="tame_editor",
)

save_back = edited.drop(columns=["Summa"], errors="ignore").copy()
save_back["Daudzums"] = pd.to_numeric(save_back["Daudzums"], errors="coerce").fillna(0.0)
save_back["Cena"] = pd.to_numeric(save_back["Cena"], errors="coerce").fillna(0.0)
save_back["Unit"] = save_back.get("Unit", "").astype(str).fillna("").str.strip()
save_back = save_back[save_back["Daudzums"] > 0].copy()
save_back = save_back.groupby("Materials", as_index=False).agg({"Daudzums": "sum", "Cena": "last", "Unit": "last"})
st.session_state.tame = save_back

df2 = save_back.copy()
df2["Summa"] = df2["Daudzums"] * df2["Cena"]

pamatsumma = float(df2["Summa"].sum())
ar_uzcen = pamatsumma * (1 + uzcenojums_pct / 100)
kopa_ar_pvn = ar_uzcen * (1 + pvn_pct / 100)

m1, m2, m3 = st.columns(3)
m1.metric("Pamatsumma", f"{pamatsumma:.2f} EUR")
m2.metric("Ar uzcenojumu", f"{ar_uzcen:.2f} EUR")
m3.metric("Kopā ar PVN", f"{kopa_ar_pvn:.2f} EUR")

st.divider()
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
