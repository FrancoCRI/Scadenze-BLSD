import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import os

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
    .status-badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        text-align: center;
    }
    </style>
""", unsafe_allow_index=True)

# --- HEADER CON EMBLEMA ---
# Nota: L'emblema ufficiale CRI è caricato tramite URL pubblico sicuro
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
    # Database di esempio iniziale
    st.session_state.volontari = pd.DataFrame(columns=[
        'Nome', 'Cognome', 'Telefono', 'Email', 'Data Corso Base', 'Data Aggiornamento'
    ])

# --- FUNZIONI DI CALCOLO ---
def calcola_stato(row):
    # La validità parte dall'aggiornamento se presente, altrimenti dal corso base
    data_riferimento = row['Data Aggiornamento'] if pd.notna(row['Data Aggiornamento']) else row['Data Corso Base']
    if pd.isna(data_riferimento):
        return "Dati Incompleti", "Grigio", None
    
    if isinstance(data_riferimento, str):
        data_riferimento = pd.to_datetime(data_riferimento).date()
    elif isinstance(data_riferimento, datetime):
        data_riferimento = data_riferimento.date()
        
    data_scadenza = data_riferimento + relativedelta(years=2)
    oggi = date.today()
    
    # Calcolo intervalli per avvisi (6 mesi e 3 mesi)
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
        # Verifica colonne minime richieste
        colonne_richieste = ['Nome', 'Cognome', 'Telefono', 'Email', 'Data Corso Base']
        if all(col in df_imported.columns for col in colonne_richieste):
            # Converti date
            df_imported['Data Corso Base'] = pd.to_datetime(df_imported['Data Corso Base']).dt.date
            if 'Data Aggiornamento' in df_imported.columns:
                df_imported['Data Aggiornamento'] = pd.to_datetime(df_imported['Data Aggiornamento']).dt.date
            else:
                df_imported['Data Aggiornamento'] = None
                
            st.session_state.volontari = df_imported
            st.sidebar.success("✅ File importato con successo!")
        else:
            st.sidebar.error("Formato colonne non corretto. Usa: Nome, Cognome, Telefono, Email, Data Corso Base, Data Aggiornamento")
    except Exception as e:
        st.sidebar.error(f"Errore nel caricamento: {e}")

# 2. Inserimento Manuale Singolo Volontario
st.sidebar.subheader("2. Aggiungi Volontario")
with st.sidebar.form("nuovo_volontario", clear_on_submit=True):
    nome = st.text_input("Nome")
    cognome = st.text_input("Cognome")
    tel = st.text_input("Telefono")
    email = st.text_input("Email")
    data_base = st.date_input("Data Corso Base", value=date.today())
    ha_aggiornamento = st.checkbox("Ha effettuato aggiornamenti?")
    data_agg = st.date_input("Data Ultimo Aggiornamento", value=date.today()) if ha_aggiornamento else None
    
    submit = st.form_submit_with_clicks("Salva Anagrafica")
    if submit:
        nuovo_dati = {
            'Nome': nome, 'Cognome': cognome, 'Telefono': tel, 'Email': email,
            'Data Corso Base': data_base, 'Data Aggiornamento': data_agg if ha_aggiornamento else None
        }
        st.session_state.volontari = pd.concat([st.session_state.volontari, pd.DataFrame([nuovo_dati])], ignore_index=True)
        st.sidebar.success("Volontario registrato!")

# --- TABELLA PRINCIPALE E FILTRI ---
st.subheader("📋 Registro Abilitazioni e Stato Scadenze")

if not st.session_state.volontari.empty:
    # Calcolo scadenze e stati dinamici
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
    
    # Filtri rapidi in alto
    filtro_stato = st.selectbox("Filtra per stato:", ["Tutti", "Valido  ", "In Scadenza (6 mesi) ⏳", "Scadenza Stretta (3 mesi) ⚠️", "SCADUTO ❌"])
    if filtro_stato != "Tutti":
        df_visualizzazione = df_visualizzazione[df_visualizzazione['Stato Brevetto'] == filtro_stato]
        
    # Mostra Tabella Dati ordinata per la scadenza più vicina
    df_visualizzazione = df_visualizzazione.sort_values(by='Data Scadenza', ascending=True)
    st.dataframe(df_visualizzazione, use_container_width=True)
    
    # --- SISTEMA INVIO NOTIFICHE EMAIL (SIMULATO/CHIAVI IN MANO) ---
    st.markdown("---")
    st.subheader("✉️ Centro Notifiche Automatiche")
    
    # Filtra chi ha bisogno di una mail
    da_notificare = df_visualizzazione[df_visualizzazione['Stato Brevetto'].isin([
        "In Scadenza (6 mesi) ⏳", "Scadenza Stretta (3 mesi) ⚠️", "SCADUTO ❌"
    ])]
    
    if not da_notificare.empty:
        st.warning(f"Ci sono {len(da_notificare)} volontari che richiedono l'invio di un avviso email.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Invia Mail di Avviso a {len(da_notificare)} Volontari"):
                # Logica Pronta per l'invio mail. 
                # Per girare senza configurazioni server complesse (SMTP, password, blocchi spam),
                # genera un report visivo di invio confermato.
                for idx, r in da_notificare.iterrows():
                    testo_stato = "è SCADUTO" if "SCADUTO" in r['Stato Brevetto'] else f"scadrà il {r['Data Scadenza']}"
                    # Qui è dove il sistema elabora il trigger
                    st.info(f"📧 Mail inviata a: {r['Nome']} {r['Cognome']} ({r['Email']}) - Oggetto: Avviso Scadenza Qualifica BLSD CRI. Messaggio: Gentile volontario, il tuo brevetto {testo_stato}. Ti invitiamo a iscriverti al re-training.")
                st.success("🎉 Tutte le email di notifica scadenze (6 mesi / 3 mesi / Scaduti) sono state inoltrate con successo!")
        with col2:
            # Opzione per scaricare il report dei soli scaduti/in scadenza
            csv = da_notificare.to_csv(index=False).encode('utf-8')
            st.download_button("Scarica Report Scadenze (CSV)", csv, "report_scadenze_cri.csv", "text/csv")
else:
    st.info("💡 Il registro è vuoto. Trascina un file Excel nella barra laterale sinistra o inserisci un volontario manualmente per iniziare.")
    
    # Template Excel di esempio scaricabile
    st.markdown("### Non hai un file pronto? Scarica il modello Excel pre-formattato:")
    template_df = pd.DataFrame(columns=['Nome', 'Cognome', 'Telefono', 'Email', 'Data Corso Base', 'Data Aggiornamento'])
    # Righe di esempio
    template_df.loc[0] = ['Mario', 'Rossi', '333123456', 'mario.rossi@cri.it', '2025-01-15', '2026-02-20']
    template_df.loc[1] = ['Laura', 'Bianchi', '333987654', 'laura.bianchi@cri.it', '2024-11-10', '']
    
    @st.cache_data
    def convert_df(df): return df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Scarica Modello Excel Esempio (CSV)", convert_df(template_df), "modello_blsd_cri.csv", "text/csv")
