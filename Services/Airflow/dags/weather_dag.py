"""
Airflow DAG pour la mise à jour quotidienne des données météo.

Ce DAG correspond au flow Prefect update_weather_daily_flow.
Il met à jour quotidiennement le fichier weather.parquet avec les nouvelles données météo.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import sys
import os

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ml.workflows.weather_flow import update_weather_daily_flow

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def run_weather_update(**context):
    """Exécute le flow de mise à jour des données météo."""
    config_path = context.get('params', {}).get('config_path', 'src/configs/consumption.yaml')
    weather_output_path = context.get('params', {}).get('weather_output_path', None)
    days_ahead = context.get('params', {}).get('days_ahead', 7)
    
    result = update_weather_daily_flow(
        config_path=config_path,
        weather_output_path=weather_output_path,
        days_ahead=days_ahead
    )
    
    return result

with DAG(
    'weather_daily_update',
    default_args=default_args,
    description='Met à jour quotidiennement le fichier weather.parquet avec les nouvelles données météo',
    schedule_interval='0 6 * * *',  # Tous les jours à 6h
    catchup=False,
    max_active_runs=1,
    tags=['weather', 'daily', 'data-update'],
    params={
        'config_path': 'src/configs/consumption.yaml',
        'weather_output_path': None,
        'days_ahead': 7
    }
) as dag:
    
    weather_update_task = PythonOperator(
        task_id='update_weather_data',
        python_callable=run_weather_update,
        provide_context=True
    )
