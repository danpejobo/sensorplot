import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
from sensorplot.core import last_og_rens_data, plot_resultat, SensorResult

# ==============================================================================
#   TEST AV FIL-LESER (CSV Sniffing)
# ==============================================================================

def lag_fil(path, innhold, encoding='latin1'):
    """Hjelper for å lage testfiler."""
    with open(path, 'w', encoding=encoding) as f:
        f.write(innhold)
    return str(path)

def test_les_tap_format_csv(tmp_path):
    """
    Tester 'TAP' format (Internasjonal):
    - Komma som skille (,)
    - Punktum som desimal (.)
    - Metadata i toppen
    - Datoformat YYYY-MM-DD
    """
    filsti = tmp_path / "tap_data.csv"
    innhold = """Serial: 123
Location: Well 3
Trash: Data
Date,Time,Value
2024-01-01,12:00:00,10.5
2024-01-02,12:00:00,11.2
"""
    lag_fil(filsti, innhold)
    
    # Merk: Datokolonnen heter "Date", Data heter "Value"
    df = last_og_rens_data(filsti, "TAP", "Date", "Time", "Value")
    
    assert len(df) == 2
    assert df['TAP.ch1'].iloc[0] == 10.5  # Sjekk at 10.5 ble lest som tall
    assert df['Datetime'].iloc[0].year == 2024
    assert df['Datetime'].iloc[0].month == 1

def test_les_norsk_format_csv(tmp_path):
    """
    Tester 'Norsk' format:
    - Semikolon som skille (;)
    - Komma som desimal (,)
    - Datoformat DD.MM.YYYY
    """
    filsti = tmp_path / "norsk_data.csv"
    innhold = """Serienummer: 999
Sted: Myra
Dato;Tid;Nivå
31.12.2023;23:00:00;10,5
01.01.2024;00:00:00;10,6
"""
    lag_fil(filsti, innhold)
    
    df = last_og_rens_data(filsti, "Norsk", "Dato", "Tid", "Nivå")
    
    assert len(df) == 2
    assert df['Norsk.ch1'].iloc[0] == 10.5 # Sjekk at 10,5 ble til 10.5
    assert df['Datetime'].iloc[0].day == 31
    assert df['Datetime'].iloc[0].month == 12

# ==============================================================================
#   TEST AV SAMMENSLÅING (Consolidation Logic)
# ==============================================================================

def test_sammenslaaing_av_serier():
    """
    Tester logikken som brukes i CLI for å slå sammen serier med samme navn.
    Vi simulerer at 'process_single_series' har returnert tre deler.
    """
    # Del 1: 2023 data
    df1 = pd.DataFrame({'Datetime': pd.to_datetime(['2023-01-01']), 'Resultat': [100]})
    res1 = SensorResult(label="Min Serie", df=df1)
    
    # Del 2: 2024 data
    df2 = pd.DataFrame({'Datetime': pd.to_datetime(['2024-01-01']), 'Resultat': [200]})
    res2 = SensorResult(label="Min Serie", df=df2)
    
    # Del 3: En helt annen serie
    df3 = pd.DataFrame({'Datetime': pd.to_datetime(['2024-01-01']), 'Resultat': [5]})
    res3 = SensorResult(label="Annen Serie", df=df3)
    
    # --- SIMULER LOGIKKEN FRA MAIN() ---
    raw_results = [res1, res2, res3]
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
            # Her er selve logikken vi tester: concat + sort
            combined_df = pd.concat(dfs).sort_values('Datetime')
            final_results.append(SensorResult(label=label, df=combined_df))
            
    # --- VERIFISERING ---
    
    # 1. Vi skal sitte igjen med 2 resultater (ikke 3)
    assert len(final_results) == 2
    
    # 2. Finn den sammenslåtte serien
    min_serie = next(r for r in final_results if r.label == "Min Serie")
    
    # 3. Sjekk at den nå inneholder begge årene
    assert len(min_serie.df) == 2
    assert min_serie.df['Datetime'].iloc[0].year == 2023
    assert min_serie.df['Datetime'].iloc[1].year == 2024
    
    # 4. Sjekk verdiene
    assert min_serie.df['Resultat'].iloc[0] == 100
    assert min_serie.df['Resultat'].iloc[1] == 200

# ==============================================================================
#   TEST AV X-INTERVAL (Plotting)
# ==============================================================================

@patch("sensorplot.core.plt")    # Mock vekk selve plottingen så vi ikke får vinduer
@patch("sensorplot.core.mdates") # Mock mdates så vi kan sjekke hva som kalles
def test_plot_resultat_x_interval(mock_mdates, mock_plt):
    """
    Sjekker at argumentet 'x_interval' (f.eks '1M') faktisk velger riktig 
    Locator i Matplotlib.
    """
    # 1. Mock subplots returverdier (Figur, Akse)
    mock_fig = MagicMock()
    mock_ax = MagicMock()
    mock_plt.subplots.return_value = (mock_fig, mock_ax)

    # 2. FIX: Mock fargepaletten slik at 'colors' listen ikke er tom
    #    Dette forhindrer ZeroDivisionError
    mock_plt.rcParams.__getitem__.return_value.by_key.return_value.__getitem__.return_value = ['blue', 'red']

    # Dummy data
    df = pd.DataFrame({'Datetime': [pd.Timestamp('2024-01-01')], 'Resultat': [1]})
    res = SensorResult(label="Test", df=df)
    
    # Test 1: "1M" skal kalle MonthLocator(interval=1)
    plot_resultat([res], "Tittel", x_interval="1M")
    mock_mdates.MonthLocator.assert_called_with(interval=1)
    
    # Test 2: "2W" skal kalle WeekdayLocator(interval=2)
    plot_resultat([res], "Tittel", x_interval="2W")
    mock_mdates.WeekdayLocator.assert_called_with(interval=2)
    
    # Test 3: "3D" skal kalle DayLocator(interval=3)
    plot_resultat([res], "Tittel", x_interval="3D")
    mock_mdates.DayLocator.assert_called_with(interval=3)
    
    # Test 4: "1Y" skal kalle YearLocator(base=1)
    plot_resultat([res], "Tittel", x_interval="1Y")
    mock_mdates.YearLocator.assert_called_with(base=1)