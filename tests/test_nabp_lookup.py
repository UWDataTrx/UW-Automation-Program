from config.config_loader import ConfigLoader
import pandas as pd

fp = ConfigLoader.load_file_paths()
net = pd.read_csv(fp['n_disrupt'], usecols=['pharmacy_nabp', 'pharmacy_npi', 'pharmacy_is_excluded'], dtype=str)

test_nabps = ['1825655', '1525798', '1462821']
for nabp in test_nabps:
    match = net[net['pharmacy_nabp'].str.strip().str.upper() == nabp]
    excluded_vals = match['pharmacy_is_excluded'].tolist() if len(match) > 0 else 'N/A'
    print(f'NABP {nabp}: {len(match)} matches, excluded={excluded_vals}')
