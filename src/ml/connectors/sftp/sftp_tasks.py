"""
Fonctions pour l'intégration SFTP avec la base de données.

Ce module contient les fonctions qui encapsulent le traitement des données
SFTP pour récupérer les valeurs réelles et mettre à jour la base de données.

Exemple d'utilisation :
    from ml.connectors.sftp.sftp_tasks import process_sftp_actual_values

    results = process_sftp_actual_values(
        sftp_host="sftp.example.com",
        sftp_username="user",
        ppk_key_path="/path/to/key.ppk",
        passphrase="passphrase",
        db_uri="postgresql://user:pass@host/db",
        remote_directory="/data/incoming",
        archive_directory="/data/archived"
    )
"""

from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .sftp_data_processor import SFTPDataProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_sftp_actual_values(
    sftp_host: str,
    sftp_username: str,
    ssh_private_key_b64: Optional[str] = None,
    ssh_private_key_content: Optional[str] = None,
    db_uri: str = None,
    remote_directory: str = None,
    archive_directory: str = "/archived",
    passphrase: Optional[str] = None,
    sftp_port: int = 22,
    sftp_timeout: int = 30,
    file_pattern: str = "*.csv",
    temp_local_dir: str = "/tmp/sftp_temp"
) -> Dict[str, Any]:
    """
    Traite les fichiers SFTP pour mettre à jour les valeurs réelles.

    Cette tâche :
    1. Se connecte au serveur SFTP avec authentification PPK
    2. Liste les fichiers dans le répertoire distant
    3. Télécharge et parse chaque fichier
    4. Fait correspondre les valeurs réelles avec les prédictions
    5. Met à jour la base de données avec les valeurs réelles
    6. Archive les fichiers traités sur le serveur SFTP

    Args:
        sftp_host: Adresse du serveur SFTP
        sftp_username: Nom d'utilisateur SFTP
        ppk_key_path: Chemin vers le fichier de clé PPK
        db_uri: URI de connexion PostgreSQL
        remote_directory: Répertoire distant contenant les fichiers à traiter
        archive_directory: Répertoire d'archive sur SFTP (défaut: /archived)
        passphrase: Passphrase pour la clé PPK (optionnel)
        sftp_port: Port SFTP (défaut: 22)
        sftp_timeout: Timeout SFTP en secondes (défaut: 30)
        file_pattern: Pattern de fichiers à traiter (défaut: *.csv)
        temp_local_dir: Répertoire temporaire local (défaut: /tmp/sftp_temp)

    Returns:
        dict: Résultats du traitement avec statistiques

    Raises:
        Exception: Si la configuration échoue ou si une erreur critique survient
    """
    # Créer le processeur
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

    # Configurer le processeur
    if not processor.setup():
        raise Exception("Impossible de configurer le processeur SFTP")

    # Traiter le répertoire
    results = processor.process_directory(
        remote_directory=remote_directory,
        archive_directory=archive_directory,
        file_pattern=file_pattern,
        temp_local_dir=temp_local_dir
    )

    # Générer le résumé
    summary = processor.get_processing_summary(results)

    logger.info(f"✅ Traitement terminé: {summary}")

    return {
        "summary": summary,
        "details": results
    }


def process_single_sftp_file(
    sftp_host: str,
    sftp_username: str,
    ssh_private_key_b64: Optional[str] = None,
    ssh_private_key_content: Optional[str] = None,
    db_uri: str = None,
    remote_file_path: str = None,
    archive_directory: str = "/archived",
    passphrase: Optional[str] = None,
    sftp_port: int = 22,
    sftp_timeout: int = 30,
    temp_local_dir: str = "/tmp/sftp_temp"
) -> Dict[str, Any]:
    """
    Traite un fichier individuel depuis SFTP.

    Utile pour traiter des fichiers spécifiques ou pour des workflows plus granulaires.

    Args:
        sftp_host: Adresse du serveur SFTP
        sftp_username: Nom d'utilisateur SFTP
        ppk_key_path: Chemin vers le fichier de clé PPK
        db_uri: URI de connexion PostgreSQL
        remote_file_path: Chemin du fichier distant à traiter
        archive_directory: Répertoire d'archive sur SFTP (défaut: /archived)
        passphrase: Passphrase pour la clé PPK (optionnel)
        sftp_port: Port SFTP (défaut: 22)
        sftp_timeout: Timeout SFTP en secondes (défaut: 30)
        temp_local_dir: Répertoire temporaire local (défaut: /tmp/sftp_temp)

    Returns:
        dict: Résultat du traitement du fichier
    """
    # Créer le processeur
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

    # Configurer le processeur
    if not processor.setup():
        raise Exception("Impossible de configurer le processeur SFTP")

    # Traiter le fichier
    result = processor.process_file(
        remote_file_path=remote_file_path,
        archive_directory=archive_directory,
        temp_local_dir=temp_local_dir
    )

    logger.info(f"✅ Fichier traité: {result}")

    return result


def list_sftp_files(
    sftp_host: str,
    sftp_username: str,
    ssh_private_key_b64: Optional[str] = None,
    ssh_private_key_content: Optional[str] = None,
    remote_directory: str = None,
    passphrase: Optional[str] = None,
    sftp_port: int = 22,
    sftp_timeout: int = 30,
    file_pattern: Optional[str] = None,
    recursive: bool = False
) -> list:
    """
    Liste les fichiers disponibles sur un serveur SFTP.

    Utile pour vérifier les fichiers avant traitement ou pour des workflows conditionnels.

    Args:
        sftp_host: Adresse du serveur SFTP
        sftp_username: Nom d'utilisateur SFTP
        ppk_key_path: Chemin vers le fichier de clé PPK
        remote_directory: Répertoire distant à lister
        passphrase: Passphrase pour la clé PPK (optionnel)
        sftp_port: Port SFTP (défaut: 22)
        sftp_timeout: Timeout SFTP en secondes (défaut: 30)
        file_pattern: Pattern de fichiers à filtrer (optionnel)
        recursive: Liste récursive (défaut: False)

    Returns:
        list: Liste des informations sur les fichiers
    """
    from .sftp_connector import SFTPConnector

    connector = SFTPConnector(
        host=sftp_host,
        username=sftp_username,
        ssh_private_key_b64=ssh_private_key_b64,
        ssh_private_key_content=ssh_private_key_content,
        passphrase=passphrase,
        port=sftp_port,
        timeout=sftp_timeout
    )

    with connector:
        files = connector.list_files(
            remote_directory,
            pattern=file_pattern,
            recursive=recursive
        )

    logger.info(f"📁 {len(files)} fichiers trouvés dans {remote_directory}")

    return files
