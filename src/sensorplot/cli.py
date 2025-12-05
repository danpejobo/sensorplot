import argparse
import sys
import re
import pandas as pd
from sensorplot.core import last_og_rens_data, vask_data, plot_resultat

# ==============================================================================
#   KONFIGURASJON
# ==============================================================================

ARG_FILES   = 'files'    
ARG_SERIES  = 'series'   # NYTT FLAGG: --series "Navn=Formel"
ARG_FORMULA = 'formel'   # (Beholdes for bakoverkompatibilitet)
ARG_CLEAN   = 'clean'    
ARG_TITLE   = 'tittel'   
ARG_OUTPUT  = 'output'   

ARG_COL_DATE = 'datecol'
ARG_COL_TIME = 'timecol'
ARG_COL_DATA = 'datacol'

DEFAULT_Z_SCORE = 3.0 
DEF_DATE = 'Date5'
DEF_TIME = 'Time6'
DEF_DATA = 'ch1'

# ==============================================================================
#   HJELPETEKSTER
# ==============================================================================

BESKRIVELSE = """
Verktøy for å plotte og beregne sensordata fra Excel-filer (.xlsx).
Støtter nå plotting av FLERE serier i samme graf.
"""

EKSEMPLER = f"""
EKSEMPLER PÅ BRUK:
------------------
1. ENKEL SERIE (Gammel metode):
   sensorplot --{ARG_FILES} B=Baro.xlsx V=Vann.xlsx --{ARG_FORMULA} "V.ch1 - B.ch1"

2. FLERE SERIER (Ny metode):
   Her plotter vi to steder (L1 og L2) korrigert mot samme barometer (B).
   
   sensorplot --{ARG_FILES} L1=Laksemyra1.xlsx L2=Laksemyra2.xlsx B=Baro.xlsx \\
              --{ARG_SERIES} "Laksemyra 1=L1.ch1 - B.ch1" "Laksemyra 2=L2.ch1 - B.ch1"

3. AVANSERT:
   sensorplot --{ARG_FILES} A=FilA.xlsx B=FilB.xlsx C=FilC.xlsx \\
              --{ARG_SERIES} "A rådata=A.ch1" "A korrigert=A.ch1 - B.ch1" "C vs B=C.ch1 - B.ch1" \\
              --{ARG_CLEAN}
"""

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

def extract_aliases_from_formula(formula):
    """Finner alle aliaser i en formel (f.eks 'L1' fra 'L1.ch1 - B.ch1')."""
    # Leter etter mønsteret "Navn.ch1"
    pattern = r'\b([a-zA-Z0-9_æøåÆØÅ]+)\.ch1\b'
    return re.findall(pattern, formula)

def process_single_series(series_label, formula, all_files_dict, loaded_dfs_cache, args, use_time_col):
    """Behandler én enkelt serie (Laster filer, merger, beregner, vasker)."""
    
    print(f"\n--- Behandler serie: '{series_label}' ---")
    
    # 1. Finn hvilke filer som trengs for denne formelen
    needed_aliases = extract_aliases_from_formula(formula)
    if not needed_aliases:
        print(f"FEIL: Fant ingen aliaser (f.eks 'Navn.ch1') i formelen: {formula}")
        sys.exit(1)
    
    # 2. Sørg for at filene er lastet (bruk cache)
    current_dfs = []
    
    # VIKTIG: Første alias i formelen blir "Tidsbasen" (Master timeline)
    # F.eks i "L1.ch1 - B.ch1" er L1 master.
    base_alias = needed_aliases[0] 
    
    # Last base-filen først
    if base_alias not in loaded_dfs_cache:
        if base_alias not in all_files_dict:
             print(f"FEIL: Formelen bruker alias '{base_alias}' som ikke er definert i --files.")
             sys.exit(1)
        print(f"Laster {base_alias} (BASE)...")
        loaded_dfs_cache[base_alias] = last_og_rens_data(
            all_files_dict[base_alias], base_alias, args.col_date, use_time_col, args.col_data
        )
    current_dfs.append(loaded_dfs_cache[base_alias])
    
    # Last resten av filene (f.eks Baro)
    for alias in needed_aliases[1:]:
        if alias not in loaded_dfs_cache:
            if alias not in all_files_dict:
                print(f"FEIL: Formelen bruker alias '{alias}' som ikke er definert i --files.")
                sys.exit(1)
            print(f"Laster {alias} (Referanse)...")
            loaded_dfs_cache[alias] = last_og_rens_data(
                all_files_dict[alias], alias, args.col_date, use_time_col, args.col_data
            )
        # Legg til i listen for merging, men sjekk at vi ikke legger til base på nytt
        if alias != base_alias: 
            current_dfs.append(loaded_dfs_cache[alias])

    # 3. Merge dataene (Slå sammen til tidsbasen til første fil)
    merged_df = current_dfs[0] # Start med base
    for other_df in current_dfs[1:]:
        merged_df = pd.merge_asof(
            merged_df, 
            other_df, 
            on='Datetime', 
            direction='nearest', 
            tolerance=pd.Timedelta('10min')
        )

    # 4. Beregn Formel
    safe_formel = re.sub(r'\b([a-zA-Z0-9_æøåÆØÅ]+\.ch1)\b', r'`\1`', formula)
    print(f"Beregner: {formula}")
    
    try:
        merged_df['Resultat'] = merged_df.eval(safe_formel)
    except Exception as e:
        print(f"FEIL i formelberegning: {e}")
        available = [c for c in merged_df.columns if '.ch1' in c]
        print(f"Tilgjengelige variabler i denne serien: {available}")
        sys.exit(1)

    # 5. Vask Data
    if args.clean_threshold is not None:
        merged_df, antall = vask_data(merged_df, 'Resultat', z_score=args.clean_threshold)
        if antall > 0:
            print(f"  -> Renset {antall} støy-punkter.")

    if merged_df.empty:
        print("  -> ADVARSEL: Ingen data igjen etter prosessering.")
        return None

    return {
        'df': merged_df,
        'label': series_label
    }


