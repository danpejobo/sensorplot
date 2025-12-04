import argparse
import sys
import re
import pandas as pd
from sensorplot.core import last_og_rens_data, vask_data, plot_resultat

# ==============================================================================
#   KONFIGURASJON AV ARGUMENTER
# ==============================================================================

ARG_FILES   = 'files'    # Flagg: --files
ARG_FORMULA = 'formel'   # Flagg: --formel
ARG_CLEAN   = 'clean'    # Flagg: --clean
ARG_TITLE   = 'tittel'   # Flagg: --tittel

# Nye flagg for kolonnenavn
ARG_COL_DATE = 'datecol'
ARG_COL_TIME = 'timecol'
ARG_COL_DATA = 'datacol'

DEFAULT_Z_SCORE = 3.0 

# Standardverdier (Dine filer)
DEF_DATE = 'Date5'
DEF_TIME = 'Time6'
DEF_DATA = 'ch1'

# ==============================================================================
#   HJELPETEKSTER
# ==============================================================================

BESKRIVELSE = """
Verktøy for å plotte og beregne sensordata fra Excel-filer (.xlsx).

Scriptet lar deg:
 1. Laste inn flere filer og gi dem korte kallenavn (alias).
 2. Synkronisere dem på tid (automatisk merge på nærmeste tidspunkt).
 3. Kjøre matematiske formler på tvers av filene.
 4. Automatisk fjerne støy (outliers) med statistikk (Z-score).
 5. Lese filer med vilkårlige kolonnenavn (via opsjoner).
"""

EKSEMPLER = f"""
EKSEMPLER PÅ BRUK:
------------------
1. Standard bruk (Kolonner: {DEF_DATE}, {DEF_TIME}, {DEF_DATA}):
   Enkel korrigering av vannstand mot barometer.
   sensorplot --{ARG_FILES} B=Baro.xlsx V=Laksemyra.xlsx --{ARG_FORMULA} "V.ch1 - B.ch1"

2. Med konvertering og tittel:
   Hvis barometer (B) er i kPa og Vann (V) i meter.
   sensorplot --{ARG_FILES} B=Baro.xlsx V=Vann.xlsx --{ARG_FORMULA} "V.ch1 - (B.ch1 / 9.81)" --{ARG_TITLE} "Justert nivå"

3. Fjerne støy (Cleaning):
   Bruk --{ARG_CLEAN} for å fjerne ekstreme verdier (Standard: {DEFAULT_Z_SCORE} sigma).
   sensorplot --{ARG_FILES} Data=Fil.xlsx --{ARG_FORMULA} "Data.ch1" --{ARG_CLEAN}

4. Egendefinerte kolonnenavn:
   Hvis filen din har kolonner "Dato", "Klokkeslett" og "Temperatur":
   sensorplot --{ARG_FILES} T=Fil.xlsx --{ARG_FORMULA} "T.ch1" --{ARG_COL_DATE} Dato --{ARG_COL_TIME} Klokkeslett --{ARG_COL_DATA} Temperatur

5. Hvis Dato og Tid er i samme kolonne (f.eks "Timestamp"):
   Sett tidskolonne til "None".
   sensorplot --{ARG_FILES} A=Fil.xlsx --{ARG_FORMULA} "A.ch1" --{ARG_COL_DATE} Timestamp --{ARG_COL_TIME} None
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
                        help='Matematisk formel. NB: Bruk alltid .ch1 i formelen (Alias.ch1) uansett hva kolonnen heter i fila.')
    
    # -- CLEAN / RENS --
    parser.add_argument(f'--{ARG_CLEAN}', dest='clean_threshold', 
                        nargs='?', const=DEFAULT_Z_SCORE, type=float, default=None,
                        help=f'Fjern støy (Z-score). Standardverdi: {DEFAULT_Z_SCORE} (hvis ingen verdi angis).')
    
    # -- TITTEL --
    parser.add_argument(f'--{ARG_TITLE}', dest='plot_title', type=str, default="Sensor Plot", 
                        help='Tittel på plottet')

    # -- KOLONNE KONFIGURASJON --
    parser.add_argument(f'--{ARG_COL_DATE}', dest='col_date', type=str, default=DEF_DATE,
                        help=f'Navn på datokolonne (Standard: {DEF_DATE})')
    
    parser.add_argument(f'--{ARG_COL_TIME}', dest='col_time', type=str, default=DEF_TIME,
                        help=f'Navn på tidskolonne (Standard: {DEF_TIME}). Sett til "None" hvis dato/tid er samlet.')

    parser.add_argument(f'--{ARG_COL_DATA}', dest='col_data', type=str, default=DEF_DATA,
                        help=f'Navn på datokolonne som skal plottes (Standard: {DEF_DATA})')

    # Vis hjelp hvis ingen argumenter
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    files_dict = parse_files_arg(args.input_files)
    
    # Håndter spesialtilfelle hvor bruker skriver "None" i terminalen for tidskolonne
    use_time_col = args.col_time
    if use_time_col.lower() == "none":
        use_time_col = None

    print(f"--- Starter prosessering ---")
    if args.col_data != DEF_DATA:
        print(f"Info: Leser data fra kolonne '{args.col_data}' men mapper den internt til '.ch1' for formelen.")

    dfs = []
    try:
        for alias, filsti in files_dict.items():
            print(f"Laster {alias} ({filsti})...")
            # Her sender vi inn de dynamiske navnene til core-funksjonen
            dfs.append(last_og_rens_data(filsti, alias, args.col_date, use_time_col, args.col_data))
    except Exception as e:
        print(f"FEIL: {e}")
        sys.exit(1)
    
    if not dfs: return

    # Merge Data
    base_df = dfs[0]
    for other_df in dfs[1:]:
        base_df = pd.merge_asof(
            base_df, 
            other_df, 
            on='Datetime', 
            direction='nearest', 
            tolerance=pd.Timedelta('10min')
        )
    
    # Beregn Formel
    # Regex sikrer at Alias.ch1 blir `Alias.ch1` (trygt for pandas)
    pattern = r'\b([a-zA-Z0-9_æøåÆØÅ]+\.ch1)\b'
    safe_formel = re.sub(pattern, r'`\1`', args.calc_formula)
    
    print(f"Beregner: {args.calc_formula}")
    try:
        base_df['Resultat'] = base_df.eval(safe_formel)
    except Exception as e:
        print(f"\n!!! FEIL I FORMEL !!!")
        print(f"Melding: {e}")
        available = [c for c in base_df.columns if '.ch1' in c]
        print(f"Tilgjengelige variabler: {available}")
        sys.exit(1)

    # Rens Data
    if args.clean_threshold is not None:
        base_df, antall = vask_data(base_df, 'Resultat', z_score=args.clean_threshold)
        if antall > 0:
            print(f"--- RENSING ---")
            print(f"Fjernet {antall} punkter (Z-score > {args.clean_threshold}).")

    if base_df.empty:
        print("Ingen data igjen å plotte.")
        return

    plot_resultat(base_df, 'Datetime', 'Resultat', args.plot_title, args.calc_formula)

if __name__ == "__main__":
    main()