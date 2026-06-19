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

from ml.connectors.sftp.sftp_data_processor import SFTPDataProcessor
from ml.config import load_config

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

def setup_sftp_task(**context):
    """Configure le processeur SFTP (connexion SFTP + base de données)."""
    params = context.get('params', {})
    
    # Charger la config pour l'URI de la base de données
    config = load_config(config_name="consumption")
    db_uri = params.get('db_uri') or config.get('database', {}).get('uri')
    
    if not db_uri:
        raise ValueError("URI de base de données requise")
    
    # Créer le processeur SFTP
    processor = SFTPDataProcessor(
        sftp_host=params.get('sftp_host'),
        sftp_username=params.get('sftp_username'),
        ssh_private_key_b64=params.get('ssh_private_key_b64'),
        ssh_private_key_content=params.get('ssh_private_key_content'),
        db_uri=db_uri,
        passphrase=params.get('passphrase'),
        sftp_port=params.get('sftp_port', 22),
        sftp_timeout=params.get('sftp_timeout', 30)
    )
    
    if not processor.setup():
        raise Exception("Échec de la configuration du processeur SFTP")
    
    # Stocker la config dans XCom
    context['task_instance'].xcom_push(key='sftp_config', value={
        'sftp_host': params.get('sftp_host'),
        'sftp_username': params.get('sftp_username'),
        'ssh_private_key_b64': params.get('ssh_private_key_b64'),
        'ssh_private_key_content': params.get('ssh_private_key_content'),
        'db_uri': db_uri,
        'passphrase': params.get('passphrase'),
        'sftp_port': params.get('sftp_port', 22),
        'sftp_timeout': params.get('sftp_timeout', 30),
        'remote_directory': params.get('remote_directory', '/data/incoming'),
        'archive_directory': params.get('archive_directory', '/data/archived'),
        'file_pattern': params.get('file_pattern', '*.csv'),
        'temp_local_dir': params.get('temp_local_dir', '/tmp/sftp_temp')
    })
    
    return {"status": "setup_complete"}

def list_files_task(**context):
    """Liste les fichiers disponibles sur le serveur SFTP."""
    sftp_config = context['task_instance'].xcom_pull(task_ids='setup_sftp', key='sftp_config')
    
    processor = SFTPDataProcessor(
        sftp_host=sftp_config['sftp_host'],
        sftp_username=sftp_config['sftp_username'],
        ssh_private_key_b64=sftp_config['ssh_private_key_b64'],
        ssh_private_key_content=sftp_config['ssh_private_key_content'],
        db_uri=sftp_config['db_uri'],
        passphrase=sftp_config['passphrase'],
        sftp_port=sftp_config['sftp_port'],
        sftp_timeout=sftp_config['sftp_timeout']
    )
    processor.setup()
    
    # Lister les fichiers
    from ml.connectors.sftp.sftp_connector import SFTPConnector
    connector = SFTPConnector(
        host=sftp_config['sftp_host'],
        username=sftp_config['sftp_username'],
        ssh_private_key_b64=sftp_config['ssh_private_key_b64'],
        ssh_private_key_content=sftp_config['ssh_private_key_content'],
        passphrase=sftp_config['passphrase'],
        port=sftp_config['sftp_port'],
        timeout=sftp_config['sftp_timeout']
    )
    
    with connector:
        files = connector.list_files(
            remote_directory=sftp_config['remote_directory'],
            pattern=sftp_config['file_pattern']
        )
    
    # Stocker la liste des fichiers dans XCom
    context['task_instance'].xcom_push(key='file_list', value=files)
    
    return {"status": "files_listed", "n_files": len(files)}

def process_files_task(**context):
    """Traite tous les fichiers SFTP."""
    sftp_config = context['task_instance'].xcom_pull(task_ids='setup_sftp', key='sftp_config')
    file_list = context['task_instance'].xcom_pull(task_ids='list_files', key='file_list')
    
    processor = SFTPDataProcessor(
        sftp_host=sftp_config['sftp_host'],
        sftp_username=sftp_config['sftp_username'],
        ssh_private_key_b64=sftp_config['ssh_private_key_b64'],
        ssh_private_key_content=sftp_config['ssh_private_key_content'],
        db_uri=sftp_config['db_uri'],
        passphrase=sftp_config['passphrase'],
        sftp_port=sftp_config['sftp_port'],
        sftp_timeout=sftp_config['sftp_timeout']
    )
    processor.setup()
    
    # Traiter tous les fichiers
    results = processor.process_directory(
        remote_directory=sftp_config['remote_directory'],
        archive_directory=sftp_config['archive_directory'],
        file_pattern=sftp_config['file_pattern'],
        temp_local_dir=sftp_config['temp_local_dir']
    )
    
    return {"status": "processing_complete", "results": results}

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
    
    # Définir les tâches individuelles
    setup_task = PythonOperator(
        task_id='setup_sftp',
        python_callable=setup_sftp_task,
    )
    
    list_task = PythonOperator(
        task_id='list_files',
        python_callable=list_files_task,
    )
    
    process_task = PythonOperator(
        task_id='process_files',
        python_callable=process_files_task,
    )
    
    # Définir les dépendances entre les tâches
    setup_task >> list_task >> process_task
