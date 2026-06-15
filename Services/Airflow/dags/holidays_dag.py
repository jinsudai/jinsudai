"""
Airflow DAG pour la génération annuelle du fichier holidays.parquet.

Ce DAG correspond au flow Prefect holidays_annual_pipeline.
Il génère un fichier Parquet combinant vacances scolaires et jours fériés pour une année complète.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ml.workflows.holidays_flow import holidays_annual_pipeline

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def run_holidays_generation(**context):
    """Exécute le pipeline de génération des holidays."""
    params = context.get('params', {})
    
    # Déterminer l'année : utiliser l'année en cours ou celle passée en paramètre
    year = params.get('year', datetime.now().year)
    
    result = holidays_annual_pipeline(
        year=year,
        output_dir=params.get('output_dir', 'data/processed/'),
        zone=params.get('zone', 'C')
    )
    
    return result

with DAG(
    'holidays_annual_pipeline',
    default_args=default_args,
    description='Génère le fichier holidays.parquet pour une année complète',
    schedule='0 0 1 1 *',  # 1er janvier de chaque année
    catchup=False,
    max_active_runs=1,
    tags=['holidays', 'annual', 'data-generation'],
    params={
        'year': None,  # Si None, utilise l'année en cours
        'output_dir': 'data/processed/',
        'zone': 'C'
    }
) as dag:
    
    holidays_task = PythonOperator(
        task_id='generate_holidays',
        python_callable=run_holidays_generation,
    )
