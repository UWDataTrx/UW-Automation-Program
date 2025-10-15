from config.config_loader import ConfigLoader
import pandas as pd

fp = ConfigLoader.load_file_paths()
net = pd.read_csv(fp['n_disrupt'], usecols=['pharmacy_nabp', 'pharmacy_npi', 'pharmacy_is_excluded'], dtype=str)
test_nabp = '1504023'
match = net[net['pharmacy_nabp'].str.strip().str.upper() == test_nabp]
print(f'Looking for NABP: {test_nabp}')
print(f'Matches found: {len(match)}')
if len(match) > 0:
    print('\nMatch details:')
    print(match)
else:
    print('\nNo match found!')
    print('\nFirst 10 NABPs in network (uppercased):')
    print(net['pharmacy_nabp'].str.strip().str.upper().head(10).tolist())
