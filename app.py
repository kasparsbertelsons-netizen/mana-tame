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

# 2. PDF ģenerēšanas funkcija
def create_pdf(df):
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
    kopa = 0
    for index, row in df.iterrows():
        summa = row['Daudzums'] * row['Cena']
        kopa += summa
        pdf.cell(80, 10, str(row['Materials']), 1)
        pdf.cell(30, 10, str(row['Daudzums']), 1)
        pdf.cell(40, 10, f"{row['Cena']:.2f}", 1)
        pdf.cell(40, 10, f"{summa:.2f}", 1)
        pdf.ln()

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(150, 10, "KOPA (bez PVN):", 0)
    pdf.cell(40, 10, f"{kopa:.2f} EUR", 0)
    return pdf.output(dest='S').encode('latin-1')

# 3. Galvenā programma
if check_password():
    st.title("🏠 Māju tāmēšanas sistēma")
    
    # Saglabājam datus sesijā
    if 'tame_data' not in st.session_state:
        st.session_state.tame_data = pd.DataFrame(columns=['Materials', 'Daudzums', 'Cena'])

    # Ievades forma
    with st.form("ievade", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        mat = col1.text_input("Materiāls")
        daudz = col2.number_input("Daudzums", min_value=0.0, step=0.1)
        cena = col3.number_input("Cena (EUR)", min_value=0.0, step=0.01)
        if st.form_submit_button("Pievienot tāmei"):
            jauna_rinda = pd.DataFrame({'Materials': [mat], 'Daudzums': [daudz], 'Cena': [cena]})
            st.session_state.tame_data = pd.concat([st.session_state.tame_data, jauna_rinda], ignore_index=True)

    # Parādām tabulu un aprēķinus
    df = st.session_state.tame_data
    if not df.empty:
        df_display = df.copy()
        df_display['Summa'] = df_display['Daudzums'] * df_display['Cena']
        st.table(df_display)
        
        kopa = df_display['Summa'].sum()
        st.subheader(f"Kopējā summa: {kopa:.2f} EUR")

        # PDF Poga
        pdf_bytes = create_pdf(df)
        st.download_button(label="📥 Lejupielādēt PDF", data=pdf_bytes, file_name="tame.pdf", mime="application/pdf")
        
        if st.button("Notīrīt visu"):
            st.session_state.tame_data = pd.DataFrame(columns=['Materials', 'Daudzums', 'Cena'])
            st.rerun()
