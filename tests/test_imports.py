#!/usr/bin/env python
"""Script de test des imports."""
import sys
sys.path.insert(0, 'src')

print("Testing imports...")

# Test 1: consumption_preparer
try:
    from ml.consumption.consumption_preparer import ConsumptionDataPreparer
    print("[OK] consumption_preparer")
except Exception as e:
    print(f"[FAIL] consumption_preparer: {e}")

# Test 2: consumption_tasks
try:
    from ml.consumption.consumption_tasks import prepare_consumption_features_task
    print("[OK] consumption_tasks")
except Exception as e:
    print(f"[FAIL] consumption_tasks: {e}")

# Test 3: training_tasks
try:
    from ml.consumption.training_tasks import train_consumption_model_task
    print("[OK] training_tasks")
except Exception as e:
    print(f"[FAIL] training_tasks: {e}")

# Test 4: holidays_tasks
try:
    from ml.connectors.holidays.holidays_tasks import generate_holidays_parquet_task
    print("[OK] holidays_tasks")
except Exception as e:
    print(f"[FAIL] holidays_tasks: {e}")

# Test 5: weather_tasks (désactivé - fichier déplacé vers _disabled)
# try:
#     from ml.connectors.weather.weather_tasks import generate_weather_parquet_task
#     print("[OK] weather_tasks")
# except Exception as e:
#     print(f"[FAIL] weather_tasks: {e}")

# Test 6: workflows
try:
    from ml.workflows.consumption_flow import consumption_full_pipeline
    print("[OK] consumption_flow")
except Exception as e:
    print(f"[FAIL] consumption_flow: {e}")

# Test 7: config
try:
    from ml.config import load_config
    print("[OK] ml.config")
except Exception as e:
    print(f"[FAIL] ml.config: {e}")

print("\nAll tests completed!")
