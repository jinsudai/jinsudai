"""
Airflow DAG pour déclencher le pipeline d'ingestion des actuals via GitHub Action.

Ce DAG:
- Déclenche le workflow GitHub Action 1_actuals_ingestion_pipeline.yml
- Attend que le workflow se termine
- Marque la tâche comme réussie si le workflow GitHub réussit
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor
import sys
import os

# Ajouter le dossier utils au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))
from github_action_helper import trigger_github_action, check_github_action_status

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'actuals_ingestion_pipeline',
    default_args=default_args,
    description='Déclenche le pipeline d\'ingestion des actuals via GitHub Action',
    schedule='30 0 * * *',  # Tous les jours à 0h30
    catchup=False,
    tags=['ingestion', 'actuals', 'github-action'],
) as dag:
    
    trigger_task = PythonOperator(
        task_id='trigger_github_action',
        python_callable=trigger_github_action,
        op_kwargs={'github_workflow': '1_actuals_ingestion_pipeline.yml'},
    )
    
    wait_task = PythonSensor(
        task_id='wait_for_github_action',
        python_callable=check_github_action_status,
        op_kwargs={'github_workflow': '1_actuals_ingestion_pipeline.yml'},
        poke_interval=30,
        timeout=3600,
        mode='poke',
    )
    
    trigger_task >> wait_task
