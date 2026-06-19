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
LOG_FILE_PATH = os.path.join(
    os.path.dirname(__file__), 
    '..', '..', '..', 
    'pipelines', 'WeatherDaily', 'weather_daily.log'
)

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
    Commit le fichier de log dans Git.
    """
    import subprocess
    
    # Récupérer le chemin du repo git (racine du projet)
    repo_root = os.path.join(
        os.path.dirname(__file__), 
        '..', '..', '..'
    )
    
    # Chemin relatif du fichier de log par rapport au repo
    log_file_relative = os.path.relpath(LOG_FILE_PATH, repo_root)
    
    # Message de commit
    commit_message = f"Airflow - weather_daily_log_commit - Log horodaté {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    try:
        # Ajouter le fichier à git
        subprocess.run(
            ['git', 'add', log_file_relative],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Commit le fichier
        subprocess.run(
            ['git', 'commit', '-m', commit_message],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True
        )
        
        return {"status": "success", "commit_message": commit_message}
    
    except subprocess.CalledProcessError as e:
        # Si le fichier n'a pas de changements, git commit échouera - c'est normal
        if "nothing to commit" in e.stderr.lower() or "no changes added to commit" in e.stderr.lower():
            return {"status": "skipped", "reason": "No changes to commit"}
        raise

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
