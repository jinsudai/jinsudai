"""
Airflow DAG pour l'ingestion des données via SFTP.

Ce DAG correspond au flow Prefect sftp_ingestion_pipeline.
Il orchestre l'ingestion des données via SFTP : listing → téléchargement → parsing → matching → mise à jour BD → archivage.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ml.workflows.sftp_ingestion_flow import sftp_ingestion_pipeline

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

def run_sftp_ingestion(**context):
    """Exécute le pipeline d'ingestion SFTP."""
    params = context.get('params', {})
    
    result = sftp_ingestion_pipeline(
        sftp_host=params.get('sftp_host'),
        sftp_username=params.get('sftp_username'),
        ssh_private_key_b64=params.get('ssh_private_key_b64'),
        ssh_private_key_content=params.get('ssh_private_key_content'),
        db_uri=params.get('db_uri'),
        remote_directory=params.get('remote_directory'),
        archive_directory=params.get('archive_directory'),
        passphrase=params.get('passphrase'),
        sftp_port=params.get('sftp_port', 22),
        sftp_timeout=params.get('sftp_timeout', 30),
        file_pattern=params.get('file_pattern', '*.csv'),
        temp_local_dir=params.get('temp_local_dir', '/tmp/sftp_temp')
    )
    
    return result

with DAG(
    'sftp_ingestion_pipeline',
    default_args=default_args,
    description='Pipeline d\'ingestion des données via SFTP : listing → téléchargement → parsing → matching → mise à jour BD → archivage',
    schedule='0 */4 * * *',  # Toutes les 4 heures
    catchup=False,
    max_active_runs=1,
    tags=['sftp', 'ingestion', 'data-update'],
    params={
        'sftp_host': None,
        'sftp_username': None,
        'ssh_private_key_b64': None,
        'ssh_private_key_content': None,
        'db_uri': None,
        'remote_directory': None,
        'archive_directory': None,
        'passphrase': None,
        'sftp_port': 22,
        'sftp_timeout': 30,
        'file_pattern': '*.csv',
        'temp_local_dir': '/tmp/sftp_temp'
    }
) as dag:
    
    sftp_ingestion_task = PythonOperator(
        task_id='run_sftp_ingestion',
        python_callable=run_sftp_ingestion,
    )
