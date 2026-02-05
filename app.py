import streamlit as st
import pandas as pd
from fpdf import FPDF

# 1. Paroles pārbaude
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    if not st.session_state["password_correct"]:
        pwd = st.text_input("Ievadi paroli", type="password")
        if st.button("Ieiet"):
            if pwd == "buve2024":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Nepareiza parole")
        return False
    return True

# 2. PDF funkcija
def generet_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="MAJAS TAME", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(80, 10, "Materials", 1)
    pdf.cell(30, 10, "Daudzums", 1)
    pdf.cell(40, 10, "Summa (EUR)", 1)
    pdf.ln()
    pdf.set_font("Arial", '', 12)
    kopa = 0
    for index, row in df.iterrows():
        summa = row['Daudzums'] * row['Cena']
        kopa += summa
        pdf.cell(80, 10, str(row['Materials']), 1)
        pdf.cell(30, 10, str(row['Daudzums']), 1)
        pdf.cell(40, 10, f"{summa:.2f}", 1)
        pdf.ln()
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(110, 10, "KOPA:", 0)
    pdf.cell(40, 10, f"{kopa:.2f} EUR", 0)
    return pdf.output(dest='S').encode('latin-1')

# 3. Lietotne
if check_password():
    st.title("🏠 Māju tāmēšanas sistēma")
    
    if 'data' not in st.session_state:
        st.session_state.data = pd.DataFrame(columns=['Materials', 'Daudzums', 'Cena'])

    with st.form("mana_forma", clear_on_submit=True):
        m = st.text_input("Materiāls")
        d = st.number_input("Daudzums", min_value=0.0, step=0.1)
        c = st.number_input("Cena par vienību (EUR)", min_value=0.0, step=0.01)
        if st.form_submit_button("Pievienot tāmei"):
            jauns = pd.DataFrame({'Materials': [m], 'Daudzums': [d], 'Cena': [c]})
            st.session_state.data = pd.concat([st.session_state.data, jauns], ignore_index=True)

    df = st.session_state.data.copy()
    if not df.empty:
        df['Summa'] = df['Daudzums'] * df['Cena']
        st.table(df)
        kopskaits = df['Summa'].sum()
        st.write(f"### Kopējā summa: {kopskaits:.2f} EUR")

        # Poga PDF lejupielādei
        pdf_data = generet_pdf(df)
        st.download_button(label="📥 Lejupielādēt PDF tāmi", data=pdf_data, file_name="tame.pdf", mime="application/pdf")
        
        if st.button("Notīrīt tāmi"):
            st.session_state.data = pd.DataFrame(columns=['Materials', 'Daudzums', 'Cena'])
            st.rerun()
