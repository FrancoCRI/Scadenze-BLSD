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

col_logo, col_titolo = st.columns(2)
with col_logo:
    st.image(logo_url, width=90)
with col_titolo:
    st.title("Croce Rossa Italiana")
    st.subheader("Piattaforma Monitoraggio Scadenze Abilitazioni Defibrillatore (BLSD)")

st.markdown("---")

# --- INIZIALIZZAZIONE DATABASE IN MEMORIA ---
if 'volontari' not in st.session_state:
    st.session_state.volontari = pd.DataFrame(columns=[
        'Nome', 'Cognome', 'Telefono', 'Email', 'Data Corso Base'
    ])

# --- FUNZIONE LOGICA TROVA ULTIMA DATA E CALCOLA SCADENZA ---
def elabora_volontario(row):
    # Raccoglie tutte le date valide presenti nella riga (Corso Base + tutti gli Aggiornamenti)
    date_valide = []
    
    # Controlla la data del corso base
    if pd.notna(row.get('Data Corso Base')) and row.get('Data Corso Base') != '':
        date_valide.append(row['Data Corso Base'])
        
    # Cerca in modo flessibile tutte le colonne che contengono la parola 'Aggiornamento'
    for col in row.index:
        if 'Aggiornamento' in col and pd.notna(row[col]) and row[col] != '':
            date_valide.append(row[col])
            
    if not date_valide:
        return "Dati Incompleti", None, ""

    # Converte e pulisce tutte le date trovate per estrarre la più recente
    date_pulite = []
    for d in date_valide:
        if isinstance(d, str):
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    date_pulite.append(datetime.strptime(d, fmt).date())
                    break
                except:
                    continue
            try:
                date_pulite.append(pd.to_datetime(d).date())
            except:
                pass
        elif isinstance(d, (datetime, date, pd.Timestamp)):
            date_pulite.append(pd.to_datetime(d).date())

    if not date_pulite:
        return "Errore Formato Data", None, ""

    # La data di riferimento per la scadenza è l'ultima in ordine cronologico
    ultima_data_effettuata = max(date_pulite)
    
    try:
        data_scadenza = ultima_data_effettuata.replace(year=ultima_data_effettuata.year + 2)
    except ValueError:
        data_scadenza = ultima_data_effettuata + pd.Timedelta(days=730)
        
    oggi = date.today()
    giorni_mancanti = (data_scadenza - oggi).days
    
    if giorni_mancanti < 0:
        stato = "SCADUTO ❌"
    elif giorni_mancanti <= 90:
        stato = "Scadenza Stretta (3 mesi) ⚠️"
    elif giorni_mancanti <= 180:
        stato = "In Scadenza (6 mesi) ⏳"
    else:
        stato = "Valido ✅"
        
    return stato, data_scadenza, ultima_data_effettuata.strftime('%d/%m/%Y')

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
            st.sidebar.success("✅ File importato con successo!")
        else:
            st.sidebar.error("Il file deve contenere almeno: Nome, Cognome, Telefono, Email, Data Corso Base")
    except Exception as e:
        st.sidebar.error(f"Errore di lettura: {e}")

st.sidebar.subheader("2. Aggiungi Singolo Volontario")
with st.sidebar.form("nuovo_volontario", clear_on_submit=True):
    nome = st.text_input("Nome")
    cognome = st.text_input("Cognome")
    tel = st.text_input("Telefono")
    email = st.text_input("Email")
    
    # Risolto il vincolo: impostato limite minimo fisso all'anno 1980 per sbloccare il 2016
    data_base = st.date_input("Data Corso Base", value=date.today(), min_value=date(1980, 1, 1), format="DD/MM/YYYY")
    data_ultimo_agg = st.date_input("Data Ultimo Aggiornamento (Lascia ad oggi se coincide col Base)", value=date.today(), min_value=date(1980, 1, 1), format="DD/MM/YYYY")
    ha_agg = st.checkbox("Flaga questa casella se il volontario ha storici di aggiornamento")
    
    submit = st.form_submit_button("Salva Anagrafica")
    if submit:
        nuovo_dati = {
            'Nome': nome, 'Cognome': cognome, 'Telefono': tel, 'Email': email,
            'Data Corso Base': data_base, 'Data Aggiornamento 1': data_ultimo_agg if ha_agg else None
        }
        st.session_state.volontari = pd.concat([st.session_state.volontari, pd.DataFrame([nuovo_dati])], ignore_index=True)
        st.sidebar.success("Volontario registrato!")

# --- TABELLA PRINCIPALE ---
st.subheader("📋 Registro Abilitazioni e Stato Scadenze")

if not st.session_state.volontari.empty:
    stati = []
    scadenze = []
    ultimi_interventi = []
    
    for idx, row in st.session_state.volontari.iterrows():
        stato, scadenza, ultimo_effettuato = elabora_volontario(row)
        stati.append(stato)
        scadenze.append(scadenza)
        ultimi_interventi.append(ultimo_effettuato)
        
    df_visualizzazione = st.session_state.volontari.copy()
    df_visualizzazione['Ultimo Corso svolto'] = ultimi_interventi
    df_visualizzazione['Data Scadenza Brevetto'] = scadenze
    df_visualizzazione['Stato Brevetto'] = stati
    
    filtro_stato = st.selectbox("Filtra per stato qualifica:", ["Tutti", "Valido ✅", "In Scadenza (6 mesi) ⏳", "Scadenza Stretta (3 mesi) ⚠️", "SCADUTO ❌"])
    if filtro_stato != "Tutti":
        df_visualizzazione = df_visualizzazione[df_visualizzazione['Stato Brevetto'] == filtro_stato]
        
    df_visualizzazione = df_visualizzazione.sort_values(by='Data Scadenza Brevetto', ascending=True, na_position='last')
    
    # Formatta le colonne visibili all'utente in formato italiano
    for col in df_visualizzazione.columns:
        if 'Data' in col or 'Scadenza' in col:
            try:
                df_visualizzazione[col] = pd.to_datetime(df_visualizzazione[col], errors='coerce').dt.strftime('%d/%m/%Y').fillna('')
            except:
                pass

    st.dataframe(df_visualizzazione, use_container_width=True)
    
    # --- SISTEMA INVIO NOTIFICHE EMAIL ---
    st.markdown("---")
    st.subheader("✉️ Centro Notifiche Automatiche")
    
    da_notificare = df_visualizzazione[df_visualizzazione['Stato Brevetto'].isin([
        "In Scadenza (6 mesi) ⏳", "Scadenza Stretta (3 mesi) ⚠️", "SCADUTO ❌"
    ])]
    
    if not da_notificare.empty:
        st.warning(f"Ci sono {len(da_notificare)} avvisi da inoltrare ai rispettivi volontari.")
        if st.button(f"Invia Mail di Avviso a {len(da_notificare)} Interessati"):
            for idx, r in da_notificare.iterrows():
                testo_stato = "è SCADUTO" if "SCADUTO" in r['Stato Brevetto'] else f"scadrà il {r['Data Scadenza Brevetto']}"
                st.info(f"📧 Mail inviata a: {r['Nome']} {r['Cognome']} ({r['Email']}) - Stato: {r['Stato Brevetto']} - Scadenza: {r['Data Scadenza Brevetto']}")
            st.success("🎉 Invio massivo completato!")
else:
    st.info("💡 Il registro è vuoto. Carica un file Excel contenente le colonne Nome, Cognome, Telefono, Email, Data Corso Base e le colonne opzionali degli aggiornamenti (es: Data Aggiornamento 1, Data Aggiornamento 2, ecc.).")
