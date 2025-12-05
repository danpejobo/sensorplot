import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

def last_og_rens_data(filsti, alias, col_date, col_time, col_data):
    """
    Laster Excel-fil med fleksible kolonnenavn.
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
    if col_time and col_time in df.columns:
        if col_date not in df.columns:
             raise ValueError(f"Mangler datokolonne '{col_date}' i {filsti}")
        try:
            df['Datetime'] = pd.to_datetime(df[col_date].astype(str) + ' ' + df[col_time].astype(str))
        except Exception as e:
            raise ValueError(f"Feil ved sammenslåing av dato/tid i {alias}: {e}")

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
    # Rename til Alias.ch1 (internt navn)
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

def plot_resultat(df, x_col, y_col, tittel, formel_tekst, output_file=None):
    """
    Genererer plottet.
    Lagrer til fil hvis output_file er satt, ellers vises GUI.
    """
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # ENDRET FARGE HER: color='royalblue' (var #111518)
    ax.plot(df[x_col], df[y_col], label='Beregnet verdi', color='royalblue', linewidth=1)
    
    ax.set_title(f"{tittel}\n({formel_tekst})", fontsize=14)
    ax.set_ylabel("Verdi", fontsize=12)
    
    # X-akse formatering
    locator = mdates.WeekdayLocator(interval=1, byweekday=mdates.MO)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
    
    plt.xticks(rotation=45)
    ax.autoscale(enable=True, axis='y', tight=False)
    ax.grid(True, which='major', linestyle='-', alpha=0.8)
    ax.minorticks_on()
    ax.grid(True, which='minor', linestyle=':', alpha=0.4)
    
    # Legger til legenden (denne vil nå automatisk få blått symbol)
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