"""
Airflow DAG pour le pipeline de mise à jour des valeurs réelles.

Ce DAG correspond au flow Prefect actual_values_full_pipeline.
Il orchestre la mise à jour des valeurs réelles : configuration → récupération veille → génération aléatoire → mise à jour BD.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ml.workflows.actual_values_flow import actual_values_full_pipeline

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def run_actual_values_pipeline(**context):
    """Exécute le pipeline de mise à jour des valeurs réelles."""
    params = context.get('params', {})
    
    result = actual_values_full_pipeline(
        db_uri=params.get('db_uri')
    )
    
    return result

with DAG(
    'actual_values_full_pipeline',
    default_args=default_args,
    description='Pipeline complet de mise à jour des valeurs réelles : configuration → récupération veille → génération aléatoire → mise à jour BD',
    schedule='0 7 * * *',  # Tous les jours à 7h
    catchup=False,
    max_active_runs=1,
    tags=['actual-values', 'data-update', 'monitoring'],
    params={
        'db_uri': None
    }
) as dag:
    
    actual_values_task = PythonOperator(
        task_id='run_actual_values_pipeline',
        python_callable=run_actual_values_pipeline,
    )
