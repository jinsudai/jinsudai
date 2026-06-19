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

from ml.connectors.weather.weather_api import WeatherAPI
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

def run_weather_update(**context):
    """Exécute le flow de mise à jour des données météo."""
    params = context.get('params', {})
    
    config_path = params.get('config_path', 'src/configs/consumption.yaml')
    weather_output_path = params.get('weather_output_path', None)
    days_ahead = params.get('days_ahead', 7)
    
    # Charger la configuration
    config = load_config(config_path=config_path)
    
    # Récupérer les paramètres depuis la config
    latitude = config.get('data', {}).get('weather_latitude', 43.5297)
    longitude = config.get('data', {}).get('weather_longitude', 5.4474)
    location_name = config.get('data', {}).get('weather_location', 'Aix en Provence')
    
    if weather_output_path is None:
        weather_output_path = config.get('data', {}).get('weather_file', 'data/processed/weather.parquet')
    
    # Déterminer la date de début (aujourd'hui - 30 jours par défaut)
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now() + timedelta(days=days_ahead)
    
    # Récupérer les données météo
    api = WeatherAPI(latitude=latitude, longitude=longitude, location_name=location_name)
    df = api.fetch_historical(start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'), hourly=True)
    
    # Sauvegarder
    df.to_parquet(weather_output_path)
    
    return {"status": "success", "output_path": weather_output_path}

with DAG(
    'weather_daily_update',
    default_args=default_args,
    description='Met à jour quotidiennement le fichier weather.parquet avec les nouvelles données météo',
    schedule='0 6 * * *',  # Tous les jours à 6h
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
    )
