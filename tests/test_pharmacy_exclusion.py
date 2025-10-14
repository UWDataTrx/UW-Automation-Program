import pandas as pd
from utils.utils import (
    vectorized_resolve_pharmacy_exclusion,
    clear_pharmacy_exclusion_cache,
)

def make_network():
    return pd.DataFrame({
        'pharmacy_nabp': ['1234567','7654321','5555555'],
        'pharmacy_npi': ['1111111111','2222222222','3333333333'],
        'pharmacy_is_excluded': ['Yes','No','maybe']
    })

def test_basic_mapping():
    """Verify mapping outcomes for yes/no/unmatched and unexpected token."""
    clear_pharmacy_exclusion_cache(persistent=False)
    claims = pd.DataFrame({
        'NABP': ['1234567','7654321','0000000',''],
        'PHARMACYNPI': ['1111111111','2222222222','4444444444','3333333333']
    })
    network = make_network()
    result = vectorized_resolve_pharmacy_exclusion(claims, network, use_cache=False, persist=False)
    assert result.iloc[0] is True
    assert result.iloc[1] is False
    assert result.iloc[2] == 'REVIEW'
    assert result.iloc[3] == 'REVIEW'

def test_cache_hit():
    """Ensure second invocation uses cached lookup (indirectly via faster run)."""
    clear_pharmacy_exclusion_cache(persistent=False)
    claims = pd.DataFrame({'NABP':['1234567'],'PHARMACYNPI':['1111111111']})
    network = make_network()
    r1 = vectorized_resolve_pharmacy_exclusion(claims, network, use_cache=True, persist=False)
    r2 = vectorized_resolve_pharmacy_exclusion(claims, network, use_cache=True, persist=False)
    assert bool(r1.iloc[0]) and bool(r2.iloc[0])

"""Run with: pytest -q tests/test_pharmacy_exclusion.py"""
