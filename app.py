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
            if pwd == "buve2024": # Šī ir tava parole
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Nepareiza parole")
        return False
    return True

# 2. Lietotne
if check_password():
    st.title("🏠 Māju tāmēšanas sistēma")
    
    if 'data' not in st.session_state:
        st.session_state.data = pd.DataFrame(columns=['Materials', 'Daudzums', 'Cena'])

    with st.form("mana_forma", clear_on_submit=True):
        m = st.text_input("Materiāls")
        d = st.number_input("Daudzums", min_value=0.0)
        c = st.number_input("Cena (EUR)", min_value=0.0)
        if st.form_submit_button("Pievienot"):
            jauns = pd.DataFrame({'Materials': [m], 'Daudzums': [d], 'Cena': [c]})
            st.session_state.data = pd.concat([st.session_state.data, jauns], ignore_index=True)

    df = st.session_state.data.copy()
    if not df.empty:
        df['Summa'] = df['Daudzums'] * df['Cena']
        st.table(df)
        st.write(f"*KOPĀ: {df['Summa'].sum():.2f} EUR*")
