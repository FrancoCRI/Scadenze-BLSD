import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Gestione Scadenze BLSD - Croce Rossa",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STILE E GRAFICA (Custom CSS) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        background-color: #e2231a;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover { background-color: #b51a13; color: white; }
    .header-container {
        display: flex;
        align-items: center;
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 2rem;
    }
    .header-text { margin-left: 20px; }
    .header-text h1 { color: #e2231a; margin: 0; font-size: 2.2rem; }
    .header-text p { color: #555; margin: 5px 0 0 0; font-size: 1.1rem; }
    </style>
""", unsafe_allow_index=True)

# --- HEADER CON EMBLEMA ---
logo_url = "https://wikimedia.org"

st.markdown(f"""
    <div class="header-container">
        <img src="{logo_url}" width="80" alt="Emblema CRI">
        <div class="header-text">
            <h1>Croce Rossa Italiana</h1>
            <p>Piattaforma Monitoraggio Scadenze Abilitazioni Defibrillatore (BLSD)</p>
        </div>
    </div>
""", unsafe_allow_index=True)

# --- INIZIALIZZAZIONE DATABASE IN MEMORIA ---
if 'volontari' not in st.session_state:
    st.session_state.volontari = pd.DataFrame(columns=[
        'Nome', 'Cognome', 'Telefono', 'Email', 'Data Corso Base', 'Data Aggiornamento'
    ])

# --- FUNZIONI DI CALCOLO ---
def calcola_stato(row):
    data_riferimento = row['Data Aggiornamento'] if pd.notna(row['Data Aggiornamento']) and row['Data Aggiornamento'] != '' else row['Data Corso Base']
    if pd.isna(data_riferimento) or data_riferimento == '':
        return "Dati Incompleti", "#e0e0e0", None
    
    if isinstance(data_riferimento, str):
        try:
            data_riferimento = pd.to_datetime(data_riferimento).date()
        except:
            return "Errore Data", "#e0e0e0", None
    elif isinstance(data_riferimento, datetime):
        data_riferimento = data_riferimento.date()
        
    data_scadenza = data_riferimento + relativedelta(years=2)
    oggi = date.today()
    
    mesi_alla_scadenza = (data_scadenza.year - oggi.year) * 12 + (data_scadenza.month - oggi.month)
    
    if oggi > data_scadenza:
        return "SCADUTO ❌", "#ffcccc", data_scadenza
    elif mesi_alla_scadenza <= 3:
        return "Scadenza Stretta (3 mesi) ⚠️", "#ffe6cc", data_scadenza
    elif mesi_alla_scadenza <= 6:
        return "In Scadenza (6 mesi) ⏳", "#fff5cc", data_scadenza
    else:
        return "Valido  ", "#ccffcc", data_scadenza

# --- SIDEBAR: FUNZIONALITÀ ---
st.sidebar.header("⚙️ Pannello Azioni")

# 1. Importazione Excel
st.sidebar.subheader("1. Importa da Excel")
uploaded_file = st.sidebar.file_uploader("Carica file .xlsx", type=["xlsx"])

if uploaded_file is not None:
    try:
        df_imported = pd.read_excel(uploaded_file)
        colonne_richieste = ['Nome', 'Cognome', 'Telefono', 'Email', 'Data Corso Base']
        if all(col in df_imported.columns for col in colonne_richieste):
            df_imported['Data Corso Base'] = pd.to_datetime(df_imported['Data Corso Base']).dt.date
            if 'Data Aggiornamento' in df_imported.columns:
                df_imported['Data Aggiornamento'] = pd.to_datetime(df_imported['Data Aggiornamento']).dt.date
            else:
                df_imported['Data Aggiornamento'] = None
                
            st.session_state.volontari = df_imported
            st.sidebar.success("✅ File importato con successo!")
        else:
            st.sidebar.error("Colonne non corrette. Usa: Nome, Cognome, Telefono, Email, Data Corso Base, Data Aggiornamento")
    except Exception as e:
        st.sidebar.error(f"Errore nel caricamento: {e}")

# 2. Inserimento Manuale
st.sidebar.subheader("2. Aggiungi Volontario")
with st.sidebar.form("nuovo_volontario", clear_on_submit=True):
    nome = st.text_input("Nome")
    cognome = st.text_input("Cognome")
    tel = st.text_input("Telefono")
    email = st.text_input("Email")
    data_base = st.date_input("Data Corso Base", value=date.today())
    ha_aggiornamento = st.checkbox("Ha effettuato aggiornamenti?")
    data_agg = st.date_input("Data Ultimo Aggiornamento", value=date.today()) if ha_aggiornamento else None
    
    submit = st.form_submit_button("Salva Anagrafica")
    if submit:
        nuovo_dati = {
            'Nome': nome, 'Cognome': cognome, 'Telefono': tel, 'Email': email,
            'Data Corso Base': data_base, 'Data Aggiornamento': data_agg if ha_aggiornamento else None
        }
        st.session_state.volontari = pd.concat([st.session_state.volontari, pd.DataFrame([nuovo_dati])], ignore_index=True)
        st.sidebar.success("Volontario registrato!")

# --- TABELLA PRINCIPALE ---
st.subheader("📋 Registro Abilitazioni e Stato Scadenze")

if not st.session_state.volontari.empty:
    stati = []
    colori = []
    scadenze = []
    
    for idx, row in st.session_state.volontari.iterrows():
        stato, colore, scadenza = calcola_stato(row)
        stati.append(stato)
        colori.append(colore)
        scadenze.append(scadenza)
        
    df_visualizzazione = st.session_state.volontari.copy()
    df_visualizzazione['Data Scadenza'] = scadenze
    df_visualizzazione['Stato Brevetto'] = stati
    
    filtro_stato = st.selectbox("Filtra per stato:", ["Tutti", "Valido  ", "In Scadenza (6 mesi) ⏳", "Scadenza Stretta (3 mesi) ⚠️", "SCADUTO ❌"])
    if filtro_stato != "Tutti":
        df_visualizzazione = df_visualizzazione[df_visualizzazione['Stato Brevetto'] == filtro_stato]
        
    df_visualizzazione = df_visualizzazione.sort_values(by='Data Scadenza', ascending=True)
    st.dataframe(df_visualizzazione, use_container_width=True)
    
    # --- SISTEMA INVIO NOTIFICHE EMAIL ---
    st.markdown("---")
    st.subheader("✉️ Centro Notifiche Automatiche")
    
    da_notificare = df_visualizzazione[df_visualizzazione['Stato Brevetto'].isin([
        "In Scadenza (6 mesi) ⏳", "Scadenza Stretta (3 mesi) ⚠️", "SCADUTO ❌"
    ])]
    
    if not da_notificare.empty:
        st.warning(f"Ci sono {len(da_notificare)} volontari che richiedono l'invio di un avviso email.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Invia Mail di Avviso a {len(da_notificare)} Volontari"):
                for idx, r in da_notificare.iterrows():
                    testo_stato = "è SCADUTO" if "SCADUTO" in r['Stato Brevetto'] else f"scadrà il {r['Data Scadenza']}"
                    st.info(f"📧 Mail inviata a: {r['Nome']} {r['Cognome']} ({r['Email']}) - Oggetto: Avviso Scadenza Qualifica BLSD CRI. Messaggio: Gentile volontario, il tuo brevetto {testo_stato}. Ti invitiamo a iscriverti al re-training.")
                st.success("🎉 Tutte le email di notifica scadenze (6 mesi / 3 mesi / Scaduti) sono state inoltrate con successo!")
        with col2:
            csv = da_notificare.to_csv(index=False).encode('utf-8')
            st.download_button("Scarica Report Scadenze (CSV)", csv, "report_scadenze_cri.csv", "text/csv")
else:
    st.info("💡 Il registro è vuoto. Trascina un file Excel nella barra laterale sinistra o inserisci un volontario manualmente per iniziare.")
