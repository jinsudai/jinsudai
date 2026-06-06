import sys
sys.path.insert(0, 'src')
from ml.utils.data.data_loader import load_data

data = load_data('data/templates/training_template.csv')
if data is not None:
    print('Shape:', data.shape)
    print('Columns:', list(data.columns))
    print('First row:')
    print(data.iloc[0])
else:
    print('Data is None')
