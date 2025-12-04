import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

def last_og_rens_data(filsti, alias):
    """Laster Excel-fil, fikser datoer og gir kolonner alias."""
    if not os.path.exists(filsti):
        raise FileNotFoundError(f"Finner ikke filen '{filsti}'.")

    try:
        df = pd.read_excel(filsti, engine='openpyxl')
    except Exception as e:
        raise ValueError(f"Kunne ikke lese {filsti}: {e}")
    
    df.columns = [str(c).strip() for c in df.columns]
    
    required_time = ['Date5', 'Time6']
    if not all(col in df.columns for col in required_time):
        raise ValueError(f"{filsti} mangler tidskolonner {required_time}")

    data_col = 'ch1'
    if data_col not in df.columns:
         raise ValueError(f"Fant ikke '{data_col}' i {filsti}. Fant: {df.columns.tolist()}")

    try:
        df['Datetime'] = pd.to_datetime(df['Date5'].astype(str) + ' ' + df['Time6'].astype(str))
    except Exception as e:
        raise ValueError(f"Feil datoformat i {alias}: {e}")
    
    df = df.sort_values('Datetime')
    # Returner kun relevante data
    df_clean = df[['Datetime', data_col]].copy()
    df_clean.columns = ['Datetime', f'{alias}.{data_col}']
    
    return df_clean

def vask_data(df, kolonne, z_score):
    """Fjerner rader hvor verdien er utenfor Z-score grensen."""
    data = df[kolonne]
    std = data.std()
    
    if std == 0: 
        return df, 0  # Returnerer tuple: (DataFrame, antall_fjernet)
    
    mean = data.mean()
    nedre = mean - (z_score * std)
    ovre = mean + (z_score * std)
    
    df_vasket = df[(data >= nedre) & (data <= ovre)].copy()
    fjernet = len(df) - len(df_vasket)
    
    return df_vasket, fjernet

def plot_resultat(df, x_col, y_col, tittel, formel_tekst):
    """Lager selve plottet."""
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(df[x_col], df[y_col], label='Beregnet verdi', color='#1f77b4', linewidth=1)
    
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
    
    ax.legend()
    plt.tight_layout()
    plt.show()