"""
Airflow DAG pour le pipeline de prédiction.

Ce DAG correspond au flow Prefect prediction_full_pipeline.
Il orchestre le pipeline complet de prédiction : configuration → modèle → données → prédictions → stockage.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ml.utils.pipelines.Prediction_pipeline import PredictionPipeline
from ml.config import load_config

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

def run_prediction_pipeline(**context):
    """Exécute le pipeline complet de prédiction."""
    params = context.get('params', {})
    
    # Charger la config pour les valeurs par défaut
    config = load_config(config_name="consumption")
    
    mlflow_uri = params.get('mlflow_uri') or config.get('mlflow', {}).get('tracking_uri', 'http://localhost:5000')
    experiment_name = params.get('experiment_name') or config.get('mlflow', {}).get('experiment_name', 'consumption_experiment')
    db_uri = params.get('db_uri') or config.get('database', {}).get('uri')
    
    # Créer et configurer le pipeline
    pipeline = PredictionPipeline(mlflow_uri, experiment_name, db_uri)
    
    if not pipeline.setup():
        raise Exception("Échec de la configuration du pipeline")
    
    # Charger le modèle
    model_name = params.get('model_name', 'consumption_model')
    alias_prod = params.get('alias_prod', 'prod')
    
    if not pipeline.load_model(model_name, alias_prod=alias_prod):
        raise Exception(f"Échec du chargement du modèle {model_name}")
    
    # Générer les données d'inférence
    n_days = params.get('n_days', 3)
    n_samples_per_day = params.get('n_samples_per_day', 48)
    
    pipeline.generate_inference_data(n_days=n_days, n_samples_per_day=n_samples_per_day)
    
    # Préparer les features
    pipeline.prepare_features()
    
    # Exécuter les prédictions
    pipeline.run_predictions()
    
    # Stocker si base de données disponible
    if db_uri:
        pipeline.store_predictions()
    
    return {"status": "success", "model": model_name}

with DAG(
    'prediction_full_pipeline',
    default_args=default_args,
    description='Pipeline complet de prédiction : configuration → modèle → données → prédictions → stockage',
    schedule='0 8 * * *',  # Tous les jours à 8h
    catchup=False,
    max_active_runs=1,
    tags=['prediction', 'ml', 'inference'],
    params={
        'model_name': 'consumption_model',
        'mlflow_uri': None,
        'experiment_name': None,
        'db_uri': None,
        'n_days': 3,
        'n_samples_per_day': 48,
        'feature_columns': None,
        'alias_prod': 'prod',
        'use_existing_data': False,
        'df_inference_path': None
    }
) as dag:
    
    prediction_task = PythonOperator(
        task_id='run_prediction_pipeline',
        python_callable=run_prediction_pipeline,
    )
