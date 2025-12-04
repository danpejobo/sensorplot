import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

def last_og_rens_data(filsti, alias, col_date, col_time, col_data):
    """
    Laster Excel-fil med fleksible kolonnenavn.
    
    Args:
        filsti (str): Stien til filen.
        alias (str): Kallenavn for filen.
        col_date (str): Navn på datokolonnen (f.eks 'Date5').
        col_time (str): Navn på tidskolonnen (f.eks 'Time6'). Kan være None.
        col_data (str): Navn på datakolonnen (f.eks 'ch1').
    """
    if not os.path.exists(filsti):
        raise FileNotFoundError(f"Finner ikke filen '{filsti}'.")

    try:
        df = pd.read_excel(filsti, engine='openpyxl')
    except Exception as e:
        raise ValueError(f"Kunne ikke lese {filsti}: {e}")
    
    # Rens kolonnenavn (fjerner mellomrom)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Sjekk at datakolonnen finnes
    if col_data not in df.columns:
         raise ValueError(f"Fant ikke datakolonnen '{col_data}' i {filsti}. Tilgjengelige: {df.columns.tolist()}")

    # Håndtering av tid
    # Alternativ A: Vi har både dato og tid i separate kolonner
    if col_time and col_time in df.columns:
        if col_date not in df.columns:
             raise ValueError(f"Mangler datokolonne '{col_date}' i {filsti}")
        
        try:
            df['Datetime'] = pd.to_datetime(df[col_date].astype(str) + ' ' + df[col_time].astype(str))
        except Exception as e:
            raise ValueError(f"Feil ved sammenslåing av dato/tid i {alias}: {e}")

    # Alternativ B: Dato og tid er i samme kolonne (eller vi mangler tidskolonne)
    elif col_date in df.columns:
        try:
            df['Datetime'] = pd.to_datetime(df[col_date].astype(str))
        except Exception as e:
             raise ValueError(f"Kunne ikke tolke '{col_date}' som dato i {alias}: {e}")
    else:
        raise ValueError(f"Fant verken '{col_date}' eller '{col_time}' i {filsti}.")
    
    df = df.sort_values('Datetime')
    
    # Returner kun relevante data
    df_clean = df[['Datetime', col_data]].copy()
    # Rename til Alias.Kolonne
    df_clean.columns = ['Datetime', f'{alias}.ch1'] # Vi beholder .ch1 suffiks internt for enkel formelbruk
    
    return df_clean

def vask_data(df, kolonne, z_score):
    # (Ingen endring her - kopier funksjonen fra forrige versjon)
    data = df[kolonne]
    std = data.std()
    
    if std == 0: return df, 0
    
    mean = data.mean()
    nedre = mean - (z_score * std)
    ovre = mean + (z_score * std)
    
    df_vasket = df[(data >= nedre) & (data <= ovre)].copy()
    fjernet = len(df) - len(df_vasket)
    
    return df_vasket, fjernet

def plot_resultat(df, x_col, y_col, tittel, formel_tekst):
    # (Ingen endring her - kopier funksjonen fra forrige versjon)
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(df[x_col], df[y_col], label='Beregnet verdi', color='#1f77b4', linewidth=1)
    
    ax.set_title(f"{tittel}\n({formel_tekst})", fontsize=14)
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
    plt.show()