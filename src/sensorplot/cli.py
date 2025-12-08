import argparse
import sys
import re
import pandas as pd
import concurrent.futures
import threading
import logging
from sensorplot.core import SensorResult, last_og_rens_data, vask_data, plot_resultat

# Opprett logger for denne modulen
logger = logging.getLogger(__name__)

# ==============================================================================
#   KONFIGURASJON AV ARGUMENTER
# ==============================================================================

ARG_FILES   = 'files'    
ARG_SERIES  = 'series'   
ARG_FORMULA = 'formel'   
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
Støtter plotting av flere serier, matematiske korreksjoner og automatisk støyfjerning.
"""

EKSEMPLER = f"""
EKSEMPLER PÅ BRUK:
------------------
1. FLERE SERIER:
   sensorplot --{ARG_FILES} L1=Laksemyra1.xlsx L2=Laksemyra2.xlsx B=Baro.xlsx \\
              --{ARG_SERIES} "Laksemyra 1=L1.ch1 - B.ch1" "Laksemyra 2=L2.ch1 - B.ch1"

2. LANG TIDSSERIE (Sammenslåing):
   Hvis du har data for 2024 og 2025 i hver sin fil, men vil ha én linje i plottet:
   Bruk samme navn ("Min Serie") på begge!
   
   sensorplot --{ARG_FILES} D24=Data24.xlsx D25=Data25.xlsx B=Baro.xlsx \\
              --{ARG_SERIES} "Min Serie=D24.ch1 - B.ch1" "Min Serie=D25.ch1 - B.ch1"

3. LAGRE TIL FIL:
   sensorplot --{ARG_FILES} D=Data.xlsx --{ARG_FORMULA} "D.ch1" --{ARG_OUTPUT} plott.png
