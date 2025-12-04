import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import argparse
import re
import sys
import os

# ==============================================================================
#   KONFIGURASJON AV ARGUMENTER
# ==============================================================================

ARG_FILES   = 'files'    # Flagg: --files
ARG_FORMULA = 'formula'   # Flagg: --formel
ARG_CLEAN   = 'clean'    # Flagg: --rens (Endret fra zscore for å matche ønsket ditt)
ARG_TITLE   = 'tittel'   # Flagg: --tittel

# Standardverdi for Z-score hvis man bare skriver --clean uten tall
DEFAULT_Z_SCORE = 3.0 

# ==============================================================================
#   HJELPETEKSTER
# ==============================================================================

BESKRIVELSE = """
Verktøy for å plotte og beregne sensordata fra Excel-filer (.xlsx).

Scriptet lar deg:
 1. Laste inn flere filer og gi dem korte kallenavn (alias).
 2. Synkronisere dem på tid (automatisk merge).
 3. Kjøre matematiske formler på tvers av filene.
 4. Automatisk fjerne støy (outliers) med statistikk (Z-score).
"""

EKSEMPLER = f"""
EKSEMPLER PÅ BRUK:
------------------
1. Enkel korrigering av vannstand mot barometer:
   python plot_dyn.py --{ARG_FILES} Baro=Baro.xlsx Vann=Laksemyra.xlsx --{ARG_FORMULA} "Vann.ch1 - Baro.ch1"

2. Med konvertering (hvis Baro er kPa og Vann er meter):
   python plot_dyn.py --{ARG_FILES} B=Baro.xlsx V=Vann.xlsx --{ARG_FORMULA} "V.ch1 - (B.ch1 / 9.81)" --{ARG_TITLE} "Korrigert Vannstand"

3. Fjerne støy (Enkelt):
   Bruk --{ARG_CLEAN} for å fjerne ekstreme verdier (Standard: {DEFAULT_Z_SCORE} standardavvik).
   python plot_dyn.py --{ARG_FILES} Data=Fil.xlsx --{ARG_FORMULA} "Data.ch1" --{ARG_CLEAN}

4. Fjerne støy (Avansert):
   Du kan også angi et tall selv (f.eks 4.0 for mildere vasking).
   python plot_dyn.py --{ARG_FILES} Data=Fil.xlsx --{ARG_FORMULA} "Data.ch1" --{ARG_CLEAN} 5.0
"""

# ==============================================================================

def parse_files_arg(file_args):
    """Parser input: ['Alias=Path', ...] -> {'Alias': 'Path'}"""
    files_dict = {}
    for item in file_args:
        if "=" not in item:
            print(f"FEIL: Ugyldig format på fil-argumentet '{item}'. Bruk Alias=Filnavn.xlsx")
            sys.exit(1)
        alias, path = item.split("=", 1)
        files_dict[alias.strip()] = path.strip()
    return files_dict

def last_og_rens_data(filsti, alias):
    if not os.path.exists(filsti):
        print(f"FEIL: Finner ikke filen '{filsti}'.")
        sys.exit(1)

    try:
        # Laster data
        df = pd.read_excel(filsti, engine='openpyxl')
    except Exception as e:
        print(f"Kunne ikke lese {filsti}: {e}")
        sys.exit(1)
    
    # Rens kolonnenavn (fjerner mellomrom)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Sjekk etter tidskolonner
    required_time = ['Date5', 'Time6']
    if not all(col in df.columns for col in required_time):
        print(f"FEIL: {filsti} mangler tidskolonner {required_time}")
        sys.exit(1)

    # Finn datakolonnen (ch1)
    data_col = 'ch1'
    if data_col not in df.columns:
         print(f"FEIL: Fant ikke kolonnen '{data_col}' i {filsti}. Tilgjengelige: {df.columns.tolist()}")
         sys.exit(1)

    # Kombiner dato og tid
    try:
        df['Datetime'] = pd.to_datetime(df['Date5'].astype(str) + ' ' + df['Time6'].astype(str))
    except Exception as e:
        print(f"Feil datoformat i {alias}: {e}")
        sys.exit(1)
    
    df = df.sort_values('Datetime')
    df_clean = df[['Datetime', data_col]].copy()
    
    # Rename til Alias.ch1
    df_clean.columns = ['Datetime', f'{alias}.{data_col}']
    
    return df_clean

