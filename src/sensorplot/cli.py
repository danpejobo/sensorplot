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

ARG_FILES = 'files'    # Liste over filer (Alias=Fil)
ARG_SERIES = 'series'   # Liste over serier ("Navn=Formel")
ARG_FORMULA = 'formel'   # Legacy: Enkel formel
ARG_CLEAN = 'clean'    # Rensing (Z-score)
ARG_TITLE = 'tittel'   # Tittel på plott
ARG_OUTPUT = 'output'   # Lagre til fil

# Flagg for kolonnenavn
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

1. FLERE SERIER (Hovedfunksjon):
   Plott flere linjer i samme graf. Her plotter vi to lokasjoner (L1 og L2)
   korrigert mot samme barometer (B).
   
   sensorplot --{ARG_FILES} L1=Laksemyra1.xlsx L2=Laksemyra2.xlsx B=Baro.xlsx \\
              --{ARG_SERIES} "Laksemyra 1=L1.ch1 - B.ch1" "Laksemyra 2=L2.ch1 - B.ch1"

2. ENKELT PLOTT (Hurtigbruk):
   Du kan fortsatt bruke --{ARG_FORMULA} for en enkelt linje.
   
   sensorplot --{ARG_FILES} V=Vann.xlsx B=Baro.xlsx --{ARG_FORMULA} "V.ch1 - B.ch1"

3. AVANSERT FORMELL (Enhetskonvertering):
   Konverter barometer (kPa) til meter vannsøyle før subtraksjon.
   
   sensorplot --{ARG_FILES} V=Vann.xlsx B=Baro.xlsx \\
              --{ARG_SERIES} "Justert nivå=V.ch1 - (B.ch1 / 9.81)"

4. FJERNE STØY (Cleaning):
   Fjerner automatisk punkter som er støy (Standard: Z-score > {DEFAULT_Z_SCORE}).
   
   sensorplot --{ARG_FILES} D=Data.xlsx --{ARG_FORMULA} "D.ch1" --{ARG_CLEAN}

5. LAGRE TIL FIL (Server / Headless):
   Nyttig hvis du kjører på en server uten skjerm (VS Code remote).
   
   sensorplot --{ARG_FILES} D=Data.xlsx --{ARG_FORMULA} "D.ch1" --{ARG_OUTPUT} plott.png

6. EGNE KOLONNENAVN (Custom Excel):
   Hvis filene dine ikke følger standarden ({DEF_DATE}, {DEF_TIME}, {DEF_DATA}).
   F.eks hvis kolonnene heter: 'Dato', 'Tid', 'Måling'.
   
   sensorplot --{ARG_FILES} F=Fil.xlsx --{ARG_FORMULA} "F.ch1" \\
              --{ARG_COL_DATE} Dato --{ARG_COL_TIME} Tid --{ARG_COL_DATA} Måling

7. DATO OG TID SAMLET:
   Hvis dato og tid ligger i samme kolonne (f.eks 'Tidsstempel').
   
   sensorplot --{ARG_FILES} F=Fil.xlsx --{ARG_FORMULA} "F.ch1" \\
              --{ARG_COL_DATE} Tidsstempel --{ARG_COL_TIME} None
"""

# ==============================================================================

# Legg til en lås for trådsikker caching
cache_lock = threading.Lock()


def parse_files_arg(file_args):
    """Parser input: ['Alias=Path', ...] -> {'Alias': 'Path'}"""
    files_dict = {}
    for item in file_args:
        if "=" not in item:
            logger.error(
                f"FEIL: Ugyldig format på fil-argumentet '{item}'. Bruk Alias=Filnavn.xlsx")
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
    logger.info(
        # Endret tekst litt for å vise parallellitet
        f"Starter serie: '{series_label}'...")

    needed_aliases = extract_aliases_from_formula(formula)
    if not needed_aliases:
        logger.error(f"FEIL: Fant ingen aliaser i formelen: {formula}")
        return None  # Returner None i stedet for sys.exit så vi ikke dreper alle tråder

    current_dfs = []

    # --- TRÅDSIKKER LASTING AV FILER ---
    for alias in needed_aliases:
        # Sjekk først uten lås (raskt)
        if alias not in loaded_dfs_cache:
            # Hvis ikke i cache, lås døra før vi sjekker igjen og laster
            with cache_lock:
                if alias not in loaded_dfs_cache:  # Dobbeltsjekk
                    if alias not in all_files_dict:
                        logger.error(f"FEIL: Alias '{alias}' mangler.")
                        return None

                    logger.info(f"  -> Laster fil for {alias}...")
                    try:
                        loaded_dfs_cache[alias] = last_og_rens_data(
                            all_files_dict[alias], alias, args.col_date, use_time_col, args.col_data
                        )
                    except Exception as e:
                        logger.error(f"  -> FEIL ved lesing av {alias}: {e}")
                        return None

        # Nå er filen garantert i cache, hent den ut
        current_dfs.append(loaded_dfs_cache[alias])

    # --- HER STARTER BEREGNINGEN (CPU) ---
    # I Python 3.12 deler disse på 1 kjerne.
    # I Python 3.13+ (free-threaded) vil disse kjøre på HVER SIN kjerne!

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
        logger.error(f"  -> FEIL i formel '{formula}': {e}")
        return None

    if args.clean_threshold is not None:
        merged_df, antall = vask_data(
            merged_df, 'Resultat', z_score=args.clean_threshold)
        if antall > 0:
            logger.info(f"  -> {series_label}: Renset {antall} punkter.")

    if merged_df.empty:
        logger.warning(f"  -> {series_label}: Ingen data igjen.")
        return None

    logger.info(f"Ferdig med: '{series_label}'")
    return SensorResult(label=series_label, df=merged_df)


def main():
    # --- KONFIGURER LOGGING ---
    # format: "Nivå: Melding" (f.eks "INFO: Laster fil...")
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
    parser.add_argument(f'--{ARG_COL_DATE}', dest='col_date',
                        type=str, default=DEF_DATE, help=f'Standard: {DEF_DATE}')
    parser.add_argument(f'--{ARG_COL_TIME}', dest='col_time',
                        type=str, default=DEF_TIME, help=f'Standard: {DEF_TIME}')
    parser.add_argument(f'--{ARG_COL_DATA}', dest='col_data',
                        type=str, default=DEF_DATA, help=f'Standard: {DEF_DATA}')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    if not args.series_list and not args.calc_formula:
        logger.error(f"FEIL: Du må angi enten --{ARG_SERIES} eller --{ARG_FORMULA}.")
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
                logger.error(f"FEIL: Serie må ha format 'Navn=Formel'. Fikk: '{s}'")
                sys.exit(1)
            label, formula = s.split("=", 1)
            plot_definitions.append((label.strip(), formula.strip()))
    else:
        # Legacy fallback
        plot_definitions.append(("Resultat", args.calc_formula))

    logger.info(f"--- Starter prosessering (Parallelt) ---")

    loaded_dfs_cache = {}
    final_results = []

    # Bruker ThreadPoolExecutor for multithreading
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Start alle oppgavene ("futures")
        futures = []
        for label, formula in plot_definitions:
            future = executor.submit(
                process_single_series,
                label, formula, files_dict, loaded_dfs_cache, args, use_time_col
            )
            futures.append(future)

        # Samle inn resultatene etter hvert som de blir ferdige
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                final_results.append(res)

    if not final_results:
        logger.warning("Ingen data å plotte.")
        return

    logger.info("\nGenererer plott...")
    plot_resultat(final_results, args.plot_title, output_file=args.output_file)


if __name__ == "__main__":
    main()