"""

# ==============================================================================

# Legg til en lås for trådsikker caching
cache_lock = threading.Lock()

def parse_files_arg(file_args):
    """Parser input: ['Alias=Path', ...] -> {'Alias': 'Path'}"""
    files_dict = {}
    for item in file_args:
        if "=" not in item:
            logger.error(f"Ugyldig format på fil-argumentet '{item}'. Bruk Alias=Filnavn.xlsx")
            sys.exit(1)
        alias, path = item.split("=", 1)
        files_dict[alias.strip()] = path.strip()
    return files_dict

def extract_aliases_from_formula(formula):
    """Finner alle aliaser i en formel (f.eks 'L1' fra 'L1.ch1 - B.ch1')."""
    pattern = r'\b([a-zA-Z0-9_æøåÆØÅ]+)\.ch1\b'
    return re.findall(pattern, formula)

def process_single_series(series_label, formula, all_files_dict, loaded_dfs_cache, args, use_time_col):
    """
    Nå kjøres denne funksjonen i en egen tråd!
    """
    logger.info(f"Starter serie: '{series_label}'...")
    
    needed_aliases = extract_aliases_from_formula(formula)
    if not needed_aliases:
        logger.error(f"Fant ingen aliaser (f.eks 'Navn.ch1') i formelen: {formula}")
        return None 
    
    current_dfs = []
    
    # --- TRÅDSIKKER LASTING AV FILER ---
    for alias in needed_aliases:
        if alias not in loaded_dfs_cache:
            with cache_lock:
                if alias not in loaded_dfs_cache: # Dobbeltsjekk
                    if alias not in all_files_dict:
                        logger.error(f"Alias '{alias}' mangler i fil-listen.")
                        return None
                    
                    logger.info(f"  -> Laster fil for {alias}...")
                    try:
                        loaded_dfs_cache[alias] = last_og_rens_data(
                            all_files_dict[alias], alias, args.col_date, use_time_col, args.col_data
                        )
                    except Exception as e:
                        logger.error(f"  -> Feil ved lesing av {alias}: {e}")
                        return None
        
        current_dfs.append(loaded_dfs_cache[alias])

    # --- BEREGNING (CPU) ---
    merged_df = current_dfs[0]
    for other_df in current_dfs[1:]:
        merged_df = pd.merge_asof(
            merged_df, 
            other_df, 
            on='Datetime', 
            direction='nearest', 
            tolerance=pd.Timedelta('10min')
        )

    safe_formel = re.sub(r'\b([a-zA-Z0-9_æøåÆØÅ]+\.ch1)\b', r'`\1`', formula)
    
    try:
        merged_df['Resultat'] = merged_df.eval(safe_formel)
    except Exception as e:
        logger.error(f"  -> Feil i formel '{formula}': {e}")
        return None

    if args.clean_threshold is not None:
        merged_df, antall = vask_data(merged_df, 'Resultat', z_score=args.clean_threshold)
        if antall > 0:
            logger.info(f"  -> {series_label}: Renset {antall} punkter.")

    if merged_df.empty:
        logger.warning(f"  -> {series_label}: Ingen data igjen.")
        return None

    logger.info(f"Ferdig med del-serie: '{series_label}'")
    return SensorResult(label=series_label, df=merged_df)


def main():
    # --- KONFIGURER LOGGING ---
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    parser = argparse.ArgumentParser(
        description=BESKRIVELSE,
        epilog=EKSEMPLER,
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Filer
    parser.add_argument(f'--{ARG_FILES}', dest='input_files', nargs='+', required=True, 
                        help='Liste over filer. Format: Alias=Filnavn.xlsx')
    
    # Serier / Formler
    parser.add_argument(f'--{ARG_SERIES}', dest='series_list', nargs='+', 
                        help='Liste over serier. Format: "Navn=Formel".')

    parser.add_argument(f'--{ARG_FORMULA}', dest='calc_formula', type=str, 
                        help='(Enkel bruk) Formel for én serie. Brukes hvis --series mangler.')
    
    # Valg
    parser.add_argument(f'--{ARG_CLEAN}', dest='clean_threshold', 
                        nargs='?', const=DEFAULT_Z_SCORE, type=float, default=None,
                        help=f'Fjern støy (Z-score). Standard: {DEFAULT_Z_SCORE}.')
    
    parser.add_argument(f'--{ARG_TITLE}', dest='plot_title', type=str, default="Sensor Plot", 
                        help='Tittel på plottet')
    
    parser.add_argument(f'--{ARG_OUTPUT}', dest='output_file', 
                        nargs='?', const='sensorplot.png', default=None, type=str,
                        help='Lagre plott. Utelatt: Vis GUI.')

    # Kolonner
    parser.add_argument(f'--{ARG_COL_DATE}', dest='col_date', type=str, default=DEF_DATE, help=f'Standard: {DEF_DATE}')
    parser.add_argument(f'--{ARG_COL_TIME}', dest='col_time', type=str, default=DEF_TIME, help=f'Standard: {DEF_TIME}')
    parser.add_argument(f'--{ARG_COL_DATA}', dest='col_data', type=str, default=DEF_DATA, help=f'Standard: {DEF_DATA}')
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    
    if not args.series_list and not args.calc_formula:
        logger.error(f"Du må angi enten --{ARG_SERIES} eller --{ARG_FORMULA}.")
        sys.exit(1)

    files_dict = parse_files_arg(args.input_files)
    
    use_time_col = args.col_time
    if use_time_col and use_time_col.lower() == "none":
        use_time_col = None

    # Bygg liste over hva som skal plottes
    plot_definitions = []
    
    if args.series_list:
        for s in args.series_list:
            if "=" not in s:
                logger.error(f"Serie må ha format 'Navn=Formel'. Fikk: '{s}'")
                sys.exit(1)
            label, formula = s.split("=", 1)
            plot_definitions.append((label.strip(), formula.strip()))
    else:
        plot_definitions.append(("Resultat", args.calc_formula))

    logger.info("--- Starter prosessering (Parallelt) ---")
    
    loaded_dfs_cache = {} 
    raw_results = []
    
    # Bruker ThreadPoolExecutor for multithreading
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for label, formula in plot_definitions:
            future = executor.submit(
                process_single_series, 
                label, formula, files_dict, loaded_dfs_cache, args, use_time_col
            )
            futures.append(future)
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                raw_results.append(res)
    
    if not raw_results:
        logger.warning("Ingen data å plotte.")
        return

    # --- NY LOGIKK: SLÅ SAMMEN SERIER MED SAMME NAVN ---
    logger.info("Konsoliderer serier...")
    consolidated_dict = {}

    for res in raw_results:
        if res.label not in consolidated_dict:
            consolidated_dict[res.label] = []
        consolidated_dict[res.label].append(res.df)
    
    final_results = []
    for label, dfs in consolidated_dict.items():
        if len(dfs) == 1:
            # Bare én del, bruk den direkte
            final_results.append(SensorResult(label=label, df=dfs[0]))
        else:
            # Flere deler (f.eks 2024 og 2025), lim dem sammen og sorter på tid
            logger.info(f"  -> Slår sammen {len(dfs)} deler for serien '{label}' til én tidslinje.")
            combined_df = pd.concat(dfs).sort_values('Datetime')
            final_results.append(SensorResult(label=label, df=combined_df))

    logger.info("Genererer plott...")
    plot_resultat(final_results, args.plot_title, output_file=args.output_file)

if __name__ == "__main__":
    main()