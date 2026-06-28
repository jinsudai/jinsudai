"""
Pipeline métier pour l'ingestion de fichiers SFTP.

Ce module contient la logique métier pour l'ingestion SFTP.
"""

from typing import Dict, Any, Optional
from ml.connectors.sftp.sftp_data_processor import SFTPDataProcessor
from ml.config import load_config
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_sftp_config() -> Dict[str, Any]:
    """Charge la configuration SFTP depuis les variables d'environnement."""
    sftp_config = {
        'enabled': os.getenv('SFTP_ENABLED', 'false').lower() == 'true',
        'host': os.getenv('SFTP_HOST'),
        'port': int(os.getenv('SFTP_PORT', '22')),
        'username': os.getenv('SFTP_USERNAME'),
        'ssh_private_key_b64': os.getenv('SFTP_PRIVATE_KEY_B64'),
        'ssh_private_key_content': os.getenv('SFTP_SSH_PRIVATE_KEY_CONTENT'),
        'passphrase': os.getenv('SFTP_PASSPHRASE'),
        'timeout': int(os.getenv('SFTP_TIMEOUT', '30')),
        'remote_directory': os.getenv('SFTP_REMOTE_DIRECTORY', '/data/incoming'),
        'archive_directory': os.getenv('SFTP_ARCHIVE_DIRECTORY', '/data/archived'),
        'file_pattern': os.getenv('SFTP_FILE_PATTERN', '*.csv'),
        'temp_local_dir': os.getenv('SFTP_TEMP_LOCAL_DIR', '/tmp/sftp_temp')
    }

    if not sftp_config.get('host') or not sftp_config.get('username') or not (sftp_config.get('ssh_private_key_b64') or sftp_config.get('ssh_private_key_content')):
        raise ValueError(
            "Configuration SFTP manquante dans les variables d'environnement "
            "(SFTP_HOST, SFTP_USERNAME, SFTP_PRIVATE_KEY_B64 ou SFTP_SSH_PRIVATE_KEY_CONTENT)"
        )

    logger.info("Configuration SFTP chargée depuis les variables d'environnement")
    logger.info(f"  Host: {sftp_config.get('host')}")
    logger.info(f"  Username: {sftp_config.get('username')}")
    logger.info(f"  Remote directory: {sftp_config.get('remote_directory')}")

    return sftp_config


def get_default_db_uri(db_uri: Optional[str] = None) -> Optional[str]:
    if db_uri:
        return db_uri

    env_db_uri = os.getenv('PREDICTIONS_POSTGRES_URI')
    if env_db_uri:
        return env_db_uri

    config = load_config(config_name="consumption")
    return config.get('database', {}).get('uri')


def run_sftp_ingestion_pipeline(
    sftp_host: str,
    sftp_username: str,
    ssh_private_key_b64: Optional[str] = None,
    ssh_private_key_content: Optional[str] = None,
    db_uri: Optional[str] = None,
    remote_directory: str = '/data/incoming',
    archive_directory: str = '/data/archived',
    passphrase: Optional[str] = None,
    sftp_port: int = 22,
    sftp_timeout: int = 30,
    file_pattern: str = '*.csv',
    temp_local_dir: str = '/tmp/sftp_temp'
) -> Dict[str, Any]:

    db_uri = get_default_db_uri(db_uri)

    if not db_uri:
        raise ValueError("URI de la base de données manquante")

    processor = SFTPDataProcessor(
        sftp_host=sftp_host,
        sftp_username=sftp_username,
        ssh_private_key_b64=ssh_private_key_b64,
        ssh_private_key_content=ssh_private_key_content,
        db_uri=db_uri,
        passphrase=passphrase,
        sftp_port=sftp_port,
        sftp_timeout=sftp_timeout
    )

    if not processor.setup():
        raise RuntimeError("Impossible de configurer le pipeline SFTP")

    results = processor.process_directory(
        remote_directory=remote_directory,
        archive_directory=archive_directory,
        file_pattern=file_pattern,
        temp_local_dir=temp_local_dir
    )

    summary = processor.get_processing_summary(results)

    if not results:
        return {
            'status': 'no_files',
            'files_count': 0,
            'processing': {'status': 'skipped'},
            'summary': summary
        }

    return {
        'status': 'success',
        'files_count': len(results),
        'processing': {
            'summary': summary,
            'details': results
        },
        'summary': summary
    }


def run_sftp_ingestion_with_random_data(db_uri: Optional[str] = None) -> Dict[str, Any]:
    """Fallback: utilise `ActualValuesPipeline` pour générer et appliquer des valeurs aléatoires.

    Le pipeline `ActualValuesPipeline` récupère les prédictions de la veille,
    génère des valeurs aléatoires et met à jour la base de données.
    """
    db_uri = get_default_db_uri(db_uri)

    # Importer localement pour éviter les dépendances circulaires
    from ml.pipelines.Actual_values_pipeline import ActualValuesPipeline

    pipeline = ActualValuesPipeline(db_uri=db_uri, config={'sftp': {'enabled': False}})

    if not pipeline.setup():
        return {
            'status': 'error',
            'files_count': 0,
            'processing': {'status': 'failed'},
            'summary': {'note': 'Impossible de configurer le pipeline de valeurs réelles'}
        }

    preds_ok = pipeline.get_previous_day_predictions()
    if not preds_ok:
        return {
            'status': 'error',
            'files_count': 0,
            'processing': {'status': 'failed'},
            'summary': {'note': 'Erreur lors de la récupération des prédictions'}
        }

    # Génération et mise à jour
    if not pipeline.generate_random_actual_values():
        return {
            'status': 'error',
            'files_count': 0,
            'processing': {'status': 'failed'},
            'summary': {'note': 'Échec de la génération/mise à jour aléatoire'}
        }

    summary = {'updated': pipeline.updated_count}

    return {
        'status': 'success',
        'files_count': 1,
        'processing': {
            'summary': summary,
            'details': [{'file': 'random_generated', 'success': True, 'records_processed': pipeline.updated_count, 'predictions_updated': pipeline.updated_count}]
        },
        'summary': summary
    }


__all__ = [
    'load_sftp_config',
    'run_sftp_ingestion_pipeline'
]
