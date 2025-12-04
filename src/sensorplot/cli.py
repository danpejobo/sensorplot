import argparse
import sys
import re
import pandas as pd
from sensorplot.core import last_og_rens_data, vask_data, plot_resultat

# --- KONFIGURASJON ---
ARG_FILES   = 'files'
ARG_FORMULA = 'formel'
ARG_CLEAN   = 'clean'
ARG_TITLE   = 'tittel'
DEFAULT_Z_SCORE = 3.0 

# --- HJELPETEKST ---
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
   sensorplot --{ARG_FILES} Baro=Baro.xlsx Vann=Laksemyra.xlsx --{ARG_FORMULA} "Vann.ch1 - Baro.ch1"

2. Med konvertering (hvis Baro er kPa og Vann er meter, og du vil justere):
   sensorplot --{ARG_FILES} B=Baro.xlsx V=Vann.xlsx --{ARG_FORMULA} "V.ch1 - (B.ch1 / 9.81)" --{ARG_TITLE} "Korrigert Vannstand"

3. Fjerne støy (Z-score):
   Hvis dataene har ekstreme hopp/feil, bruk --{ARG_CLEAN}. 
   En verdi på 3.0 eller 4.0 er vanlig. Lavere tall vasker hardere.
   sensorplot --{ARG_FILES} Data=Fil.xlsx --{ARG_FORMULA} "Data.ch1" --{ARG_CLEAN} 3.5

4. Flere filer:
   sensorplot --{ARG_FILES} A=Fil1.xlsx B=Fil2.xlsx C=Fil3.xlsx --{ARG_FORMULA} "(A.ch1 + B.ch1) / C.ch1"
"""

def parse_files_arg(file_args):
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
    
    parser.add_argument(f'--{ARG_FILES}', dest='input_files', nargs='+', required=True, 
                        help='Liste over filer. Format: Alias=Filnavn.xlsx')
    
    parser.add_argument(f'--{ARG_FORMULA}', dest='calc_formula', type=str, required=True, 
                        help='Matematisk formel. F.eks "A.ch1 - B.ch1"')
    
    parser.add_argument(f'--{ARG_CLEAN}', dest='clean_threshold', 
                        nargs='?', const=DEFAULT_Z_SCORE, type=float, default=None,
                        help=f'Fjern støy (Z-score). Standardverdi: {DEFAULT_Z_SCORE}')
    
    parser.add_argument(f'--{ARG_TITLE}', dest='plot_title', type=str, default="Sensor Plot", 
                        help='Tittel på plottet')

    args = parser.parse_args()
    files_dict = parse_files_arg(args.input_files)
    
    print(f"--- Starter prosessering ---")
    
    dfs = []
    try:
        for alias, filsti in files_dict.items():
            print(f"Laster {alias} ({filsti})...")
            dfs.append(last_og_rens_data(filsti, alias))
    except Exception as e:
        print(f"FEIL: {e}")
        sys.exit(1)
    
    if not dfs: return

    base_df = dfs[0]
    for other_df in dfs[1:]:
        base_df = pd.merge_asof(
            base_df, 
            other_df, 
            on='Datetime', 
            direction='nearest', 
            tolerance=pd.Timedelta('10min')
        )
    
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

    if args.clean_threshold is not None:
        base_df, antall = vask_data(base_df, 'Resultat', z_score=args.clean_threshold)
        if antall > 0:
            print(f"--- RENSING ---")
            print(f"Fjernet {antall} punkter (Z-score > {args.clean_threshold}).")

    if base_df.empty:
        print("Ingen data igjen å plotte.")
        return

    plot_resultat(base_df, 'Datetime', 'Resultat', args.plot_title, args.calc_formula)