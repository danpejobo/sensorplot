import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

def last_og_rens_data(filsti, alias, col_date, col_time, col_data):
    """
    Laster Excel eller CSV-fil.
    Håndterer metadata i toppen av CSV-filer automatisk.
    """
    if not os.path.exists(filsti):
        raise FileNotFoundError(f"Finner ikke filen '{filsti}'.")

    # Sjekk filendelse
    _, ext = os.path.splitext(filsti)
    ext = ext.lower()

    try:
        if ext == '.xlsx':
            # Excel leses som før
            df = pd.read_excel(filsti, engine='openpyxl')
        
        elif ext == '.csv':
            # CSV krever detektivarbeid pga metadata i toppen.
            header_row = 0
            encoding = 'latin1' # Vanlig for loggere (støtter °C tegnet)
            
            # 1. Finn linjen der headeren (f.eks "Date") starter
            with open(filsti, 'r', encoding=encoding) as f:
                for i, line in enumerate(f):
                    if col_date in line:
                        header_row = i
                        break
            
            # 2. Les CSV med riktige innstillinger for norske data
            df = pd.read_csv(
                filsti, 
                sep=';',        # Semikolon som skille
                decimal=',',    # Komma som desimal
                skiprows=header_row, 
                encoding=encoding,
                on_bad_lines='skip' 
            )
            
        else:
             raise ValueError(f"Ukjent filformat: {ext}. Støtter kun .xlsx og .csv")

    except Exception as e:
        raise ValueError(f"Kunne ikke lese {filsti}: {e}")
    
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
            # dayfirst=True er viktig for CSV (f.eks 19.09.2024)
            df['Datetime'] = pd.to_datetime(df[col_date].astype(str) + ' ' + df[col_time].astype(str), dayfirst=True)
        except Exception as e:
            raise ValueError(f"Feil ved sammenslåing av dato/tid i {alias}: {e}")

    elif col_date in df.columns:
        try:
            df['Datetime'] = pd.to_datetime(df[col_date].astype(str), dayfirst=True)
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
        df = serie['df']
        label = serie['label']
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