from dataclasses import dataclass
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

@dataclass
class SensorResult:
    label: str
    df: pd.DataFrame
    

def last_og_rens_data(
    filsti: str | Path, 
    alias: str, 
    col_date: str, 
    col_time: str | None, 
    col_data: str
) -> pd.DataFrame:
    
    path = Path(filsti)
    if not path.exists():
        raise FileNotFoundError(f"Finner ikke filen '{path}'")

    ext = path.suffix.lower()
    
    # Default to standard ISO (Year-Month-Day) unless CSV overrides it
    day_first_config = False

    match ext:
        case '.xlsx':
            df = pd.read_excel(path, engine='openpyxl')
        
        case '.csv':
            header_row = 0
            encoding = 'latin1'
            
            with open(path, 'r', encoding=encoding) as f:
                for i, line in enumerate(f):
                    if col_date in line:
                        header_row = i
                        break
            
            df = pd.read_csv(
                path, 
                sep=';', 
                decimal=',', 
                skiprows=header_row, 
                encoding=encoding,
                on_bad_lines='skip'
            )
            # Your CSVs use DD.MM.YYYY
            day_first_config = True
            
        case _:
            raise ValueError(f"Ukjent filformat: {ext}")
    
    # Rens kolonnenavn (fjerner mellomrom)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Sjekk at datakolonnen finnes
    if col_data not in df.columns:
         raise ValueError(f"Fant ikke datakolonnen '{col_data}' i {filsti}. Tilgjengelige: {df.columns.tolist()}")

    # Håndtering av tid
    if col_time and col_time in df.columns:
        if col_date not in df.columns:
             raise ValueError(f"Mangler datokolonne '{col_date}' i {filsti}")
        try:
            # Bruker variabelen day_first_config som vi satte over
            df['Datetime'] = pd.to_datetime(
                df[col_date].astype(str) + ' ' + df[col_time].astype(str), 
                dayfirst=day_first_config
            )
        except Exception as e:
            raise ValueError(f"Feil ved sammenslåing av dato/tid i {alias}: {e}")

    elif col_date in df.columns:
        try:
            df['Datetime'] = pd.to_datetime(
                df[col_date].astype(str), 
                dayfirst=day_first_config
            )
        except Exception as e:
             raise ValueError(f"Kunne ikke tolke '{col_date}' som dato i {alias}: {e}")
    else:
        raise ValueError(f"Fant verken '{col_date}' eller '{col_time}' i {filsti}.")
    
    df = df.sort_values('Datetime')
    
    # Returner kun relevante data
    df_clean = df[['Datetime', col_data]].copy()
    df_clean.columns = ['Datetime', f'{alias}.ch1']
    
    return df_clean

def vask_data(df, kolonne, z_score):
    """Fjerner data som er statistiske utliggere (outliers)."""
    data = df[kolonne]
    std = data.std()
    
    if std == 0: return df, 0
    
    mean = data.mean()
    nedre = mean - (z_score * std)
    ovre = mean + (z_score * std)
    
    df_vasket = df[(data >= nedre) & (data <= ovre)].copy()
    fjernet = len(df) - len(df_vasket)
    
    return df_vasket, fjernet

def plot_resultat(result_series_list, tittel, output_file=None):
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
    
    locator = mdates.WeekdayLocator(interval=1, byweekday=mdates.MO)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
    
    plt.xticks(rotation=45)
    ax.autoscale(enable=True, axis='y', tight=False)
    ax.grid(True, which='major', linestyle='-', alpha=0.8)
    ax.minorticks_on()
    ax.grid(True, which='minor', linestyle=':', alpha=0.4)
    
    ax.legend()
    plt.tight_layout()
    
    if output_file:
        try:
            plt.savefig(output_file)
            print(f"Plot lagret til fil: {output_file}")
        except Exception as e:
            print(f"Kunne ikke lagre plot til {output_file}: {e}")
    else:
        print("Viser plot...")
        plt.show()