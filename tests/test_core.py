import pytest
import pandas as pd
import os
from pathlib import Path
from sensorplot.core import last_og_rens_data, vask_data

# ==============================================================================
#   HJELPEFUNKSJONER
# ==============================================================================

def lag_csv_fil(path, innhold, koding='latin1'):
    with open(path, 'w', encoding=koding) as f:
        f.write(innhold)
    return str(path)

# ==============================================================================
#   ENHETSTESTER (Unit Tests)
# ==============================================================================

def test_vask_data_fjerner_stoy():
    """Sjekker at Z-score fjerner utliggere."""
    data = {
        'Datetime': pd.date_range(start='1/1/2024', periods=10),
        'Resultat': [10, 10, 10, 10, 10, 10, 10, 10, 100, -100] 
    }
    df = pd.DataFrame(data)
    df_vasket, antall = vask_data(df, 'Resultat', z_score=1.0)
    
    assert antall == 2
    assert len(df_vasket) == 8
    assert df_vasket['Resultat'].max() == 10

def test_les_norsk_csv_med_metadata(tmp_path):
    """
    Tester at vi klarer å lese en 'Norsk' CSV-fil fra en logger.
    - Semikolon som skille
    - Komma som desimal
    - Metadata i toppen (skal hoppes over)
    - Datoformat: DD.MM.YYYY (dag først)
    """
    filnavn = tmp_path / "norsk_logg.csv"
    innhold = """Serial number: 12345
Project: Test
Location: Myra
Date;Time;Level
10.05.2024;12:00:00;10,5
11.05.2024;13:00:00;11,2
"""
    lag_csv_fil(filnavn, innhold)
    
    df = last_og_rens_data(filnavn, "Test", "Date", "Time", "Level")
    
    assert len(df) == 2
    # ENDRING: Sjekker nå 'Test.Level' i stedet for hardkodet 'ch1'
    assert df['Test.Level'].iloc[0] == 10.5  
    
    # Sjekk at 10. mai ble lest riktig (ikke 5. oktober)
    assert df['Datetime'].iloc[0].day == 10 
    assert df['Datetime'].iloc[0].month == 5

def test_les_engelsk_csv_med_metadata(tmp_path):
    """
    Tester at vi klarer å lese en 'Engelsk/TAP' CSV-fil.
    - Komma som skille
    - Punktum som desimal
    - Datoformat: YYYY/MM/DD (år først)
    """
    filnavn = tmp_path / "engelsk_logg.csv"
    innhold = """Logger ID: 999
Some Info: ...
Date,Time,Value
2024/05/10,12:00:00,10.5
2024/05/11,13:00:00,11.2
"""
    lag_csv_fil(filnavn, innhold)
    
    df = last_og_rens_data(filnavn, "Test2", "Date", "Time", "Value")
    
    assert len(df) == 2
    # ENDRING: Sjekker 'Test2.Value'
    assert df['Test2.Value'].iloc[0] == 10.5
    assert df['Datetime'].iloc[0].year == 2024
    assert df['Datetime'].iloc[0].month == 5
    assert df['Datetime'].iloc[0].day == 10

def test_les_excel_med_metadata(tmp_path):
    """
    Tester at vi finner headeren selv om den ligger langt nede i Excel-arket.
    """
    filnavn = tmp_path / "rotete.xlsx"
    
    # Vi lager en DataFrame som ser ut som et rotete Excel-ark
    data = [
        ["Prosjekt:", "Hemmelig"],
        ["", ""],
        ["Dato", "Tid", "Måling"], # Header er her (rad 2 / index 2)
        ["2024-01-01", "12:00:00", 500]
    ]
    df_raw = pd.DataFrame(data)
    df_raw.to_excel(filnavn, index=False, header=False)
    
    # Prøv å lese den
    df = last_og_rens_data(filnavn, "ExcelTest", "Dato", "Tid", "Måling")
    
    assert not df.empty
    # ENDRING: Sjekker 'ExcelTest.Måling'
    assert df['ExcelTest.Måling'].iloc[0] == 500

# ==============================================================================
#   INTEGRASJONSTESTER (Krever ekte filer i tests/data/)
# ==============================================================================

@pytest.mark.skipif(not os.path.exists("tests/data/Baro.xlsx"), reason="Mangler fil")
def test_laste_ekte_baro_fil():
    filsti = "tests/data/Baro.xlsx"
    df = last_og_rens_data(filsti, "Baro", "Date5", "Time6", "ch1")
    assert not df.empty
    assert 'Datetime' in df.columns
    # Denne vil hete 'Baro.ch1' fordi vi ba om 'ch1', så det er OK.

@pytest.mark.skipif(not os.path.exists("tests/data/Laksemyra_1.xlsx"), reason="Mangler fil")
def test_laste_ekte_laksemyra_fil():
    filsti = "tests/data/Laksemyra_1.xlsx"
    df = last_og_rens_data(filsti, "Laks", "Date5", "Time6", "ch1")
    assert not df.empty