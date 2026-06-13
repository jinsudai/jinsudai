"""
Flow Prefect pour l'ingestion des données via SFTP.

Ce flow orchestre toutes les étapes :
1. Configuration du processeur SFTP (connexion SFTP + base de données)
2. Liste des fichiers disponibles sur le serveur SFTP
3. Traitement des fichiers (téléchargement, parsing, matching avec prédictions)
4. Mise à jour de la base de données avec les valeurs réelles
5. Archivage des fichiers traités
6. Génération d'un résumé du traitement

Exemple d'utilisation :
    from ml.workflows.sftp_ingestion_flow import sftp_ingestion_pipeline
    
    # Exécuter le pipeline complet
    result = sftp_ingestion_pipeline()
"""

from prefect import flow, task
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from ml.workflows.sftp_ingestion_pipeline import (
    load_sftp_config,
    run_sftp_ingestion_pipeline
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@task
def setup_sftp_config_task() -> Dict[str, Any]:
    """Tâche de chargement de la configuration SFTP depuis les variables d'environnement."""
    return load_sftp_config()


@flow(
    name="sftp-ingestion-pipeline",
    description="Pipeline d'ingestion des données via SFTP : listing → téléchargement → parsing → matching → mise à jour BD → archivage",
    retries=1,
    retry_delay_seconds=60
)
def sftp_ingestion_pipeline(
    sftp_host: Optional[str] = None,
    sftp_username: Optional[str] = None,
    ssh_private_key_b64: Optional[str] = None,
    ssh_private_key_content: Optional[str] = None,
    db_uri: Optional[str] = None,
    remote_directory: Optional[str] = None,
    archive_directory: Optional[str] = None,
    passphrase: Optional[str] = None,
    sftp_port: int = 22,
    sftp_timeout: int = 30,
    file_pattern: str = "*.csv",
    temp_local_dir: str = "/tmp/sftp_temp"
) -> Dict[str, Any]:
    """Pipeline Prefect d'ingestion des données SFTP."""
    logger.info("####################################################")
    logger.info("### PIPELINE D'INGESTION DES DONNÉES VIA SFTP ###")
    logger.info(f"### Date/Heure: {datetime.now()} ###")
    logger.info("####################################################\n")

    sftp_config = setup_sftp_config_task()

    return run_sftp_ingestion_pipeline(
        sftp_host=sftp_host or sftp_config.get('host'),
        sftp_username=sftp_username or sftp_config.get('username'),
        ssh_private_key_b64=ssh_private_key_b64 or sftp_config.get('ssh_private_key_b64'),
        ssh_private_key_content=ssh_private_key_content or sftp_config.get('ssh_private_key_content'),
        db_uri=db_uri,
        remote_directory=remote_directory or sftp_config.get('remote_directory'),
        archive_directory=archive_directory or sftp_config.get('archive_directory'),
        passphrase=passphrase or sftp_config.get('passphrase'),
        sftp_port=sftp_port or sftp_config.get('port', 22),
        sftp_timeout=sftp_timeout or sftp_config.get('timeout', 30),
        file_pattern=file_pattern or sftp_config.get('file_pattern', '*.csv'),
        temp_local_dir=temp_local_dir or sftp_config.get('temp_local_dir', '/tmp/sftp_temp')
    )
