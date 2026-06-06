"""
Test du pipeline consommation avec données de test.
"""
import sys
sys.path.insert(0, 'src')

from prefect import flow, task
from ml.consumption.consumption_tasks import prepare_consumption_features_task
from ml.consumption.training_tasks import (
    train_consumption_model_task,
    evaluate_consumption_model_task,
    monitor_consumption_model_task,
    stage_and_log_consumption_model_task
)

@flow(name="test-consumption-pipeline")
def test_consumption_pipeline():
    """Test du pipeline avec fichiers de test existants."""
    
    # Utiliser nos fichiers de test existants
    weather_path = 'data/processed/test_weather_full.parquet'
    holidays_path = 'data/processed/test_holidays_full.parquet'
    raw_path = 'data/templates/test_raw_consumption.csv'
    
    # 1. Préparer les features
    features_path = prepare_consumption_features_task(
        raw_path=raw_path,
        weather_path=weather_path,
        holidays_path=holidays_path,
        output_path='data/processed/test_features_from_pipeline.parquet'
    )
    
    print(f"[OK] Features prepared: {features_path}")
    
    # 2. Entraîner le modèle
    train_result = train_consumption_model_task(
        features_path=features_path,
        config_path='src/configs/consumption.yaml'
    )
    
    print(f"[OK] Model trained: {train_result['config']['model_type']}")
    print(f"   Metrics: {train_result['metrics']}")
    
    # 3. Évaluer le modèle
    import pandas as pd
    from ml.utils.data.data_preparation import split_data
    from ml.config import load_config
    
    config = load_config('src/configs/consumption.yaml')
    features_df = pd.read_parquet(features_path)
    target_column = config.get('data', {}).get('target_column', 'Valeur')
    
    _, X_test, _, y_test = split_data(
        features_df,
        test_size=0.2,
        random_state=42,
        target_column=target_column
    )
    
    eval_result = evaluate_consumption_model_task(
        model=train_result["model"],
        X_test=X_test,
        y_test=y_test,
        feature_names=list(X_test.columns)
    )
    
    print(f"[OK] Model evaluated: {eval_result['metrics']}")
    
    # 4. Monitoring
    # NE PAS enlever Horodate car AutoGluon a été entraîné avec
    X_train_full = features_df.drop(columns=[target_column])
    y_train_full = features_df[target_column]
    
    monitor_result = monitor_consumption_model_task(
        model=train_result["model"],
        X_train=X_train_full,
        X_test=X_test,
        y_train=y_train_full,
        y_test=y_test,
        feature_names=list(X_test.columns),
        problem_type="regression"
    )
    
    print(f"[OK] Model monitored")
    
    return {
        "status": "success",
        "features_path": features_path,
        "training": train_result,
        "evaluation": eval_result,
        "monitoring": monitor_result
    }

if __name__ == "__main__":
    result = test_consumption_pipeline()
    print(f"\n[SUCCESS] Pipeline test completed!")
    print(f"Status: {result['status']}")
