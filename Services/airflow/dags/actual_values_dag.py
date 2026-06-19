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

from ml.utils.pipelines.Actual_values_pipeline import ActualValuesPipeline
from ml.config import load_config

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def setup_actual_values_task(**context):
    """Configure le pipeline de valeurs réelles (Base de données)."""
    params = context.get('params', {})
    
    # Charger la config pour l'URI de la base de données
    config = load_config(config_name="consumption")
    db_uri = params.get('db_uri') or config.get('database', {}).get('uri')
    
    if not db_uri:
        raise ValueError("URI de base de données requise")
    
    # Stocker l'URI dans XCom pour les tâches suivantes
    context['task_instance'].xcom_push(key='db_uri', value=db_uri)
    
    # Créer et configurer le pipeline
    pipeline = ActualValuesPipeline(db_uri)
    
    if not pipeline.setup():
        raise Exception("Échec de la configuration du pipeline")
    
    return {"status": "setup_complete"}

def get_previous_day_predictions_task(**context):
    """Récupère les prédictions de la veille."""
    db_uri = context['task_instance'].xcom_pull(task_ids='setup_actual_values', key='db_uri')
    
    pipeline = ActualValuesPipeline(db_uri)
    pipeline.setup()
    
    if not pipeline.get_previous_day_predictions():
        raise Exception("Aucune prédiction trouvée pour la veille")
    
    return {"status": "predictions_retrieved", "count": len(pipeline.previous_day_predictions)}

def generate_random_actual_values_task(**context):
    """Génère des valeurs aléatoires pour les prédictions de la veille."""
    db_uri = context['task_instance'].xcom_pull(task_ids='setup_actual_values', key='db_uri')
    
    pipeline = ActualValuesPipeline(db_uri)
    pipeline.setup()
    pipeline.get_previous_day_predictions()
    
    if not pipeline.generate_random_actual_values():
        raise Exception("Échec de la génération des valeurs aléatoires")
    
    return {"status": "values_generated", "count": pipeline.updated_count}

def verify_updates_task(**context):
    """Vérifie les mises à jour effectuées."""
    db_uri = context['task_instance'].xcom_pull(task_ids='setup_actual_values', key='db_uri')
    
    pipeline = ActualValuesPipeline(db_uri)
    pipeline.setup()
    pipeline.get_previous_day_predictions()
    pipeline.generate_random_actual_values()
    
    updated_predictions = pipeline.verify_updates()
    
    return {"status": "verified", "updated_count": pipeline.updated_count}

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
    
    # Définir les tâches individuelles
    setup_task = PythonOperator(
        task_id='setup_actual_values',
        python_callable=setup_actual_values_task,
    )
    
    get_predictions_task = PythonOperator(
        task_id='get_previous_day_predictions',
        python_callable=get_previous_day_predictions_task,
    )
    
    generate_values_task = PythonOperator(
        task_id='generate_random_actual_values',
        python_callable=generate_random_actual_values_task,
    )
    
    verify_task = PythonOperator(
        task_id='verify_updates',
        python_callable=verify_updates_task,
    )
    
    # Définir les dépendances entre les tâches
    setup_task >> get_predictions_task >> generate_values_task >> verify_task
