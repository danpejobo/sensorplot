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
ARG_X_INT   = 'x-interval' 

ARG_COL_DATE = 'datecol'
ARG_COL_TIME = 'timecol'
ARG_COL_DATA = 'datacol'

DEFAULT_Z_SCORE = 3.0 
DEF_DATE = 'Date5'
DEF_TIME = 'Time6'
DEF_DATA = 'ch1'

# ==============================================================================
#   HJELPETEKSTER (BESKRIVELSE OG EKSEMPLER)
# ==============================================================================

BESKRIVELSE = """
-------------------------------------------------------------------------
 SENSORPLOT - Verktøy for visualisering og analyse av tidsseriedata
-------------------------------------------------------------------------
 Dette verktøyet er designet for å behandle store mengder sensordata 
 fra både Excel (.xlsx) og CSV-filer (.csv).

 HOVEDFUNKSJONER:
  1. Multiformat: Leser automatisk filer fra ulike loggere (både norsk
     og internasjonalt datoformat).
  2. Parallell prosessering: Laster og behandler filer samtidig for høy ytelse.
  3. Serier: Kan plotte flere uavhengige linjer i samme graf, eller sy sammen
     oppdelte filer (f.eks 2023 + 2024) til én kontinuerlig tidslinje.
  4. Matematikk: Lar deg korrigere data (f.eks barometrisk kompensasjon)
     direkte i kommandolinjen.
  5. Vasking: Fjerner automatisk støy (outliers) basert på statistikk.
"""

