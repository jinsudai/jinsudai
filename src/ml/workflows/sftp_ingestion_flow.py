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
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from ml.connectors.sftp.sftp_tasks import (
    process_sftp_actual_values_task,
    list_sftp_files_task
)
from ml.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@task
def setup_sftp_config_task() -> Dict[str, Any]:
    """
    Tâche de configuration des paramètres SFTP depuis la config.
    
    Returns:
        dict: Configuration SFTP
    """
    config = load_config(config_name="consumption")
    
    sftp_config = config.get('sftp', {})
    
    if not sftp_config:
        raise ValueError("Configuration SFTP manquante dans consumption.yaml")
    
    logger.info("Configuration SFTP chargée")
    logger.info(f"  Host: {sftp_config.get('host')}")
    logger.info(f"  Username: {sftp_config.get('username')}")
    logger.info(f"  Remote directory: {sftp_config.get('remote_directory')}")
    
    return sftp_config


@task
def list_files_task(
    sftp_host: str,
    sftp_username: str,
    ssh_private_key_content: str,
    remote_directory: str = None,
    passphrase: Optional[str] = None,
    sftp_port: int = 22,
    sftp_timeout: int = 30,
    file_pattern: str = "*.csv"
) -> List[Dict[str, Any]]:
    """
    Tâche de listing des fichiers disponibles sur SFTP.
    
    Args:
        sftp_host: Adresse du serveur SFTP
        sftp_username: Nom d'utilisateur SFTP
        ppk_key_path: Chemin vers le fichier de clé PPK
        remote_directory: Répertoire distant à lister
        passphrase: Passphrase pour la clé PPK (optionnel)
        sftp_port: Port SFTP (défaut: 22)
        sftp_timeout: Timeout SFTP en secondes (défaut: 30)
        file_pattern: Pattern de fichiers à filtrer (défaut: *.csv)
    
    Returns:
        list: Liste des informations sur les fichiers
    """
    files = list_sftp_files_task(
        sftp_host=sftp_host,
        sftp_username=sftp_username,
        ssh_private_key_content=ssh_private_key_content,
        remote_directory=remote_directory,
        passphrase=passphrase,
        sftp_port=sftp_port,
        sftp_timeout=sftp_timeout,
        file_pattern=file_pattern,
        recursive=False
    )
    
    logger.info(f"{len(files)} fichiers trouvés dans {remote_directory}")
    
    return files


@task
def process_files_task(
    sftp_host: str,
    sftp_username: str,
    ssh_private_key_content: str,
    db_uri: str = None,
    remote_directory: str = None,
    archive_directory: str = None,
    passphrase: Optional[str] = None,
    sftp_port: int = 22,
    sftp_timeout: int = 30,
    file_pattern: str = "*.csv",
    temp_local_dir: str = "/tmp/sftp_temp"
) -> Dict[str, Any]:
    """
    Tâche de traitement des fichiers SFTP.
    
    Args:
        sftp_host: Adresse du serveur SFTP
        sftp_username: Nom d'utilisateur SFTP
        ppk_key_path: Chemin vers le fichier de clé PPK
        db_uri: URI de connexion PostgreSQL
        remote_directory: Répertoire distant contenant les fichiers
        archive_directory: Répertoire d'archive sur SFTP
        passphrase: Passphrase pour la clé PPK (optionnel)
        sftp_port: Port SFTP (défaut: 22)
        sftp_timeout: Timeout SFTP en secondes (défaut: 30)
        file_pattern: Pattern de fichiers à traiter (défaut: *.csv)
        temp_local_dir: Répertoire temporaire local (défaut: /tmp/sftp_temp)
    
    Returns:
        dict: Résultats du traitement avec statistiques
    """
    result = process_sftp_actual_values_task(
        sftp_host=sftp_host,
        sftp_username=sftp_username,
        ssh_private_key_content=ssh_private_key_content,
        db_uri=db_uri,
        remote_directory=remote_directory,
        archive_directory=archive_directory,
        passphrase=passphrase,
        sftp_port=sftp_port,
        sftp_timeout=sftp_timeout,
        file_pattern=file_pattern,
        temp_local_dir=temp_local_dir
    )
    
    return result


