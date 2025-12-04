import pytest
import pandas as pd
import os
from sensorplot.core import last_og_rens_data, vask_data

# 1. Enhetstest av logikk (trenger ikke filene dine)
def test_vask_data_fjerner_stoy():
    """Sjekker at ekstreme verdier blir fjernet."""
    data = {
        'Datetime': pd.date_range(start='1/1/2024', periods=10),
        'Resultat': [10, 10, 10, 10, 10, 1000, 10, 10, 10, -500] # To ekstreme verdier
    }
    df = pd.DataFrame(data)
    
    # Kjør vask med Z-score 2 (strenge krav)
    df_vasket, antall_fjernet = vask_data(df, 'Resultat', z_score=2)
    
    assert antall_fjernet == 2
    assert len(df_vasket) == 8
    assert df_vasket['Resultat'].max() == 10

# 2. Integrasjonstest med DINE filer
# Denne testen kjører kun hvis filene faktisk ligger i tests/data/
@pytest.mark.skipif(not os.path.exists("tests/data/Baro.xlsx"), reason="Mangler Baro.xlsx i tests/data")
def test_laste_ekte_fil():
    """Prøver å laste Baro.xlsx og sjekker formatet."""
    filsti = "tests/data/Baro.xlsx"
    alias = "TestBaro"
    
    df = last_og_rens_data(filsti, alias)
    
    # Sjekk at vi fikk data
    assert not df.empty
    # Sjekk at kolonnene er riktige
    assert 'Datetime' in df.columns
    assert f'{alias}.ch1' in df.columns
    # Sjekk at tidene er sortert
    assert df['Datetime'].is_monotonic_increasing

@pytest.mark.skipif(not os.path.exists("tests/data/Laksemyra 1.xlsx"), reason="Mangler Laksemyra filen")
def test_laksemyra_fil():
    filsti = "tests/data/Laksemyra 1.xlsx"
    df = last_og_rens_data(filsti, "Laks")
    assert not df.empty
    assert "Laks.ch1" in df.columns