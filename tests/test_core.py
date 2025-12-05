import pytest
import pandas as pd
import os
from sensorplot.core import last_og_rens_data, vask_data

# ==============================================================================
#   ENHETSTESTER (Tester logikk med falske data)
# ==============================================================================

def test_vask_data_fjerner_stoy():
    """
    Sjekker at ekstreme verdier blir fjernet.
    Vi bruker z_score=1.0 her fordi datasettet er veldig lite (10 punkter).
    """
    data = {
        'Datetime': pd.date_range(start='1/1/2024', periods=10),
        # Vi legger inn 10-tall som "normalen", og +/- 100 som støy
        'Resultat': [10, 10, 10, 10, 10, 10, 10, 10, 100, -100] 
    }
    df = pd.DataFrame(data)
    
    # Kaller vask_data. Forventer at 2 punkter fjernes (+100 og -100)
    df_vasket, antall_fjernet = vask_data(df, 'Resultat', z_score=1.0)
    
    assert antall_fjernet == 2
    assert len(df_vasket) == 8
    assert df_vasket['Resultat'].max() == 10  # Maks skal nå være 10, ikke 100

def test_last_data_egendefinerte_kolonner(tmp_path):
    """
    Tester at vi kan lese en fil med helt andre kolonnenavn
    enn standarden (f.eks 'MinDato', 'Klokke', 'Nivå').
    """
    # 1. Lag en midlertidig Excel-fil
    d = {
        'MinDato': ['2024-01-01', '2024-01-02'],
        'Klokke': ['12:00:00', '13:00:00'],
        'Nivå': [5.5, 6.0],
        'Annet': ['A', 'B']
    }
    df = pd.DataFrame(d)
    filsti = tmp_path / "test_custom.xlsx"
    df.to_excel(filsti, index=False)

    # 2. Kall funksjonen med de nye navnene
    # Alias="Test", Date="MinDato", Time="Klokke", Data="Nivå"
    resultat = last_og_rens_data(str(filsti), "Test", "MinDato", "Klokke", "Nivå")

    # 3. Sjekk at data ble lest og omdøpt korrekt
    assert not resultat.empty
    assert "Test.ch1" in resultat.columns  # Skal alltid omdøpes til Alias.ch1 internt
    assert len(resultat) == 2
    assert resultat['Test.ch1'].iloc[0] == 5.5

def test_last_data_samlet_dato_tid(tmp_path):
    """
    Tester at vi kan lese en fil der dato og tid er i én kolonne (Timestamp),
    ved å sette tidskolonne til None.
    """
    d = {
        'Tidsstempel': ['2024-01-01 10:00', '2024-01-01 11:00'],
        'Temp': [20, 21]
    }
    df = pd.DataFrame(d)
    filsti = tmp_path / "test_timestamp.xlsx"
    df.to_excel(filsti, index=False)

    # Kall med time_col=None
    resultat = last_og_rens_data(str(filsti), "TempSensor", "Tidsstempel", None, "Temp")

    assert "TempSensor.ch1" in resultat.columns
    assert resultat['Datetime'].iloc[0].hour == 10


# ==============================================================================
#   INTEGRASJONSTESTER (Tester med dine ekte filer)
#   Disse kjøres KUN hvis du har lagt filene i 'tests/data/'
# ==============================================================================

@pytest.mark.skipif(not os.path.exists("tests/data/Baro.xlsx"), reason="Mangler Baro.xlsx i tests/data")
def test_laste_ekte_baro_fil():
    """Prøver å laste Baro.xlsx med standardkolonner (Date5, Time6, ch1)."""
    filsti = "tests/data/Baro.xlsx"
    alias = "TestBaro"
    
    # Vi sender inn standardnavnene eksplisitt
    df = last_og_rens_data(filsti, alias, "Date5", "Time6", "ch1")
    
    assert not df.empty
    assert 'Datetime' in df.columns
    assert f'{alias}.ch1' in df.columns
    assert df['Datetime'].is_monotonic_increasing

@pytest.mark.skipif(not os.path.exists("tests/data/Laksemyra 1.xlsx"), reason="Mangler Laksemyra filen")
def test_laste_ekte_laksemyra_fil():
    filsti = "tests/data/Laksemyra 1.xlsx"
    
    df = last_og_rens_data(filsti, "Laks", "Date5", "Time6", "ch1")
    
    assert not df.empty
    assert "Laks.ch1" in df.columns