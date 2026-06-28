"""
Airflow DAG pour déclencher le pipeline d'entraînement via GitHub Action.

Ce DAG:
- Vérifie si le training est nécessaire (drift ou dernier training > 1 jour)
- Déclenche le workflow GitHub Action 3_training-pipeline.yml si nécessaire
- Attend que le workflow se termine
- Marque la tâche comme réussie si le workflow GitHub réussit
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.python import BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.sensors.python import PythonSensor
import sys
import os

# Ajouter le dossier utils au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))
from github_action_helper import trigger_github_action, check_github_action_status, should_trigger_training

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
    'training_pipeline',
    default_args=default_args,
    description='Déclenche le pipeline d\'entraînement via GitHub Action (conditionnel)',
    schedule=None,  # Désactivé - orchestré par master_pipeline
    catchup=False,
    tags=['training', 'github-action'],
) as dag:
    
    # Vérifier si le training est nécessaire
    check_training_needed = BranchPythonOperator(
        task_id='check_training_needed',
        python_callable=should_trigger_training,
    )
    
    # Tâche de training
    train_task = PythonOperator(
        task_id='train',
        python_callable=trigger_github_action,
        op_kwargs={'github_workflow': '3_run_training.yml'},
    )
    
    wait_task = PythonSensor(
        task_id='wait_for_github_action',
        python_callable=check_github_action_status,
        op_kwargs={'github_workflow': '3_run_training.yml'},
        poke_interval=30,
        timeout=3600,
        mode='poke',
    )
    
    # Tâche de skip
    skip_training = EmptyOperator(
        task_id='skip',
    )
    
    # Dépendances conditionnelles
    check_training_needed >> [train_task, skip_training]
    train_task >> wait_task
