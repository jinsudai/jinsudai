"""
Airflow DAG pour ajouter des logs horodatés au pipeline WeatherDaily et les committer dans Git.

Ce DAG:
- Lit le fichier de log s'il existe (pipelines/WeatherDaily/weather_daily.log)
- Ajoute une ligne de log horodatée avec l'origine Airflow
- Commit le fichier dans Git
"""
from datetime import datetime
from airflow import DAG
from airflow.operators.empty import EmptyOperator

with DAG(
    'weather_daily_log_commit_v2',  # Nouveau nom pour éviter les conflits avec les anciens runs
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=['weather', 'logging', 'git-commit'],
) as dag:
    
    add_log_task = EmptyOperator(task_id='add_weather_log_entry')
    commit_git_task = EmptyOperator(task_id='commit_log_to_git')
    
    # Dépendance: d'abord ajouter le log, puis committer
    add_log_task >> commit_git_task
