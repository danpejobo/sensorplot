import pytest
import pandas as pd
import os
from sensorplot.core import last_og_rens_data, vask_data

# --- ENHETSTESTER (Mock data) ---

def test_vask_data_fjerner_stoy():
    """Sjekker at ekstreme verdier blir fjernet (Z-score)."""
    data = {
        'Datetime': pd.date_range(start='1/1/2024', periods=10),
        # Vi bruker symmetriske utliggere (+100 og -100) rundt en kjerne av 10-tall.
        'Resultat': [10, 10, 10, 10, 10, 10, 10, 10, 100, -100] 
    }
    df = pd.DataFrame(data)
    
    # ENDRET: Vi senker Z-score til 1.0 for denne testen.
    # Fordi datasettet er så lite, blåser utliggerne opp standardavviket.
    # Ved å bruke z=1 strammer vi inn grensen slik at +/- 100 garantert ryker.
    df_vasket, antall_fjernet = vask_data(df, 'Resultat', z_score=1.0)
    
    assert antall_fjernet == 2
    assert len(df_vasket) == 8
    assert df_vasket['Resultat'].max() == 10

def test_last_data_egendefinerte_kolonner(tmp_path):
    """
    Tester at vi kan lese en fil med helt andre kolonnenavn
    enn standarden (f.eks 'MinDato', 'Klokke', 'Nivå').
    """
    d = {
        'MinDato': ['2024-01-01', '2024-01-02'],
        'Klokke': ['12:00:00', '13:00:00'],
        'Nivå': [5.5, 6.0],
        'Uvesentlig': ['A', 'B']
    }
    df = pd.DataFrame(d)
    filsti = tmp_path / "test_custom.xlsx"
    df.to_excel(filsti, index=False)

    resultat = last_og_rens_data(str(filsti), "Test", "MinDato", "Klokke", "Nivå")

    assert not resultat.empty
    assert "Test.ch1" in resultat.columns
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

    resultat = last_og_rens_data(str(filsti), "TempSensor", "Tidsstempel", None, "Temp")

    assert "TempSensor.ch1" in resultat.columns
    assert resultat['Datetime'].iloc[0].hour == 10

# --- INTEGRASJONSTESTER (Ekte filer) ---

@pytest.mark.skipif(not os.path.exists("tests/data/Baro.xlsx"), reason="Mangler Baro.xlsx i tests/data")
def test_laste_ekte_baro_fil():
    filsti = "tests/data/Baro.xlsx"
    alias = "TestBaro"
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