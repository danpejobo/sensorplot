import pytest
import pandas as pd
import os
from unittest.mock import MagicMock
from sensorplot.cli import process_single_series

# En enkel Mock-klasse for å simulere argumentene fra argparse
class MockArgs:
    def __init__(self):
        self.col_date = 'Date5'
        self.col_data = 'ch1'
        self.clean_threshold = None 

def lag_dummy_excel(path, filename, date_start, values):
    """Hjelpefunksjon for å lage Excel-filer til testing."""
    # Lager unike tidspunkter (12:00, 13:00...) for å unngå merge-feil
    dates = pd.date_range(start=f"{date_start} 12:00", periods=len(values), freq='h')
    
    data = {
        'Date5': dates.date,
        'Time6': dates.time, 
        'ch1': values
    }
    df = pd.DataFrame(data)
    full_path = path / filename
    df.to_excel(full_path, index=False)
    return str(full_path)

def test_independent_pairs(tmp_path):
    """
    TESTER SCENARIO: To helt uavhengige sett.
    Sett 1: Laks1 (Data) - Baro1 (Korreksjon)
    Sett 2: Laks2 (Data) - Baro2 (Korreksjon)
    """
    
    # 1. GENERER DATA (3 punkter per fil)
    l1_path = lag_dummy_excel(tmp_path, "Laks1.xlsx", "2024-01-01", [100, 100, 100])
    b1_path = lag_dummy_excel(tmp_path, "Baro1.xlsx", "2024-01-01", [10, 10, 10])
    l2_path = lag_dummy_excel(tmp_path, "Laks2.xlsx", "2024-01-01", [50, 50, 50])
    b2_path = lag_dummy_excel(tmp_path, "Baro2.xlsx", "2024-01-01", [5, 5, 5])
    
    files_dict = {
        "L1": l1_path,
        "B1": b1_path,
        "L2": l2_path,
        "B2": b2_path
    }
    
    args = MockArgs()
    loaded_dfs_cache = {} 
    use_time_col = 'Time6'

    # ---------------------------------------------------------
    # 2. PROSESSER SERIE 1 ("Laks1 - Baro1")
    # ---------------------------------------------------------
    res1 = process_single_series(
        series_label="Lokasjon 1",
        formula="L1.ch1 - B1.ch1",
        all_files_dict=files_dict,
        loaded_dfs_cache=loaded_dfs_cache,
        args=args,
        use_time_col=use_time_col
    )
    
    # BRUKER .df (Dataclass)
    vals1 = res1.df['Resultat'].values
    assert vals1[0] == 90.0
    assert "L1" in loaded_dfs_cache
    assert "B1" in loaded_dfs_cache

    # ---------------------------------------------------------
    # 3. PROSESSER SERIE 2 ("Laks2 - Baro2")
    # ---------------------------------------------------------
    res2 = process_single_series(
        series_label="Lokasjon 2",
        formula="L2.ch1 - B2.ch1",
        all_files_dict=files_dict,
        loaded_dfs_cache=loaded_dfs_cache,
        args=args,
        use_time_col=use_time_col
    )
    
    # BRUKER .df (Dataclass)
    vals2 = res2.df['Resultat'].values
    assert vals2[0] == 45.0
    
    assert "L2" in loaded_dfs_cache
    assert "B2" in loaded_dfs_cache
    assert len(loaded_dfs_cache) == 4

    print("\nTest 'Independent Pairs' OK: Klarte å skille L1/B1 og L2/B2.")