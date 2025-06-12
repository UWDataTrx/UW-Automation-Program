import pytest
import pandas as pd
from utils import load_file_paths, safe_read_excel, standardize_pharmacy_ids, merge_with_network

def test_load_file_paths():
    paths = load_file_paths('file_paths.json')
    assert isinstance(paths, dict)
    assert 'reprice' in paths

def test_safe_read_excel():
    paths = load_file_paths('file_paths.json')
    df = safe_read_excel(paths['reprice'])
    assert isinstance(df, pd.DataFrame)

def test_standardize_pharmacy_ids():
    # Test with both NPI and NABP present
    df = pd.DataFrame({'PHARMACYNPI': [1234567890, None, ''], 'NABP': ['0987654', '1234567', '7654321']})
    result = standardize_pharmacy_ids(df)
    assert 'pharmacy_id' in result.columns
    assert result.loc[0, 'pharmacy_id'] == '1234567890'
    assert result.loc[1, 'pharmacy_id'] == '1234567'
    assert result.loc[2, 'pharmacy_id'] == '7654321'

def test_standardize_pharmacy_ids_nan():
    # Test with NaN values
    df = pd.DataFrame({'PHARMACYNPI': [float('nan')], 'NABP': [float('nan')]})
    result = standardize_pharmacy_ids(df)
    assert result['pharmacy_id'].iloc[0] == ''

def test_merge_with_network_partial_match():
    # Test merge with partial match
    df = pd.DataFrame({'pharmacy_id': ['123', '456']})
    network = pd.DataFrame({'pharmacy_npi': ['123', None], 'pharmacy_nabp': [None, '456'], 'pharmacy_is_excluded': [True, False]})
    merged = merge_with_network(df, network)
    assert 'pharmacy_is_excluded' in merged.columns
    assert merged.loc[merged['pharmacy_id'] == '123', 'pharmacy_is_excluded'].iloc[0] is True
    assert merged.loc[merged['pharmacy_id'] == '456', 'pharmacy_is_excluded'].iloc[0] is False

def test_merge_with_network_no_match():
    # Test merge with no match
    df = pd.DataFrame({'pharmacy_id': ['999']})
    network = pd.DataFrame({'pharmacy_npi': ['123'], 'pharmacy_nabp': ['456'], 'pharmacy_is_excluded': [True]})
    merged = merge_with_network(df, network)
    assert pd.isna(merged['pharmacy_is_excluded'].iloc[0])
    result = standardize_pharmacy_ids(df)
    assert 'pharmacy_id' in result.columns

def test_merge_with_network():
    df = pd.DataFrame({'pharmacy_id': ['123']})
    network = pd.DataFrame({'pharmacy_id': ['123'], 'pharmacy_is_excluded': [True]})
    result = merge_with_network(df, network)
    assert 'pharmacy_is_excluded' in result.columns
