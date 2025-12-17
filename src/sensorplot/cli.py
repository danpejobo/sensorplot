import argparse
import sys
import re
import pandas as pd
import concurrent.futures
import threading
import logging
import yaml
from pathlib import Path
from sensorplot.core import SensorResult, last_og_rens_data, vask_data, plot_resultat

# Opprett logger
logger = logging.getLogger(__name__)

# ==============================================================================
#   KONFIGURASJON
# ==============================================================================

ARG_CONFIG = 'config'
ARG_FILES = 'files'
ARG_SERIES = 'series'
ARG_FORMULA = 'formel'
ARG_CLEAN = 'clean'
ARG_TITLE = 'tittel'
ARG_OUTPUT = 'output'
ARG_X_INT = 'x-interval'

ARG_COL_DATE = 'datecol'
ARG_COL_TIME = 'timecol'
ARG_COL_DATA = 'datacol'

DEFAULT_Z_SCORE = 3.0
DEF_DATE = 'Date5'
DEF_TIME = 'Time6'
DEF_DATA = 'ch1'

BESKRIVELSE = """
Verktøy for å plotte og beregne sensordata fra Excel-filer (.xlsx) og CSV.
Støtter konfigurasjonsfil (YAML) for komplekse oppsett med ulike filformater.
Kan beregne nye serier basert på formler som 'L1.Nivå - B1.Trykk'.
"""

EKSEMPLER = f"""
EKSEMPLER:

1. Bruk konfigurasjonsfil (Anbefalt):
   sensorplot -c plot_oppsett.yaml

2. Enkel plotting fra kommandolinjen:
   sensorplot --files L1=data.xlsx --series "Vannstand=L1.ch1" --output plott.png

3. Avansert formel med egne kolonnenavn:
   sensorplot --files L=logger.csv B=baro.csv --datacol Level --series "Korrigert=L.Level - B.Level"

4. Overstyr globale kolonner per fil (krever config):
   (Se dokumentasjon for YAML-syntaks)
"""

cache_lock = threading.Lock()


def load_config_file(filepath):
    path = Path(filepath)
    if not path.exists():
        logger.error(f"Finner ikke konfigurasjonsfilen: {path}")
        sys.exit(1)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Feil ved lesing av YAML: {e}")
        sys.exit(1)


def normalize_files_dict(raw_files_dict):
    """
    Sørger for at alle filer har samme struktur internt:
    {'alias': {'path': '...', 'cols': {...}}}
    """
    normalized = {}
    for alias, value in raw_files_dict.items():
        if isinstance(value, str):
            # Enkel string ("path/to/file") -> Bruk globale kolonner
            normalized[alias] = {'path': value, 'cols': {}}
        elif isinstance(value, dict):
            # Objekt med overrides -> Hent ut path og kolonner
            if 'path' not in value:
                logger.error(f"Fil-definisjon for '{alias}' mangler 'path'.")
                sys.exit(1)

            # Hent ut eventuelle kolonne-overstyringer
            cols = {}
            if 'col_date' in value:
                cols['col_date'] = value['col_date']
            if 'col_time' in value:
                cols['col_time'] = value['col_time']
            if 'col_data' in value:
                cols['col_data'] = value['col_data']

            normalized[alias] = {'path': value['path'], 'cols': cols}
    return normalized


def parse_files_arg(file_args):
    """Parser CLI input: ['Alias=Path'] -> Standard struktur."""
    if not file_args:
        return {}
    files_dict = {}
    for item in file_args:
        if "=" not in item:
            logger.error(f"Ugyldig format: '{item}'. Bruk Alias=Filnavn")
            sys.exit(1)
        alias, path = item.split("=", 1)
        # CLI-filer har ingen spesielle kolonner (bruker globale)
        files_dict[alias.strip()] = {'path': path.strip(), 'cols': {}}
    return files_dict


def extract_aliases_from_formula(formula):
    pattern = r'\b([a-zA-Z0-9_æøåÆØÅ]+)\.ch1\b'
    return re.findall(pattern, formula)


