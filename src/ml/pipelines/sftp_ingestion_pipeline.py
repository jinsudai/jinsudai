"""
Pipeline métier pour l'ingestion de fichiers SFTP.

Ce module contient la logique métier indépendante de Prefect.
Il est ensuite utilisé par `ml.workflows.sftp_ingestion_flow`.
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

    env_db_uri = os.getenv('DATABASE_URI')
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
    """Exécute le pipeline SFTP sans dépendre de Prefect."""
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


__all__ = [
    'load_sftp_config',
    'run_sftp_ingestion_pipeline'
]
