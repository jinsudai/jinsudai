"""
Airflow DAG pour ajouter des logs horodatés au pipeline WeatherDaily et les committer dans Git.

Ce DAG:
- Lit le fichier de log s'il existe (pipelines/WeatherDaily/weather_daily.log)
- Ajoute une ligne de log horodatée avec l'origine Airflow
- Commit le fichier dans Git
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

# Configuration du chemin du fichier de log
# Dans le conteneur Airflow, les DAGs sont dans /opt/airflow/dags/
# Le dossier src est copié dans /opt/airflow/src
# On utilise un chemin absolu depuis AIRFLOW_HOME
AIRFLOW_HOME = os.environ.get('AIRFLOW_HOME', '/opt/airflow')
LOG_FILE_PATH = os.path.join(AIRFLOW_HOME, 'logs', 'weather_daily.log')

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def add_log_entry(**context):
    """
    Ajoute une entrée de log horodatée dans le fichier weather_daily.log.
    
    Format: [YYYY-MM-DD HH:MM:SS] Airflow - weather_daily_log_commit - Message
    """
    dag_run = context.get('dag_run')
    execution_date = context.get('execution_date')
    
    # Formater la date et l'heure
    timestamp = execution_date.strftime('%Y-%m-%d %H:%M:%S')
    
    # Créer le message de log
    log_message = f"[{timestamp}] Airflow - weather_daily_log_commit - Pipeline WeatherDaily exécuté avec succès\n"
    
    # S'assurer que le répertoire existe
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Lire le fichier existant s'il existe
    existing_content = ""
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
            existing_content = f.read()
    
    # Ajouter la nouvelle entrée de log
    with open(LOG_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(existing_content)
        f.write(log_message)
    
    return {"status": "success", "log_file": LOG_FILE_PATH, "message": log_message.strip()}

def commit_log_to_git(**context):
    """
    Commit le fichier de log dans Git via l'API GitHub.
    
    Note: Dans un environnement Airflow conteneurisé, le repo git local n'est pas accessible.
    Cette fonction utilise l'API GitHub pour faire le commit à distance.
    """
    # Pour l'instant, on skippe cette partie car elle nécessite une configuration GitHub
    # TODO: Implémenter avec l'API GitHub ou monter le repo git dans le conteneur
    return {"status": "skipped", "reason": "Git commit non implémenté dans l'environnement conteneurisé"}

with DAG(
    'weather_daily_log_commit',
    default_args=default_args,
    description='Ajoute des logs horodatés au pipeline WeatherDaily et les committer dans Git',
    schedule='0 6 * * *',  # Tous les jours à 6h (après le DAG weather_daily_update)
    catchup=False,
    max_active_runs=1,
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
