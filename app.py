import streamlit as st
import pandas as pd
from fpdf import FPDF
import os

# 1. PAROLES PĀRBAUDE
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    if not st.session_state["password_correct"]:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.write("### MLK House Sistēma")
            pwd = st.text_input("Ievadiet paroli", type="password")
            if st.button("Ieiet"):
                if pwd == "buve2024":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("Nepareiza parole!")
        return False
    return True

# 2. DATU IELĀDE NO EXCEL
def ieladet_katalogu():
    faila_vards = "katalogs.xlsx"
    if os.path.exists(faila_vards):
        try:
            df_kat = pd.read_excel(faila_vards)
            return dict(zip(df_kat['Materials'], df_kat['Cena']))
        except:
            return {"Kļūda Excel nolasīšanā": 0.0}
    return {"Katalogs nav atrasts": 0.0}

# 3. PDF FUNKCIJA
def create_pdf(df, kopa):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="BUVNIECIBAS TAME", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(80, 10, "Materials", 1)
    pdf.cell(30, 10, "Daudz.", 1)
    pdf.cell(40, 10, "Cena", 1)
    pdf.cell(40, 10, "Summa", 1)
    pdf.ln()
    pdf.set_font("Arial", '', 12)
    for _, row in df.iterrows():
        s = row['Daudzums'] * row['Cena']
        pdf.cell(80, 10, str(row['Materials']), 1)
        pdf.cell(30, 10, str(row['Daudzums']), 1)
        pdf.cell(40, 10, f"{row['Cena']:.2f}", 1)
        pdf.cell(40, 10, f"{s:.2f}", 1)
        pdf.ln()
    pdf.ln(5)
    pdf.cell(150, 10, "KOPA:", 0)
    pdf.cell(40, 10, f"{kopa:.2f} EUR", 0)
    return pdf.output(dest='S').encode('latin-1')

# 4. GALVENĀ PROGRAMMA
if check_password():
    # Attēls augšā
    if os.path.exists("mlkhouse.jpg"):
        st.image("mlkhouse.jpg", use_container_width=True)
    
    st.title("🏠 MLK House Tāmētājs")
    KATALOGS = ieladet_katalogu()
    
    if 'tame' not in st.session_state:
        st.session_state.tame = pd.DataFrame(columns=['Materials', 'Daudzums', 'Cena'])

    # Ievade
    with st.expander("Pievienot materiālu", expanded=True):
        izvele = st.selectbox("Izvēlies materiālu:", list(KATALOGS.keys()))
        cena = KATALOGS[izvele]
        st.write(f"Cena: {cena:.2f} EUR")
        daudz = st.number_input("Daudzums:", min_value=0.0, step=1.0, value=1.0)
        
        if st.button("Pievienot sarakstam"):
            jauns = pd.DataFrame({'Materials': [izvele], 'Daudzums': [daudz], 'Cena': [cena]})
            st.session_state.tame = pd.concat([st.session_state.tame, jauns], ignore_index=True)
            st.rerun()

    # Rezultāti
    df = st.session_state.tame
    if not df.empty:
        st.subheader("Tāmes kopsavilkums")
        df['Summa'] = df['Daudzums'] * df['Cena']
        st.table(df)
        
        kopa = df['Summa'].sum()
        st.metric("KOPĒJĀ SUMMA", f"{kopa:.2f} EUR")
        
        c1, c2 = st.columns(2)
        with c1:
            pdf_data = create_pdf(df, kopa)
            st.download_button("📥 Lejupielādēt PDF", data=pdf_data, file_name="tame.pdf")
        with c2:
            if st.button("Notīrīt visu"):
                st.session_state.tame = pd.DataFrame(columns=['Materials', 'Daudzums', 'Cena'])
                st.rerun()
