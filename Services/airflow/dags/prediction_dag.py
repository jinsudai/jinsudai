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

def setup_prediction_task(**context):
    """Configure le pipeline de prédiction (MLflow + Base de données)."""
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
    
    # Stocker le pipeline dans XCom pour les tâches suivantes
    context['task_instance'].xcom_push(key='pipeline_config', value={
        'mlflow_uri': mlflow_uri,
        'experiment_name': experiment_name,
        'db_uri': db_uri,
        'model_name': params.get('model_name', 'consumption_model'),
        'alias_prod': params.get('alias_prod', 'prod'),
        'n_days': params.get('n_days', 3),
        'n_samples_per_day': params.get('n_samples_per_day', 48)
    })
    
    return {"status": "setup_complete"}

def load_model_task(**context):
    """Charge le modèle en production depuis MLflow."""
    params = context.get('params', {})
    pipeline_config = context['task_instance'].xcom_pull(task_ids='setup_prediction', key='pipeline_config')
    
    # Recréer le pipeline avec la config
    pipeline = PredictionPipeline(
        pipeline_config['mlflow_uri'],
        pipeline_config['experiment_name'],
        pipeline_config['db_uri']
    )
    pipeline.setup()
    
    model_name = pipeline_config['model_name']
    alias_prod = pipeline_config['alias_prod']
    
    if not pipeline.load_model(model_name, alias_prod=alias_prod):
        raise Exception(f"Échec du chargement du modèle {model_name}")
    
    return {"status": "model_loaded", "model_name": model_name}

def generate_inference_data_task(**context):
    """Génère les données d'inférence."""
    pipeline_config = context['task_instance'].xcom_pull(task_ids='setup_prediction', key='pipeline_config')
    
    pipeline = PredictionPipeline(
        pipeline_config['mlflow_uri'],
        pipeline_config['experiment_name'],
        pipeline_config['db_uri']
    )
    pipeline.setup()
    pipeline.load_model(pipeline_config['model_name'], alias_prod=pipeline_config['alias_prod'])
    
    n_days = pipeline_config['n_days']
    n_samples_per_day = pipeline_config['n_samples_per_day']
    
    if not pipeline.generate_data(n_days=n_days, n_samples_per_day=n_samples_per_day):
        raise Exception("Échec de la génération des données d'inférence")
    
    return {"status": "data_generated", "n_days": n_days, "n_samples": n_days * n_samples_per_day}

def prepare_features_task(**context):
    """Prépare les features à partir des données d'inférence."""
    pipeline_config = context['task_instance'].xcom_pull(task_ids='setup_prediction', key='pipeline_config')
    
    pipeline = PredictionPipeline(
        pipeline_config['mlflow_uri'],
        pipeline_config['experiment_name'],
        pipeline_config['db_uri']
    )
    pipeline.setup()
    pipeline.load_model(pipeline_config['model_name'], alias_prod=pipeline_config['alias_prod'])
    pipeline.generate_data(n_days=pipeline_config['n_days'], n_samples_per_day=pipeline_config['n_samples_per_day'])
    
    df_features = pipeline.prepare_features()
    
    if df_features is None:
        raise Exception("Échec de la préparation des features")
    
    return {"status": "features_prepared", "n_features": len(df_features)}

def run_predictions_task(**context):
    """Exécute les prédictions."""
    pipeline_config = context['task_instance'].xcom_pull(task_ids='setup_prediction', key='pipeline_config')
    
    pipeline = PredictionPipeline(
        pipeline_config['mlflow_uri'],
        pipeline_config['experiment_name'],
        pipeline_config['db_uri']
    )
    pipeline.setup()
    pipeline.load_model(pipeline_config['model_name'], alias_prod=pipeline_config['alias_prod'])
    pipeline.generate_data(n_days=pipeline_config['n_days'], n_samples_per_day=pipeline_config['n_samples_per_day'])
    pipeline.prepare_features()
    
    if not pipeline.run_predictions():
        raise Exception("Échec de l'exécution des prédictions")
    
    return {"status": "predictions_complete"}

def store_predictions_task(**context):
    """Stocke les prédictions en base de données."""
    pipeline_config = context['task_instance'].xcom_pull(task_ids='setup_prediction', key='pipeline_config')
    
    pipeline = PredictionPipeline(
        pipeline_config['mlflow_uri'],
        pipeline_config['experiment_name'],
        pipeline_config['db_uri']
    )
    pipeline.setup()
    pipeline.load_model(pipeline_config['model_name'], alias_prod=pipeline_config['alias_prod'])
    pipeline.generate_data(n_days=pipeline_config['n_days'], n_samples_per_day=pipeline_config['n_samples_per_day'])
    pipeline.prepare_features()
    pipeline.run_predictions()
    
    if pipeline_config['db_uri']:
        if not pipeline.store_predictions():
            raise Exception("Échec du stockage des prédictions")
        return {"status": "stored"}
    else:
        return {"status": "skipped", "reason": "no_db_uri"}

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
    
    # Définir les tâches individuelles
    setup_task = PythonOperator(
        task_id='setup_prediction',
        python_callable=setup_prediction_task,
    )
    
    load_model_task_op = PythonOperator(
        task_id='load_model',
        python_callable=load_model_task,
    )
    
    generate_data_task_op = PythonOperator(
        task_id='generate_inference_data',
        python_callable=generate_inference_data_task,
    )
    
    prepare_features_task_op = PythonOperator(
        task_id='prepare_features',
        python_callable=prepare_features_task,
    )
    
    run_predictions_task_op = PythonOperator(
        task_id='run_predictions',
        python_callable=run_predictions_task,
    )
    
    store_predictions_task_op = PythonOperator(
        task_id='store_predictions',
        python_callable=store_predictions_task,
    )
    
    # Définir les dépendances entre les tâches
    setup_task >> load_model_task_op >> generate_data_task_op >> prepare_features_task_op >> run_predictions_task_op >> store_predictions_task_op
