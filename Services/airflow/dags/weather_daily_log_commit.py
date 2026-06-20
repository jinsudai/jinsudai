"""
Airflow DAG pour ajouter des logs horodatés au pipeline WeatherDaily et les committer dans Git.

Ce DAG:
- Lit le fichier de log s'il existe (pipelines/WeatherDaily/weather_daily.log)
- Ajoute une ligne de log horodatée avec l'origine Airflow
- Commit le fichier dans Git
"""
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
import os

# Configuration du chemin du fichier de log
AIRFLOW_HOME = os.environ.get('AIRFLOW_HOME', '/opt/airflow')
LOG_FILE_PATH = os.path.join(AIRFLOW_HOME, 'logs', 'weather_daily.log')

def add_log_entry(**context):
    """
    Ajoute une entrée de log horodatée dans le fichier weather_daily.log.
    """
    execution_date = context.get('execution_date')
    timestamp = execution_date.strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] Airflow - weather_daily_log_commit_v2 - Pipeline WeatherDaily exécuté avec succès\n"
    
    # S'assurer que le répertoire existe
    log_dir = os.path.dirname(LOG_FILE_PATH)
    os.makedirs(log_dir, exist_ok=True)
    
    # Écrire le message (mode append)
    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write(log_message)
    
    return {"status": "success", "log_file": LOG_FILE_PATH}

def commit_log_to_git(**context):
    """
    Commit le fichier de log dans Git (désactivé pour l'instant).
    """
    return {"status": "skipped", "reason": "Git commit non implémenté"}

with DAG(
    'weather_daily_log_commit_v2',
    start_date=datetime(2024, 1, 1),
    schedule='0 6 * * *',  # Tous les jours à 6h
    catchup=False,
    tags=['weather', 'logging', 'git-commit'],
) as dag:
    
    add_log_task = PythonOperator(
        task_id='add_weather_log_entry',
        python_callable=add_log_entry,
    )
    
    commit_git_task = PythonOperator(
        task_id='commit_log_to_git',
        python_callable=commit_log_to_git,
    )
    
    # Dépendance: d'abord ajouter le log, puis committer
    add_log_task >> commit_git_task