def main():
    parser = argparse.ArgumentParser(
        description=BESKRIVELSE,
        epilog=EKSEMPLER,
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(f'--{ARG_FILES}', dest='input_files', nargs='+', required=True, 
                        help='Liste over filer. Format: Alias=Filnavn.xlsx')
    
    # -- SERIER (NY) --
    parser.add_argument(f'--{ARG_SERIES}', dest='series_list', nargs='+', 
                        help='Liste over serier. Format: "Navn=Formel".')

    # -- FORMEL (GAMMEL) --
    parser.add_argument(f'--{ARG_FORMULA}', dest='calc_formula', type=str, 
                        help='(Legacy) Enkel formel. Brukes hvis --series ikke er angitt.')
    
    parser.add_argument(f'--{ARG_CLEAN}', dest='clean_threshold', 
                        nargs='?', const=DEFAULT_Z_SCORE, type=float, default=None,
                        help=f'Fjern støy (Z-score). Standard: {DEFAULT_Z_SCORE}.')
    
    parser.add_argument(f'--{ARG_TITLE}', dest='plot_title', type=str, default="Sensor Plot", 
                        help='Tittel på plottet')

    parser.add_argument(f'--{ARG_COL_DATE}', dest='col_date', type=str, default=DEF_DATE, help=f'Standard: {DEF_DATE}')
    parser.add_argument(f'--{ARG_COL_TIME}', dest='col_time', type=str, default=DEF_TIME, help=f'Standard: {DEF_TIME}')
    parser.add_argument(f'--{ARG_COL_DATA}', dest='col_data', type=str, default=DEF_DATA, help=f'Standard: {DEF_DATA}')
    
    parser.add_argument(f'--{ARG_OUTPUT}', dest='output_file', 
                        nargs='?', const='sensorplot.png', default=None, type=str,
                        help='Lagre plott. Utelatt: Vis GUI.')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    
    # Validering: Må ha enten --series eller --formel
    if not args.series_list and not args.calc_formula:
        print("FEIL: Du må angi enten --series (for flere linjer) eller --formel (for én linje).")
        sys.exit(1)

    files_dict = parse_files_arg(args.input_files)
    
    use_time_col = args.col_time
    if use_time_col and use_time_col.lower() == "none":
        use_time_col = None

    # Bygg liste over hva som skal plottes
    # Format: [ ('Navn', 'Formel'), ... ]
    plot_definitions = []
    
    if args.series_list:
        # Parser "Navn=Formel"
        for s in args.series_list:
            if "=" not in s:
                print(f"FEIL: Serie må ha format 'Navn=Formel'. Fikk: '{s}'")
                sys.exit(1)
            label, formula = s.split("=", 1)
            plot_definitions.append((label.strip(), formula.strip()))
    else:
        # Bruker legacy --formel
        plot_definitions.append(("Resultat", args.calc_formula))

    print(f"--- Starter prosessering ---")
    
    # Cache for innlastede dataframes så vi slipper å lese Baro.xlsx 5 ganger
    loaded_dfs_cache = {} 
    
    final_results = []
    
    for label, formula in plot_definitions:
        res = process_single_series(label, formula, files_dict, loaded_dfs_cache, args, use_time_col)
        if res:
            final_results.append(res)
    
    if not final_results:
        print("Ingen data å plotte.")
        return

    print("\nGenererer plott...")
    # Plotter alle seriene i samme figur
    plot_resultat(final_results, args.plot_title, output_file=args.output_file)

if __name__ == "__main__":
    main()