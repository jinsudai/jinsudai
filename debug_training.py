import sys
sys.path.insert(0, 'src')

import pandas as pd
from ml.utils.models.model import train_model
from ml.utils.data.data_preparation import split_data
from ml.config import load_config

# Load config
config = load_config(config_name="consumption")
print(f"Model type from config: {config.get('model', {}).get('model_type')}")

# Load features
features_path = 'data/processed/test_features_from_pipeline.parquet'
df = pd.read_parquet(features_path)
print(f"Features shape: {df.shape}")
print(f"Columns: {list(df.columns)}")

# Get target column
target_column = config.get('data', {}).get('target_column', 'Valeur')
print(f"Target column: {target_column}")

# Split data
X_train, X_test, y_train, y_test = split_data(
    df,
    test_size=0.2,
    random_state=42,
    target_column=target_column
)
print(f"X_train shape: {X_train.shape}, y_train shape: {y_train.shape}")
print(f"X_test shape: {X_test.shape}, y_test shape: {y_test.shape}")

# Try to train
model_type = config.get('model', {}).get('model_type', 'random_forest')
print(f"\nAttempting to train with model_type: {model_type}")

model = train_model(X_train, y_train, model_type=model_type)

if model is None:
    print("ERROR: train_model returned None")
else:
    print(f"SUCCESS: Model trained: {type(model).__name__}")