EKSEMPLER = f"""
EKSEMPLER PÅ BRUK:
==================

1. GRUNNLEGGENDE BRUK (To filer, én korrigert serie)
   Her laster vi en vannstand-fil (L) og en baro-fil (B). Vi plotter differansen.
   
   sensorplot --{ARG_FILES} L=Vann.xlsx B=Baro.xlsx \\
              --{ARG_SERIES} "Korrigert Vannstand=L.ch1 - B.ch1"

2. AVANSERT FORMELL (Enhetskonvertering)
   Hvis Baro er i kPa og Vann i meter, må vi konvertere Baro til meter før vi trekker fra.
   (Formel: kPa / 9.81 = meter vannsøyle).
   
   sensorplot --{ARG_FILES} L=Vann.xlsx B=Baro.xlsx \\
              --{ARG_SERIES} "Nivå=L.ch1 - (B.ch1 / 9.81)"

3. FLERE LOKASJONER I SAMME PLOTT
   Sammenlign to forskjellige brønner (L1 og L2) korrigert mot samme barometer (B).
   
   sensorplot --{ARG_FILES} L1=Brønn1.xlsx L2=Brønn2.xlsx B=Baro.xlsx \\
              --{ARG_SERIES} "Brønn 1=L1.ch1 - B.ch1" "Brønn 2=L2.ch1 - B.ch1"

4. SAMMENSLÅING AV FLERE ÅR (Long time series)
   Har du dataene dine splittet i flere filer (f.eks. "Data2023.xlsx" og "Data2024.xlsx")?
   Gi dem SAMME navn i --{ARG_SERIES}, så syr programmet dem sammen automatisk.
   
   sensorplot --{ARG_FILES} D23=Data2023.xlsx D24=Data2024.xlsx B=Baro.xlsx \\
              --{ARG_SERIES} "Lang tidsserie=D23.ch1 - B.ch1" "Lang tidsserie=D24.ch1 - B.ch1"

5. LOGGER-FILER (CSV) MED EGNE KOLONNENAVN
   Mange loggere bruker andre kolonnenavn enn standarden ({DEF_DATE}/{DEF_TIME}/{DEF_DATA}).
   Her spesifiserer vi at dato heter 'Date', tid 'Time' og data 'LEVEL'.
   
   sensorplot --{ARG_FILES} L=Logger.csv \\
              --{ARG_SERIES} "Rådata=L.ch1" \\
              --{ARG_COL_DATE} Date --{ARG_COL_TIME} Time --{ARG_COL_DATA} LEVEL

6. RYDDIGERE X-AKSE (Manuell intervall)
   Hvis en lang tidsserie gir for tett tekst på x-aksen, kan du tvinge intervallet.
   Koder: D=Dag, W=Uke, M=Måned, Y=År.
   
   sensorplot ... --{ARG_X_INT} 1M   (Vis en etikett for hver måned)
   sensorplot ... --{ARG_X_INT} 2W   (Vis en etikett hver 2. uke)

7. FJERNE STØY OG LAGRE TIL FIL (Server-modus)
   --{ARG_CLEAN} fjerner punkter som avviker mye (Z-score).
   --{ARG_OUTPUT} lagrer bildet i stedet for å vise det på skjermen.
   
   sensorplot --{ARG_FILES} D=Data.xlsx --{ARG_FORMULA} "D.ch1" \\
              --{ARG_CLEAN} --{ARG_OUTPUT} rapport.png
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
    Kjøres i en egen tråd via ThreadPoolExecutor.
    Henter filer (cachet), merger dem tidsmessig, og beregner formelen.
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
            # Lås kun hvis vi faktisk må laste filen (eller vente på noen som gjør det)
            with cache_lock:
                if alias not in loaded_dfs_cache: # Dobbeltsjekk innenfor låsen
                    if alias not in all_files_dict:
                        logger.error(f"Alias '{alias}' mangler i fil-listen (--{ARG_FILES}).")
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
    # Merge alle filene til samme tidslinje som den første filen i formelen
    merged_df = current_dfs[0]
    for other_df in current_dfs[1:]:
        merged_df = pd.merge_asof(
            merged_df, 
            other_df, 
            on='Datetime', 
            direction='nearest', 
            tolerance=pd.Timedelta('10min')
        )

    # Bytt ut Alias.ch1 med pandas-vennlig `Alias.ch1` syntax for eval()
    safe_formel = re.sub(r'\b([a-zA-Z0-9_æøåÆØÅ]+\.ch1)\b', r'`\1`', formula)
    
    try:
        merged_df['Resultat'] = merged_df.eval(safe_formel)
    except Exception as e:
        logger.error(f"  -> Feil i formel '{formula}': {e}")
        return None

    # Vask data (fjern støy)
    if args.clean_threshold is not None:
        merged_df, antall = vask_data(merged_df, 'Resultat', z_score=args.clean_threshold)
        if antall > 0:
            logger.info(f"  -> {series_label}: Renset {antall} punkter (Z-score).")

    if merged_df.empty:
        logger.warning(f"  -> {series_label}: Ingen data igjen etter prosessering.")
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
                        help='Lagre plott til fil. Uten filnavn: "sensorplot.png". Utelatt: Vis GUI.')

    parser.add_argument(f'--{ARG_X_INT}', dest='x_interval', type=str, default=None,
                        help='Manuell X-akse etikett-intervall. Eks: "2W" (2 uker), "1M" (1 mnd), "1Y" (1 år).')

    # Kolonner
    parser.add_argument(f'--{ARG_COL_DATE}', dest='col_date', type=str, default=DEF_DATE, 
                        help=f'Navn på datokolonne (Standard: {DEF_DATE})')
    parser.add_argument(f'--{ARG_COL_TIME}', dest='col_time', type=str, default=DEF_TIME, 
                        help=f'Navn på tidskolonne (Standard: {DEF_TIME}). Sett til "None" hvis samlet.')
    parser.add_argument(f'--{ARG_COL_DATA}', dest='col_data', type=str, default=DEF_DATA, 
                        help=f'Navn på datokolonne (Standard: {DEF_DATA})')
    
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
        # Legacy fallback
        plot_definitions.append(("Resultat", args.calc_formula))

    logger.info("--- Starter prosessering (Parallelt) ---")
    
    loaded_dfs_cache = {} 
    raw_results = []
    
    # Bruker ThreadPoolExecutor for å kjøre ting samtidig (I/O bundet)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for label, formula in plot_definitions:
            future = executor.submit(
                process_single_series, 
                label, formula, files_dict, loaded_dfs_cache, args, use_time_col
            )
            futures.append(future)
        
        # Hent resultater etter hvert som de blir ferdige
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                raw_results.append(res)
    
    if not raw_results:
        logger.warning("Ingen data å plotte.")
        return

    # --- KONSOLIDERING: Slå sammen serier med samme navn ---
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
    
    plot_resultat(
        final_results, 
        args.plot_title, 
        output_file=args.output_file, 
        x_interval=args.x_interval
    )

if __name__ == "__main__":
    main()