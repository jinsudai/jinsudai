"""
Airflow DAG pour le pipeline de consommation électrique.

Ce DAG correspond au flow Prefect consumption_full_pipeline.
Il orchestre le pipeline complet : données brutes → modèle en production.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ml.workflows.consumption_flow import consumption_full_pipeline

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=15),
}

def run_consumption_pipeline(**context):
    """Exécute le pipeline complet de consommation."""
    params = context.get('params', {})
    
    result = consumption_full_pipeline(
        start_date=params.get('start_date', '2024-01-01'),
        end_date=params.get('end_date', '2024-01-31'),
        raw_path=params.get('raw_path', 'data/templates/raw_template.csv'),
        output_dir=params.get('output_dir', 'data/processed/')
    )
    
    return result

with DAG(
    'consumption_full_pipeline',
    default_args=default_args,
    description='Pipeline complet : données brutes → modèle en production',
    schedule='0 3 * * 0',  # Tous les dimanches à 3h du matin
    catchup=False,
    max_active_runs=1,
    tags=['consumption', 'training', 'ml'],
    params={
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'raw_path': 'data/templates/raw_template.csv',
        'output_dir': 'data/processed/'
    }
) as dag:
    
    consumption_task = PythonOperator(
        task_id='run_consumption_pipeline',
        python_callable=run_consumption_pipeline,
    )
