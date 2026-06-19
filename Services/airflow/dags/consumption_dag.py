"""
Airflow DAG pour le pipeline de consommation électrique.

Ce DAG correspond au flow Prefect consumption_full_pipeline.
Il orchestre le pipeline complet : données brutes → modèle en production.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ml.consumption.consumption_preparer import ConsumptionDataPreparer
from ml.connectors.weather.weather_api import WeatherAPI
from ml.connectors.holidays.holidays_api import HolidaysCombinedAPI
from ml.config import load_config

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=15),
}

def generate_weather_task(**context):
    """Génère les données météo."""
    params = context.get('params', {})
    
    start_date = params.get('start_date', '2024-01-01')
    end_date = params.get('end_date', '2024-01-31')
    output_dir = params.get('output_dir', 'data/processed/')
    
    # Charger la config
    config = load_config(config_name="consumption")
    
    # Générer les données météo
    latitude = config.get('data', {}).get('weather_latitude', 43.5297)
    longitude = config.get('data', {}).get('weather_longitude', 5.4474)
    location_name = config.get('data', {}).get('weather_location', 'Aix en Provence')
    
    weather_api = WeatherAPI(latitude=latitude, longitude=longitude, location_name=location_name)
    weather_path = f"{output_dir}/weather_{start_date}_to_{end_date}.parquet"
    weather_df = weather_api.fetch_historical(start_date=start_date, end_date=end_date, hourly=True)
    weather_df.to_parquet(weather_path)
    
    # Stocker le chemin dans XCom
    context['task_instance'].xcom_push(key='weather_path', value=weather_path)
    
    return {"status": "weather_generated", "weather_path": weather_path}

def generate_holidays_task(**context):
    """Génère les données vacances."""
    params = context.get('params', {})
    
    start_date = params.get('start_date', '2024-01-01')
    end_date = params.get('end_date', '2024-01-31')
    output_dir = params.get('output_dir', 'data/processed/')
    
    # Charger la config
    config = load_config(config_name="consumption")
    
    # Générer les données vacances
    zone = config.get('data', {}).get('holidays_zone', 'B')
    holidays_api = HolidaysCombinedAPI()
    holidays_path = f"{output_dir}/holidays_{start_date}_to_{end_date}.parquet"
    holidays_df = holidays_api.fetch(start_date=start_date, end_date=end_date, zone=zone)
    holidays_df.to_parquet(holidays_path)
    
    # Stocker le chemin dans XCom
    context['task_instance'].xcom_push(key='holidays_path', value=holidays_path)
    
    return {"status": "holidays_generated", "holidays_path": holidays_path}

def prepare_consumption_features_task(**context):
    """Prépare les features consommation."""
    params = context.get('params', {})
    
    start_date = params.get('start_date', '2024-01-01')
    end_date = params.get('end_date', '2024-01-31')
    raw_path = params.get('raw_path', 'data/templates/raw_template.csv')
    output_dir = params.get('output_dir', 'data/processed/')
    
    # Récupérer les chemins depuis XCom
    weather_path = context['task_instance'].xcom_pull(task_ids='generate_weather', key='weather_path')
    holidays_path = context['task_instance'].xcom_pull(task_ids='generate_holidays', key='holidays_path')
    
    # Préparer les features consommation
    preparer = ConsumptionDataPreparer()
    features_path = f"{output_dir}/consumption_features_{start_date}_to_{end_date}.parquet"
    preparer.prepare(raw_path=raw_path, weather_path=weather_path, holidays_path=holidays_path, output_path=features_path)
    
    return {"status": "features_prepared", "features_path": features_path}

with DAG(
    'consumption_full_pipeline',
    default_args=default_args,
    description='Pipeline complet : données brutes → modèle en production',
    schedule='0 3 * * 0',  # Tous les dimanches à 3h du matin
    catchup=False,
    max_active_runs=1,
    tags=['consumption', 'training', 'ml'],
    params={
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'raw_path': 'data/templates/raw_template.csv',
        'output_dir': 'data/processed/'
    }
) as dag:
    
    # Définir les tâches individuelles
    weather_task = PythonOperator(
        task_id='generate_weather',
        python_callable=generate_weather_task,
    )
    
    holidays_task = PythonOperator(
        task_id='generate_holidays',
        python_callable=generate_holidays_task,
    )
    
    features_task = PythonOperator(
        task_id='prepare_consumption_features',
        python_callable=prepare_consumption_features_task,
    )
    
    # Définir les dépendances entre les tâches
    # weather et holidays peuvent s'exécuter en parallèle
    [weather_task, holidays_task] >> features_task
