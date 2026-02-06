import streamlit as st
import pandas as pd
from fpdf import FPDF
import os

# --- 1. KONFIGURĀCIJA UN PAROLES PĀRBAUDE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    if not st.session_state["password_correct"]:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.write("### Piekļuve tāmēšanas sistēmai")
            pwd = st.text_input("Ievadiet paroli", type="password")
            if st.button("Ieiet"):
                if pwd == "buve2024": # Tava parole
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("Nepareiza parole!")
        return False
    return True

# --- 2. EXCEL DATU IELĀDE ---
def ieladet_katalogu():
    faila_vards = "katalogs.xlsx"
    if os.path.exists(faila_vards):
        try:
            df_kat = pd.read_excel(faila_vards)
            # Pārveidojam vārdnīcā: Atslēga = Materiāls, Vērtība = Cena
            return dict(zip(df_kat['Materials'], df_kat['Cena']))
        except Exception as e:
            st.error(f"Kļūda nolasot Excel: {e}")
            return {"Kļūda Excel failā": 0.0}
    else:
        return {"Nav atrasts katalogs.xlsx": 0.0}

# --- 3. PDF ĢENERĒŠANA ---
def create_pdf(df, kopa):
    pdf = FPDF()
    pdf.add_page()
    # Piezīme: Standarta FPDF ne vienmēr atbalsta LV mīkstinājuma zīmes bez papildus fontiem
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="BUVNIECIBAS TAME", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(80, 10, "Materials", 1)
    pdf.cell(30, 10, "Daudzums", 1)
    pdf.cell(40, 10, "Cena (Vien.)", 1)
    pdf.cell(40, 10, "Summa", 1)
    pdf.ln()

    pdf.set_font("Arial", '', 11)
    for index, row in df.iterrows():
        summa = row['Daudzums'] * row['Cena']
        pdf.cell(80, 10, str(row['Materials']), 1)
        pdf.cell(30, 10, str(row['Daudzums']), 1)
        pdf.cell(40, 10, f"{row['Cena']:.2f}", 1)
        pdf.cell(40, 10, f"{summa:.2f}", 1)
        pdf.ln()

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(150, 10, "KOPA (EUR):", 0)
    pdf.cell(40, 10, f"{kopa:.2f}", 0)
    return pdf.output(dest='S').encode('latin-1')

# --- 4. LIETOTNES LOĢIKA ---
if check_password():
    # Galvenais attēls augšpusē
    if os.path.exists("mlkhouse.jpg"):
        st.image("mlkhouse.jpg", use_container_width=True)
    
    st.title("🏠 MLK House Tāmēšanas Portāls")
    
    # Ielādējam materiālus no Excel
    KATALOGS = ieladet_katalogu()
    
    # Inicializējam tames datus sesijā
    if 'tame_list' not in st.session_state:
        st.session_state.tame_list = pd.DataFrame(columns=['Materials', 'Daudzums', 'Cena'])

    # Ievades zona
    st.subheader("Pievienot pozīciju no kataloga")
    with st.expander("Atvērt materiālu izvēlni", expanded=True):
        col_m, col_d = st.columns([3, 1])
        izveletais_mat = col_m.selectbox("Izvēlieties materiālu:", list(KATALOGS.keys()))
        daudzums = col_d.number_input("Daudzums:", min_value=0.0, step=1.0, value=1.0)
        
        pasreizeja_cena = KATALOGS[izveletais_mat]
        st.write(f"Vienības cena: *{pasreizeja_cena:.2f} EUR*")
        
        if st.button("Pievienot tāmei"):
            jauna_rinda = pd.DataFrame({
                'Materials': [izveletais_mat], 
                'Daudzums': [daudzums], 
                'Cena': [pasreizeja_cena]
            })
            st.session_state.tame_list = pd.concat([st.session_state.tame_list, jauna_rinda], ignore_index=True)
            st.rerun()

    # Aprēķinu tabula
    df = st.session_state.tame_list
    if not df.empty:
        st.divider()
        st.subheader("Tāmes kopsavilkums")
        
        df_display = df.copy()
        df_display['Summa'] = df_display['Daudzums'] * df_display['Cena']
        
        st.dataframe(df_display, use_container_width=True)
        
        kopa = df_display['Summa'].sum()
        st.metric("KOPĒJĀ SUMMA", f
