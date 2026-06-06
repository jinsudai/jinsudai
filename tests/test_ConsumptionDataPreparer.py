import os
import sys
os.environ['ENV'] = 'dev'
sys.path.insert(0, 'src')

from ml.consumption.consumption_preparer import ConsumptionDataPreparer
from ml.config import load_config
import warnings
warnings.filterwarnings('ignore')

# Charger la config comme dans le notebook
config = load_config(config_name="consumption")
print('Config charged')
print('raw_path:', config.get('data', {}).get('raw_path'))
print('train_path:', config.get('data', {}).get('train_path'))

preparer = ConsumptionDataPreparer()
try:
    features_df = preparer.prepare()
    print(f'✅ Success! {len(features_df)} records')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