@task
def generate_summary_task(processing_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tâche de génération d'un résumé du traitement.
    
    Args:
        processing_result: Résultats du traitement
    
    Returns:
        dict: Résumé du traitement
    """
    summary = processing_result.get("summary", {})
    details = processing_result.get("details", [])
    
    logger.info("=== RÉSUMÉ DU TRAITEMENT ===")
    logger.info(f"  Total fichiers: {summary.get('total_files', 0)}")
    logger.info(f"  Réussis: {summary.get('successful', 0)}")
    logger.info(f"  Échoués: {summary.get('failed', 0)}")
    logger.info(f"  Total enregistrements: {summary.get('total_records_processed', 0)}")
    logger.info(f"  Prédictions mises à jour: {summary.get('total_predictions_updated', 0)}")
    logger.info(f"  Fichiers archivés: {summary.get('files_archived', 0)}")
    logger.info(f"  Taux de succès: {summary.get('success_rate', 0):.2%}")
    
    return summary


@flow(
    name="sftp-ingestion-pipeline",
    description="Pipeline d'ingestion des données via SFTP : listing → téléchargement → parsing → matching → mise à jour BD → archivage",
    retries=1,
    retry_delay_seconds=60
)
def sftp_ingestion_pipeline(
    sftp_host: Optional[str] = None,
    sftp_username: Optional[str] = None,
    ssh_private_key_content: str = None,
    db_uri: Optional[str] = None,
    remote_directory: Optional[str] = None,
    archive_directory: Optional[str] = None,
    passphrase: Optional[str] = None,
    sftp_port: int = 22,
    sftp_timeout: int = 30,
    file_pattern: str = "*.csv",
    temp_local_dir: str = "/tmp/sftp_temp"
) -> Dict[str, Any]:
    """
    Pipeline complet pour l'ingestion des données via SFTP.
    
    Étapes :
    1. Configuration des paramètres SFTP depuis la config
    2. Listing des fichiers disponibles sur le serveur SFTP
    3. Traitement des fichiers (téléchargement, parsing, matching avec prédictions)
    4. Mise à jour de la base de données avec les valeurs réelles
    5. Archivage des fichiers traités
    6. Génération d'un résumé du traitement
    
    Args:
        sftp_host: Adresse du serveur SFTP (optionnel, utilise la config par défaut)
        sftp_username: Nom d'utilisateur SFTP (optionnel, utilise la config par défaut)
        ppk_key_path: Chemin vers le fichier de clé PPK (optionnel, utilise la config par défaut)
        db_uri: URI de connexion PostgreSQL (optionnel, utilise la config par défaut)
        remote_directory: Répertoire distant (optionnel, utilise la config par défaut)
        archive_directory: Répertoire d'archive (optionnel, utilise la config par défaut)
        passphrase: Passphrase pour la clé PPK (optionnel)
        sftp_port: Port SFTP (défaut: 22)
        sftp_timeout: Timeout SFTP en secondes (défaut: 30)
        file_pattern: Pattern de fichiers à traiter (défaut: *.csv)
        temp_local_dir: Répertoire temporaire local (défaut: /tmp/sftp_temp)
    
    Returns:
        dict: Résultats complets du pipeline
    """
    logger.info("####################################################")
    logger.info("### PIPELINE D'INGESTION DES DONNÉES VIA SFTP ###")
    logger.info(f"### Date/Heure: {datetime.now()} ###")
    logger.info("####################################################\n")
    
    # 1. ===== CONFIGURATION =====
    logger.info("=== ÉTAPE 1: Configuration SFTP ===")
    
    sftp_config = setup_sftp_config_task()
    
    # Utiliser les paramètres passés ou ceux de la config
    sftp_host = sftp_host or sftp_config.get('host')
    sftp_username = sftp_username or sftp_config.get('username')
    ssh_private_key_content = ssh_private_key_content or sftp_config.get('ssh_private_key_content')
    remote_directory = remote_directory or sftp_config.get('remote_directory')
    archive_directory = archive_directory or sftp_config.get('archive_directory', '/archived')
    
    # Charger la config pour la BD
    config = load_config(config_name="consumption")
    db_uri = db_uri or config.get('database', {}).get('uri')
    
    passphrase = passphrase or sftp_config.get('passphrase')
    sftp_port = sftp_port or sftp_config.get('port', 22)
    sftp_timeout = sftp_timeout or sftp_config.get('timeout', 30)
    
    # 2. ===== LISTING DES FICHIERS =====
    logger.info("\n=== ÉTAPE 2: Listing des fichiers disponibles ===")
    
    files = list_files_task(
        sftp_host=sftp_host,
        sftp_username=sftp_username,
        ssh_private_key_content=ssh_private_key_content,
        remote_directory=remote_directory,
        passphrase=passphrase,
        sftp_port=sftp_port,
        sftp_timeout=sftp_timeout,
        file_pattern=file_pattern
    )
    
    if not files:
        logger.warning("Aucun fichier trouvé, pipeline terminé")
        return {
            "status": "no_files",
            "files_count": 0,
            "processing": {"status": "skipped"},
            "summary": {"total_files": 0, "successful": 0, "failed": 0}
        }
    
    # 3. ===== TRAITEMENT DES FICHIERS =====
    logger.info("\n=== ÉTAPE 3: Traitement des fichiers ===")
    
    processing_result = process_files_task(
        sftp_host=sftp_host,
        sftp_username=sftp_username,
        ssh_private_key_content=ssh_private_key_content,
        db_uri=db_uri,
        remote_directory=remote_directory,
        archive_directory=archive_directory,
        passphrase=passphrase,
        sftp_port=sftp_port,
        sftp_timeout=sftp_timeout,
        file_pattern=file_pattern,
        temp_local_dir=temp_local_dir
    )
    
    # 4. ===== GÉNÉRATION DU RÉSUMÉ =====
    logger.info("\n=== ÉTAPE 4: Génération du résumé ===")
    
    summary = generate_summary_task(processing_result=processing_result)
    
    # 5. ===== RÉSULTAT FINAL =====
    logger.info("\n" + "="*60)
    logger.info("PIPELINE D'INGESTION SFTP TERMINÉ")
    logger.info("="*60)
    
    return {
        "status": "success",
        "files_count": len(files),
        "processing": processing_result,
        "summary": summary
    }