def vask_data(df, kolonne, z_score):
    """Fjerner data som er statistiske utliggere (outliers)."""
    data = df[kolonne]
    mean = data.mean()
    std = data.std()
    
    if std == 0: return df
    
    nedre = mean - (z_score * std)
    ovre = mean + (z_score * std)
    
    df_vasket = df[(data >= nedre) & (data <= ovre)].copy()
    fjernet = len(df) - len(df_vasket)
    
    if fjernet > 0:
        print(f"--- RENSING (Z-score: {z_score}) ---")
        print(f"Fjernet {fjernet} punkter (støy).")
        print(f"Beholder verdier mellom {nedre:.2f} og {ovre:.2f}")
        print(f"----------------------------------\n")
    else:
        print(f"--- RENSING (Z-score: {z_score}) ---")
        print("Ingen verdier funnet utenfor normalen.")
        print("----------------------------------\n")
    
    return df_vasket

def main():
    parser = argparse.ArgumentParser(
        description=BESKRIVELSE,
        epilog=EKSEMPLER,
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # -- FILES --
    parser.add_argument(f'--{ARG_FILES}', dest='input_files', nargs='+', required=True, 
                        help='Liste over filer. Format: Alias=Filnavn.xlsx')
    
    # -- FORMEL --
    parser.add_argument(f'--{ARG_FORMULA}', dest='calc_formula', type=str, required=True, 
                        help='Matematisk formel. F.eks "A.ch1 - B.ch1"')
    
    # -- CLEAN / RENS --
    # Her bruker vi nargs='?' og const.
    # Hvis flagget ikke er med: clean_threshold = None
    # Hvis flagget er med (uten tall): clean_threshold = DEFAULT_Z_SCORE (3.0)
    # Hvis flagget er med (med tall): clean_threshold = tallet brukeren skrev
    parser.add_argument(f'--{ARG_CLEAN}', dest='clean_threshold', 
                        nargs='?', const=DEFAULT_Z_SCORE, type=float, default=None,
                        help=f'Fjern støy. Standardverdi: {DEFAULT_Z_SCORE} (hvis ingen verdi angis).')
    
    # -- TITTEL --
    parser.add_argument(f'--{ARG_TITLE}', dest='plot_title', type=str, default="Sensor Plot", 
                        help='Tittel på plottet')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    files_dict = parse_files_arg(args.input_files)
    
    print(f"--- Starter prosessering ---")
    
    # 1. Last Data
    dfs = []
    for alias, filsti in files_dict.items():
        print(f"Laster {alias} ({filsti})...")
        dfs.append(last_og_rens_data(filsti, alias))
    
    if not dfs: return

    # 2. Merge Data
    base_df = dfs[0]
    for other_df in dfs[1:]:
        base_df = pd.merge_asof(
            base_df, 
            other_df, 
            on='Datetime', 
            direction='nearest', 
            tolerance=pd.Timedelta('10min')
        )
    
    # 3. Beregn Formel
    pattern = r'\b([a-zA-Z0-9_æøåÆØÅ]+\.ch1)\b'
    safe_formel = re.sub(pattern, r'`\1`', args.calc_formula)
    
    print(f"Beregner: {args.calc_formula}")
    try:
        base_df['Resultat'] = base_df.eval(safe_formel)
    except Exception as e:
        print(f"\n!!! FEIL I FORMEL !!!")
        print(f"Melding: {e}")
        available = [c for c in base_df.columns if '.ch1' in c]
        print(f"Tilgjengelige kolonner: {available}")
        sys.exit(1)

    # 4. Rens Data (hvis clean_threshold er satt)
    if args.clean_threshold is not None:
        base_df = vask_data(base_df, 'Resultat', z_score=args.clean_threshold)

    if base_df.empty:
        print("Ingen data igjen å plotte.")
        return

    # 5. Plotting
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(base_df['Datetime'], base_df['Resultat'], label='Beregnet verdi', color='#1f77b4', linewidth=1)
    
    ax.set_title(f"{args.plot_title}\n({args.calc_formula})", fontsize=14)
    ax.set_ylabel("Verdi", fontsize=12)
    
    # --- X-AKSE FORMATERING ---
    # Ukesmerker
    locator = mdates.WeekdayLocator(interval=1, byweekday=mdates.MO)
    ax.xaxis.set_major_locator(locator)
    
    # OPPDATERT: Datoformat med årstall (Dag.Måned.År)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
    
    plt.xticks(rotation=45)
    ax.autoscale(enable=True, axis='y', tight=False)
    ax.grid(True, which='major', linestyle='-', alpha=0.8)
    ax.minorticks_on()
    ax.grid(True, which='minor', linestyle=':', alpha=0.4)
    
    ax.legend()
    plt.tight_layout()
    print("Viser plot...")
    plt.show()

if __name__ == "__main__":
    main()