def process_single_series(series_label, formula, all_files_dict, loaded_dfs_cache, global_args, global_time_col):
    """
    Behandler en enkelt serie/formel (designet for å kjøres i en tråd).

    Denne funksjonen analyserer en formelstreng (f.eks. "L1.Nivå - B1.Trykk"),
    identifiserer hvilke filer og kolonner som trengs, laster dem inn (via cache),
    slår sammen tidsseriene, utfører beregningen og vasker resultatet for støy.

    Args:
        series_label (str): Navnet på serien som skal vises i plottet/legenden.
        formula (str): Matematisk formel (f.eks. "L1.Nivå - 10"). Må inneholde 'Alias.Kolonne'.
        all_files_dict (dict): Register over alle tilgjengelige filer og deres stier/innstillinger.
        loaded_dfs_cache (dict): Et delt dictionary (thread-safe) som lagrer ferdig lastede DataFrames for å unngå dobbel lesing.
        global_args (Namespace): Globale innstillinger fra CLI/Config (f.eks. default kolonner, Z-score).
        global_time_col (str): Navn på standard tidskolonne hvis filen ikke spesifiserer en egen.

    Returns:
        SensorResult | None: Returnerer et objekt med label og resultat-DataFrame hvis vellykket, 
                               ellers None hvis noe feilet (f.eks. manglende fil eller beregningsfeil).
    """
    logger.info(f"Starter serie: '{series_label}'...")

    # 1. Finn alle referanser på formen 'Alias.Kolonne' i formelen
    # Vi leter etter ord som står foran og bak et punktum
    potential_refs = re.findall(
        r'\b([a-zA-Z0-9_\-æøåÆØÅ]+)\.([a-zA-Z0-9_\-æøåÆØÅ]+)\b', formula)

    needed_aliases = []
    for alias, col in potential_refs:
        # Sjekk om delen foran punktum faktisk er et kjent fil-alias
        if alias in all_files_dict:
            needed_aliases.append(alias)

    # Fjern duplikater
    needed_aliases = list(set(needed_aliases))

    if not needed_aliases:
        logger.error(f"Fant ingen kjente aliaser i formelen: {formula}")
        return None

    current_dfs = []

    for alias in needed_aliases:
        # Hent fil-info
        file_info = all_files_dict[alias]
        file_path = file_info['path']
        file_cols = file_info['cols']

        # BESTEM KOLONNENAVN:
        # Bruk fil-spesifikk override, eller fall tilbake på global setting
        use_date = file_cols.get('col_date', global_args.col_date)
        use_data = file_cols.get('col_data', global_args.col_data)

        # Tidshåndtering (kan være None)
        if 'col_time' in file_cols:
            use_time = file_cols['col_time']
            if use_time and use_time.lower() == "none":
                use_time = None
        else:
            use_time = global_time_col

        # Sjekk cache / Last data
        if alias not in loaded_dfs_cache:
            with cache_lock:
                if alias not in loaded_dfs_cache:
                    logger.info(
                        f"  -> Laster {alias} (Dato: {use_date}, Tid: {use_time}, Data: {use_data})...")
                    try:
                        # Merk: last_og_rens_data returnerer nå kolonne navngitt 'Alias.DataKolonne'
                        loaded_dfs_cache[alias] = last_og_rens_data(
                            file_path, alias, use_date, use_time, use_data
                        )
                    except Exception as e:
                        logger.error(f"  -> Feil ved lesing av {alias}: {e}")
                        return None

        current_dfs.append(loaded_dfs_cache[alias])

    # Slå sammen (Merge)
    merged_df = current_dfs[0]
    for other_df in current_dfs[1:]:
        merged_df = pd.merge_asof(
            merged_df, other_df, on='Datetime', direction='nearest', tolerance=pd.Timedelta('10min')
        )

    # Gjør formelen trygg for eval() ved å sette backticks rundt kjente 'Alias.Kolonne'
    # Dette gjør at pandas skjønner at "L1.Level" er én kolonne, og ikke objektet L1 sin property Level.
    def replace_match(match):
        a, c = match.group(1), match.group(2)
        if a in all_files_dict:
            return f"`{a}.{c}`"  # Eks: `L1.Level`
        return match.group(0)

    safe_formel = re.sub(
        r'\b([a-zA-Z0-9_\-æøåÆØÅ]+)\.([a-zA-Z0-9_\-æøåÆØÅ]+)\b', replace_match, formula)

    try:
        merged_df['Resultat'] = merged_df.eval(safe_formel)
    except Exception as e:
        logger.error(f"  -> Feil i formel '{formula}': {e}")
        return None

    # Støyvask
    if global_args.clean_threshold is not None:
        merged_df, antall = vask_data(
            merged_df, 'Resultat', z_score=global_args.clean_threshold)
        if antall > 0:
            logger.info(f"  -> {series_label}: Renset {antall} punkter.")

    if merged_df.empty:
        logger.warning(
            f"  -> {series_label}: Ingen data igjen etter prosessering.")
        return None

    logger.info(f"Ferdig med del-serie: '{series_label}'")
    return SensorResult(label=series_label, df=merged_df)


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)s: %(message)s')

    parser = argparse.ArgumentParser(
        description=BESKRIVELSE, epilog=EKSEMPLER, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(f'--{ARG_CONFIG}', '-c', dest='config_file',
                        type=str, help='Sti til YAML-konfig.')
    parser.add_argument(f'--{ARG_FILES}', dest='input_files', nargs='+',
                        help='Liste over filer. Format: Alias=Filnavn.xlsx')
    parser.add_argument(f'--{ARG_SERIES}', dest='series_list',
                        nargs='+', help='Liste over serier.')
    parser.add_argument(f'--{ARG_FORMULA}', dest='calc_formula',
                        type=str, help='Legacy: Enkel formel.')
    parser.add_argument(f'--{ARG_CLEAN}', dest='clean_threshold', nargs='?',
                        const=DEFAULT_Z_SCORE, type=float, default=None, help=f'Fjern støy.')
    parser.add_argument(f'--{ARG_TITLE}', dest='plot_title',
                        type=str, default=None, help='Tittel')
    parser.add_argument(f'--{ARG_OUTPUT}', dest='output_file', nargs='?',
                        const='sensorplot.png', default=None, type=str, help='Lagre plott.')
    parser.add_argument(f'--{ARG_X_INT}', dest='x_interval',
                        type=str, default=None, help='Manuell X-akse.')

    # Kolonner (Globale defaults)
    parser.add_argument(f'--{ARG_COL_DATE}', dest='col_date',
                        type=str, default=None, help='Global Dato-kolonne')
    parser.add_argument(f'--{ARG_COL_TIME}', dest='col_time',
                        type=str, default=None, help='Global Tid-kolonne')
    parser.add_argument(f'--{ARG_COL_DATA}', dest='col_data',
                        type=str, default=None, help='Global Data-kolonne')

    args = parser.parse_args()

    # --- VARIABLER ---
    files_dict = {}  # Format: {'Alias': {'path': '...', 'cols': {...}}}
    plot_definitions = []

    config_defaults = {
        'col_date': DEF_DATE,
        'col_time': DEF_TIME,
        'col_data': DEF_DATA,
        'title': "Sensor Plot",
        'clean': None,
        'output': None,
        'x_interval': None
    }

    # 1. LAST FRA CONFIG
    if args.config_file:
        logger.info(f"Leser konfigurasjon fra {args.config_file}...")
        cfg = load_config_file(args.config_file)

        settings = cfg.get('settings', {})
        for key, val in settings.items():
            if key in config_defaults:
                config_defaults[key] = val

        # Håndter filer med normalisering
        raw_files = cfg.get('files', {})
        files_dict = normalize_files_dict(raw_files)

        for s in cfg.get('series', []):
            plot_definitions.append((s['label'], s['formula']))

    # 2. OVERSTYR MED CLI
    if args.input_files:
        # CLI-filer legges til (eller overskriver eksisterende alias)
        files_dict.update(parse_files_arg(args.input_files))

    if args.series_list:
        for s in args.series_list:
            if "=" not in s:
                logger.error(f"Serie feilformat: {s}")
                sys.exit(1)
            lbl, frm = s.split("=", 1)
            plot_definitions.append((lbl.strip(), frm.strip()))
    elif args.calc_formula:
        plot_definitions.append(("Resultat", args.calc_formula))

    if not files_dict:
        logger.error("Ingen filer definert.")
        sys.exit(1)
    if not plot_definitions:
        logger.error("Ingen serier definert.")
        sys.exit(1)

    # 3. SETT ENDELIGE GLOBALE INNSTILLINGER
    final_col_date = args.col_date if args.col_date else config_defaults['col_date']
    final_col_time = args.col_time if args.col_time else config_defaults['col_time']
    final_col_data = args.col_data if args.col_data else config_defaults['col_data']
    final_title = args.plot_title if args.plot_title else config_defaults['title']
    final_output = args.output_file if args.output_file else config_defaults['output']
    final_x_int = args.x_interval if args.x_interval else config_defaults['x_interval']

    if args.clean_threshold is not None:
        final_clean = args.clean_threshold
    else:
        final_clean = config_defaults['clean']

    if final_col_time and final_col_time.lower() == "none":
        final_col_time = None

    # --- START ---
    logger.info("--- Starter prosessering ---")

    loaded_dfs_cache = {}
    raw_results = []

    # Objekt for å bære globale innstillinger
    global_args = argparse.Namespace(
        col_date=final_col_date,
        col_data=final_col_data,
        clean_threshold=final_clean
    )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for label, formula in plot_definitions:
            future = executor.submit(
                process_single_series,
                label, formula, files_dict, loaded_dfs_cache,
                global_args, final_col_time
            )
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                raw_results.append(res)

    if not raw_results:
        logger.warning("Ingen data å plotte.")
        return

    logger.info("Konsoliderer serier...")
    consolidated_dict = {}
    for res in raw_results:
        if res.label not in consolidated_dict:
            consolidated_dict[res.label] = []
        consolidated_dict[res.label].append(res.df)

    final_results = []
    for label, dfs in consolidated_dict.items():
        if len(dfs) == 1:
            final_results.append(SensorResult(label=label, df=dfs[0]))
        else:
            logger.info(f"  -> Slår sammen {len(dfs)} deler for '{label}'.")
            combined_df = pd.concat(dfs).sort_values('Datetime')
            final_results.append(SensorResult(label=label, df=combined_df))

    logger.info("Genererer plott...")
    plot_resultat(final_results, final_title,
                  output_file=final_output, x_interval=final_x_int)


if __name__ == "__main__":
    main()
