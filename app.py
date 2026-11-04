import streamlit as st
import pandas as pd
from datetime import datetime, date

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Gestione Scadenze BLSD - Croce Rossa",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- HEADER CON EMBLEMA ---
logo_url = "https://wikimedia.org"

col_logo, col_titolo = st.columns()
with col_logo:
    st.image(logo_url, width=90)
with col_titolo:
    st.title("Croce Rossa Italiana")
    st.subheader("Piattaforma Monitoraggio Scadenze Abilitazioni Defibrillatore (BLSD)")

st.markdown("---")

# --- INIZIALIZZAZIONE DATABASE IN MEMORIA ---
if 'volontari' not in st.session_state:
    st.session_state.volontari = pd.DataFrame(columns=[
        'Nome', 'Cognome', 'Telefono', 'Email', 'Data Corso Base', 'Data Aggiornamento'
    ])

# --- FUNZIONI DI CALCOLO E CONVERSIONE ---
def calcola_scadenza_e_stato(row):
    data_ref = row['Data Aggiornamento'] if pd.notna(row['Data Aggiornamento']) and row['Data Aggiornamento'] != '' else row['Data Corso Base']
    if pd.isna(data_ref) or data_ref == '':
        return "Dati Incompleti", None
    
    if isinstance(data_ref, str):
        try:
            dt = datetime.strptime(data_ref, "%d/%m/%Y").date()
        except:
            try:
                dt = datetime.strptime(data_ref, "%Y-%m-%d").date()
            except:
                try:
                    dt = pd.to_datetime(data_ref).date()
                except:
                    return "Errore Formato Data", None
    elif isinstance(data_ref, datetime) or isinstance(data_ref, date):
        dt = pd.to_datetime(data_ref).date()
    else:
        dt = data_ref

    try:
        data_scadenza = dt.replace(year=dt.year + 2)
    except ValueError:
        data_scadenza = dt + pd.Timedelta(days=730)
        
    oggi = date.today()
    giorni_mancanti = (data_scadenza - oggi).days
    
    if giorni_mancanti < 0:
        return "SCADUTO ❌", data_scadenza
    elif giorni_mancanti <= 90:
        return "Scadenza Stretta (3 mesi) ⚠️", data_scadenza
    elif giorni_mancanti <= 180:
        return "In Scadenza (6 mesi) ⏳", data_scadenza
    else:
        return "Valido ✅", data_scadenza

# --- SIDEBAR: FUNZIONALITÀ ---
st.sidebar.header("⚙️ Pannello Azioni")

st.sidebar.subheader("1. Importa da Excel")
uploaded_file = st.sidebar.file_uploader("Carica file .xlsx", type=["xlsx"])

if uploaded_file is not None:
    try:
        df_imported = pd.read_excel(uploaded_file)
        colonne_richieste = ['Nome', 'Cognome', 'Telefono', 'Email', 'Data Corso Base']
        if all(col in df_imported.columns for col in colonne_richieste):
            st.session_state.volontari = df_imported
            st.sidebar.success("✅ File importato!")
        else:
            st.sidebar.error("Colonne richieste: Nome, Cognome, Telefono, Email, Data Corso Base")
    except Exception as e:
        st.sidebar.error(f"Errore: {e}")

st.sidebar.subheader("2. Aggiungi Volontario")
with st.sidebar.form("nuovo_volontario", clear_on_submit=True):
    nome = st.text_input("Nome")
    cognome = st.text_input("Cognome")
    tel = st.text_input("Telefono")
    email = st.text_input("Email")
    data_base = st.date_input("Data Corso Base", value=date.today(), format="DD/MM/YYYY")
    ha_aggiornamento = st.checkbox("Ha effettuato aggiornamenti?")
    data_agg = st.date_input("Data Ultimo Aggiornamento", value=date.today(), format="DD/MM/YYYY") if ha_aggiornamento else None
    
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
    scadenze = []
    
    for idx, row in st.session_state.volontari.iterrows():
        stato, scadenza = calcola_scadenza_e_stato(row)
        stati.append(stato)
        scadenze.append(scadenza)
        
    df_visualizzazione = st.session_state.volontari.copy()
    df_visualizzazione['Data Scadenza'] = scadenze
    df_visualizzazione['Stato Brevetto'] = stati
    
    filtro_stato = st.selectbox("Filtra per stato:", ["Tutti", "Valido ✅", "In Scadenza (6 mesi) ⏳", "Scadenza Stretta (3 mesi) ⚠️", "SCADUTO ❌"])
    if filtro_stato != "Tutti":
        df_visualizzazione = df_visualizzazione[df_visualizzazione['Stato Brevetto'] == filtro_stato]
        
    df_visualizzazione = df_visualizzazione.sort_values(by='Data Scadenza', ascending=True, na_position='last')
    
    for col in ['Data Corso Base', 'Data Aggiornamento', 'Data Scadenza']:
        if col in df_visualizzazione.columns:
            df_visualizzazione[col] = pd.to_datetime(df_visualizzazione[col], errors='coerce').dt.strftime('%d/%m/%Y').fillna('')

    st.dataframe(df_visualizzazione, use_container_width=True)
    
    # --- SISTEMA INVIO NOTIFICHE EMAIL ---
    st.markdown("---")
    st.subheader("✉️ Centro Notifiche Automatiche")
    
    da_notificare = df_visualizzazione[df_visualizzazione['Stato Brevetto'].isin([
        "In Scadenza (6 mesi) ⏳", "Scadenza Stretta (3 mesi) ⚠️", "SCADUTO ❌"
    ])]
    
    if not da_notificare.empty:
        st.warning(f"Ci sono {len(da_notificare)} avvisi da inviare.")
        if st.button(f"Invia Mail di Avviso a {len(da_notificare)} Volontari"):
            for idx, r in da_notificare.iterrows():
                testo_stato = "è SCADUTO" if "SCADUTO" in r['Stato Brevetto'] else f"scadrà il {r['Data Scadenza']}"
                st.info(f"📧 Mail inviata a: {r['Nome']} {r['Cognome']} ({r['Email']}) - Scadenza: {r['Data Scadenza']}")
            st.success("🎉 Email inviate con successo!")
else:
    st.info("💡 Il registro è vuoto. Carica un file Excel a sinistra o inserisci un volontario per partire.")
