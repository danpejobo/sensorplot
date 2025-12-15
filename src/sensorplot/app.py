import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re
from pathlib import Path
import tempfile
import os

# Vi importerer din eksisterende logikk fra core
from sensorplot.core import last_og_rens_data, vask_data

def save_uploaded_file(uploaded_file):
    """Hjelper for å lagre opplastet fil midlertidig slik at core.py kan lese den."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            return tmp.name
    except Exception as e:
        st.error(f"Feil ved lagring av fil: {e}")
        return None

def configure_page() -> None:
    """Konfigurerer siden. Må kun kalles når appen kjøres standalone."""
    st.set_page_config(page_title="Sensorplot GUI", layout="wide")

def run_app() -> None:
    """Kjører selve Sensorplot UI-logikken. Kan trygt importeres av andre apper."""
    st.title("Sensorplot 📈")

    # --- SIDEBAR: KONFIGURASJON ---
    with st.sidebar:
        st.header("1. Innstillinger")
        col_date = st.text_input("Dato-kolonne", value="Date")
        col_time = st.text_input("Tid-kolonne", value="Time")
        col_data = st.text_input("Data-kolonne", value="LEVEL")
        
        st.header("2. Last opp filer")
        uploaded_files = st.file_uploader("Velg Excel/CSV filer", accept_multiple_files=True)
        
        # Mapping mellom Alias og DataFrame
        files_map = {} 
        
        if uploaded_files:
            st.subheader("Gi alias til filer")
            for uf in uploaded_files:
                # La brukeren velge et kort navn (Alias) f.eks "B" eller "L1"
                default_alias = uf.name.split('.')[0].replace(" ", "_")
                alias = st.text_input(f"Alias for {uf.name}", value=default_alias, key=uf.name)
                
                # Lagre filen midlertidig og last inn med din core-logikk
                temp_path = save_uploaded_file(uf)
                if temp_path:
                    try:
                        # Gjenbruker din robuste last_og_rens_data funksjon
                        df = last_og_rens_data(temp_path, alias, col_date, col_time, col_data)
                        files_map[alias] = df
                    except Exception as e:
                        st.error(f"Kunne ikke lese {alias}: {e}")
                    finally:
                        if os.path.exists(temp_path):
                            os.remove(temp_path) # Rydd opp

    # --- HOVEDVINDU: FORMLER OG PLOTT ---
    if files_map:
        st.header("3. Definer Serier")
        
        # Input for formler
        formulas_input = st.text_area(
            "Skriv formler (én per linje). Eks: MinSerie = L1.ch1 - B.ch1", 
            height=150
        )
        
        z_score = st.slider("Støyvask (Z-Score)", 1.0, 5.0, 3.0)
        
        if st.button("Generer Plott"):
            # Bruker matplotlib objekt-orientert stil
            fig, ax = plt.subplots(figsize=(12, 6))
            colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
            
            lines = [line.strip() for line in formulas_input.split('\n') if line.strip()]
            
            plotted_something = False
            for i, line in enumerate(lines):
                if "=" not in line:
                    st.warning(f"Ignorerer ugyldig linje: {line}")
                    continue
                
                label, formula = line.split("=", 1)
                label = label.strip()
                formula = formula.strip()
                
                # Finn aliaser i formelen
                needed_aliases = re.findall(r'\b([a-zA-Z0-9_æøåÆØÅ]+)\.ch1\b', formula)
                
                if not needed_aliases:
                    continue
                
                # Merge logikk
                try:
                    # Start med første dataframe
                    base_alias = needed_aliases[0]
                    if base_alias not in files_map:
                        st.error(f"Finner ikke alias '{base_alias}'")
                        continue

                    merged_df = files_map[base_alias].copy()
                    
                    for other_alias in needed_aliases[1:]:
                        if other_alias not in files_map:
                            st.error(f"Finner ikke alias '{other_alias}'")
                            break
                            
                        merged_df = pd.merge_asof(
                            merged_df, 
                            files_map[other_alias], 
                            on='Datetime', 
                            direction='nearest', 
                            tolerance=pd.Timedelta('10min')
                        )
                    
                    # Beregn
                    safe_formel = re.sub(r'\b([a-zA-Z0-9_æøåÆØÅ]+\.ch1)\b', r'`\1`', formula)
                    merged_df['Resultat'] = merged_df.eval(safe_formel)
                    
                    # Vask
                    merged_df, _ = vask_data(merged_df, 'Resultat', z_score)
                    
                    # Plot
                    ax.plot(merged_df['Datetime'], merged_df['Resultat'], label=label, color=colors[i % len(colors)])
                    plotted_something = True
                    
                except Exception as e:
                    st.error(f"Feil i beregning av '{label}': {e}")

            if plotted_something:
                # Formatering av plott
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
                fig.autofmt_xdate()
                ax.grid(True, alpha=0.3)
                ax.legend()
                ax.set_ylabel("Verdi")
                
                st.pyplot(fig)
            else:
                st.info("Ingen gyldige formler funnet eller data å plotte.")

def main() -> None:
    """Konfigurer siden og kjør appen standalone."""
    configure_page()
    run_app()

if __name__ == "__main__":
    main()