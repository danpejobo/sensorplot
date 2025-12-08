from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import logging
import os

# Opprett logger for denne modulen
logger = logging.getLogger(__name__)

# --- DATACLASS ---
@dataclass
class SensorResult:
    label: str
    df: pd.DataFrame

# --- TYPE HINTING ---
def last_og_rens_data(
    filsti: str | Path, 
    alias: str, 
    col_date: str, 
    col_time: str | None, 
    col_data: str
) -> pd.DataFrame:
    """
    Laster Excel eller CSV-fil med automatisk deteksjon av format og metadata.
    """
    path = Path(filsti)
    if not path.exists():
        raise FileNotFoundError(f"Finner ikke filen '{path}'")

    ext = path.suffix.lower()
    day_first_config = False

    match ext:
        case '.xlsx':
            # --- EXCEL LOGIKK ---
            df_peek = pd.read_excel(path, engine='openpyxl', nrows=30, header=None)
            
            header_row = 0
            found_header = False
            
            for idx, row in df_peek.iterrows():
                row_values = [str(val).strip() for val in row.values]
                if col_date in row_values:
                    header_row = idx
                    found_header = True
                    break
            
            if not found_header:
                logger.warning(f"Fant ikke '{col_date}' i toppen av {path}. Leser fra start.")

            df = pd.read_excel(path, engine='openpyxl', header=header_row)
            
            if not df.empty and col_date in df.columns:
                first_val = df[col_date].dropna().iloc[0]
                if isinstance(first_val, str) and '.' in first_val:
                    day_first_config = True
                else:
                    day_first_config = False
        
        case '.csv':
            # --- CSV LOGIKK ---
            header_row = 0
            encoding = 'latin1'
            header_line_content = ""
            
            with open(path, 'r', encoding=encoding) as f:
                for i, line in enumerate(f):
                    if col_date in line:
                        header_row = i
                        header_line_content = line
                        break
            
            if ';' in header_line_content:
                sep = ';'
                decimal = ','
                day_first_config = True
            else:
                sep = ','
                decimal = '.'
                day_first_config = False
            
            df = pd.read_csv(
                path, 
                sep=sep, 
                decimal=decimal, 
                skiprows=header_row, 
                encoding=encoding,
                on_bad_lines='skip'
            )
            
        case _:
            raise ValueError(f"Ukjent filformat: {ext}")
    
    df.columns = [str(c).strip() for c in df.columns]
    
    if col_data not in df.columns:
         raise ValueError(f"Fant ikke datakolonnen '{col_data}' i {path}. Tilgjengelige: {df.columns.tolist()}")

    if col_time and col_time in df.columns:
        if col_date not in df.columns:
             raise ValueError(f"Mangler datokolonne '{col_date}' i {path}")
        try:
            df['Datetime'] = pd.to_datetime(
                df[col_date].astype(str) + ' ' + df[col_time].astype(str), 
                dayfirst=day_first_config
            )
        except Exception as e:
            raise ValueError(f"Feil ved dato/tid sammenslåing i {alias}: {e}")

    elif col_date in df.columns:
        try:
            df['Datetime'] = pd.to_datetime(
                df[col_date].astype(str), 
                dayfirst=day_first_config
            )
        except Exception as e:
             raise ValueError(f"Kunne ikke tolke '{col_date}' som dato i {alias}: {e}")
    else:
        raise ValueError(f"Fant verken '{col_date}' eller '{col_time}' i {path}.")
    
    df = df.sort_values('Datetime')
    
    df_clean = df[['Datetime', col_data]].copy()
    df_clean.columns = ['Datetime', f'{alias}.ch1']
    
    return df_clean

def vask_data(df: pd.DataFrame, kolonne: str, z_score: float) -> tuple[pd.DataFrame, int]:
    data = df[kolonne]
    std = data.std()
    
    if std == 0: return df, 0
    
    mean = data.mean()
    nedre = mean - (z_score * std)
    ovre = mean + (z_score * std)
    
    df_vasket = df[(data >= nedre) & (data <= ovre)].copy()
    fjernet = len(df) - len(df_vasket)
    
    return df_vasket, fjernet

def plot_resultat(
    result_series_list: list[SensorResult], 
    tittel: str, 
    output_file: str | None = None
) -> None:
    """Genererer plottet for FLERE serier."""
    fig, ax = plt.subplots(figsize=(14, 7))
    
    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = prop_cycle.by_key()['color']
    
    for i, serie in enumerate(result_series_list):
        df = serie.df
        label = serie.label
        farge = colors[i % len(colors)]
        ax.plot(df['Datetime'], df['Resultat'], label=label, color=farge, linewidth=1.5, alpha=0.9)
    
    ax.set_title(tittel, fontsize=14)
    ax.set_ylabel("Verdi", fontsize=12)
    
    # --- SMARTERE X-AKSE FORMATERING (NYTT) ---
    
    # 1. Bruk AutoDateLocator i stedet for WeekdayLocator.
    #    Denne analyserer dataene og finner beste intervall (år, mnd, uke, dag).
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    
    # 2. Format: Vi beholder norsk dato-stil
    formatter = mdates.DateFormatter('%d.%m.%Y')
    ax.xaxis.set_major_formatter(formatter)
    
    # 3. Autofmt: Roterer datoene automatisk så de ikke overlapper
    fig.autofmt_xdate() 
    
    # (Vi fjerner manuell rotasjon og ticks-grid manipulation som var her før,
    #  da autofmt og autolocator gjør en bedre jobb)
    
    ax.autoscale(enable=True, axis='y', tight=False)
    ax.grid(True, which='major', linestyle='-', alpha=0.8)
    ax.minorticks_on()
    ax.grid(True, which='minor', linestyle=':', alpha=0.4)
    
    ax.legend()
    plt.tight_layout()
    
    if output_file:
        try:
            plt.savefig(output_file)
            logger.info(f"Plot lagret til fil: {output_file}")
        except Exception as e:
            logger.error(f"Kunne ikke lagre plot til {output_file}: {e}")
    else:
        logger.info("Viser plot...")
        plt.show()