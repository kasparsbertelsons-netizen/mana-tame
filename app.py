import streamlit as st
import pandas as pd
from fpdf import FPDF
import os

# 1. PAROLES PĀRBAUDE
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

# 2. DATU IELĀDE NO EXCEL (KATALOGS)
def ieladet_katalogu():
    faila_vards = "katalogs.xlsx"
    if os.path.exists(faila_vards):
        # Nolasa Excel failu - pieņemam, ka ir stabiņi 'Materials' un 'Cena'
        df_kat = pd.read_excel(faila_vards)
        return dict(zip(df_kat['Materials'], df_kat['Cena']))
    else:
        # Rezerves variants, ja Excel faila nav
        return {"Paraugs: Betons": 100.0, "Paraugs: Bloki": 2.50}

# 3. GALVENĀ LIETOTNE
if check_password():
    # --- PIEVIENO ATTĒLU / LOGO ---
    # Ja tev GitHub ir fails 'logo.png', tas parādīsies šeit
    if os.path.exists("logo.png.png"):
        st.image("logo.png.png", width=200)
    
    st.title("🏠 Dinamiskā Tāmēšanas Sistēma")
    
    # Ielādējam katalogu no Excel
    KATALOGS = ieladet_katalogu()
    
    if 'tame_data' not in st.session_state:
        st.session_state.tame_data = pd.DataFrame(columns=['Materials', 'Daudzums', 'Cena'])

    # IZVĒLE
    st.subheader("Izvēlieties pozīcijas no Excel kataloga")
    izveletais_mat = st.selectbox("Materiāls:", list(KATALOGS.keys()))
    pasreizeja_cena = KATALOGS[izveletais_mat]
    
    st.write(f"Cena: *{pasreizeja_cena:.2f} EUR*")
    daudzums = st.number_input("Daudzums:", min_value=0.0, step=1.0)
    
    if st.button("Pievienot"):
        jauna_rinda = pd.DataFrame({
            'Materials': [izveletais_mat], 
            'Daudzums': [daudzums], 
            'Cena': [pasreizeja_cena]
        })
        st.session_state.tame_data = pd.concat([st.session_state.tame_data, jauna_rinda], ignore_index=True)

    # ATSKAITE (Tabula)
    df = st.session_state.tame_data
    if not df.empty:
        df_copy = df.copy()
        df_copy['Summa'] = df_copy['Daudzums'] * df_copy['Cena']
        st.table(df_copy)
        st.metric("KOPĀ", f"{df_copy['Summa'].sum():.2f} EUR")
