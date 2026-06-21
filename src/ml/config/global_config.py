"""
Module de chargement de la configuration globale.

Ce module fournit des fonctions pour charger la configuration globale
depuis le fichier config.yaml à la racine du projet.

Exemple d'utilisation :
    from ml.config.global_config import load_global_config, get_email_config

    # Charger toute la configuration
    config = load_global_config()

    # Récupérer uniquement la configuration email
    email_config = get_email_config()

    # Créer un notificateur email avec la configuration globale
    from ml.utils.notifications.email_notifier import EmailNotifier
    notifier = EmailNotifier(config=email_config)
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Chemin vers le fichier de configuration globale
GLOBAL_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config.yaml"


def load_global_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Charge la configuration globale depuis config.yaml.

    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)
                    Si non fourni, utilise config.yaml à la racine du projet

    Returns:
        Dictionnaire avec la configuration complète

    Raises:
        FileNotFoundError: Si le fichier de configuration n'existe pas
        yaml.YAMLError: Si le fichier YAML est invalide
    """
    if config_path is None:
        config_path = GLOBAL_CONFIG_PATH

    if not config_path.exists():
        raise FileNotFoundError(f"Fichier de configuration global introuvable: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        logger.info(f"Configuration globale chargée depuis {config_path}")
        return config

    except yaml.YAMLError as e:
        logger.error(f"Erreur lors du parsing du fichier YAML: {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {e}")
        raise


def get_email_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Récupère uniquement la configuration email.

    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)

    Returns:
        Dictionnaire avec la configuration email
    """
    config = load_global_config(config_path)
    return config.get("email", {})


def get_database_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Récupère uniquement la configuration de la base de données.

    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)

    Returns:
        Dictionnaire avec la configuration de la base de données
    """
    config = load_global_config(config_path)
    return config.get("database", {})


def get_sftp_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Récupère uniquement la configuration SFTP.

    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)

    Returns:
        Dictionnaire avec la configuration SFTP
    """
    config = load_global_config(config_path)
    return config.get("sftp", {})


def get_mlflow_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Récupère uniquement la configuration MLflow.

    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)

    Returns:
        Dictionnaire avec la configuration MLflow
    """
    config = load_global_config(config_path)
    return config.get("mlflow", {})


def get_environment(config_path: Optional[Path] = None) -> str:
    """
    Récupère l'environnement actuel.

    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)

    Returns:
        Environnement (dev, test, prod)
    """
    config = load_global_config(config_path)
    return config.get("environment", "dev")


def create_email_notifier_from_config(config_path: Optional[Path] = None):
    """
    Crée un notificateur email à partir de la configuration globale.

    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)

    Returns:
        Instance de EmailNotifier configurée

    Raises:
        ImportError: Si le module email_notifier n'est pas disponible
    """
    from ml.utils.notifications.email_notifier import EmailNotifier

    email_config = get_email_config(config_path)

    # Vérifier si les notifications email sont activées
    if not email_config.get("enabled", False):
        logger.warning("Les notifications email sont désactivées dans la configuration")
        return None

    # Créer le notificateur avec la configuration
    return EmailNotifier(config=email_config)


def get_database_uri(config_path: Optional[Path] = None) -> Optional[str]:
    """
    Récupère l'URI de la base de données depuis la configuration ou les variables d'environnement.

    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)

    Returns:
        URI de la base de données ou None
    """
    # Priorité: variable d'environnement > configuration
    db_uri = os.getenv("PREDICTIONS_POSTGRES_URI")

    if not db_uri:
        db_config = get_database_config(config_path)
        db_uri = db_config.get("uri")

    return db_uri


def get_resend_api_key(config_path: Optional[Path] = None) -> Optional[str]:
    """
    Récupère la clé API Resend depuis la configuration ou les variables d'environnement.

    Args:
        config_path: Chemin vers le fichier de configuration (optionnel)

    Returns:
        Clé API Resend ou None
    """
    # Priorité: variable d'environnement > configuration
    api_key = os.getenv("RESEND_API_KEY")

    if not api_key:
        email_config = get_email_config(config_path)
        resend_config = email_config.get("resend", {})
        api_key = resend_config.get("api_key")

    return api_key


def load_config_with_environment(config_name: str) -> Dict[str, Any]:
    """
    Charge la configuration en fusionnant la config de base avec la config spécifique à l'environnement.

    Args:
        config_name: Nom de la configuration (ex: 'consumption', 'solar_production')

    Returns:
        Dictionnaire avec la configuration fusionnée
    """
    from ml.config import load_config
    
    # Charger la config de base
    base_config = load_config(config_name=config_name)
    
    # Charger la config spécifique à l'environnement si elle existe
    # Priorité: variable d'environnement ENVIRONMENT (majuscules) > Environment (premier caractère majuscule) > Dev par défaut
    environment = os.getenv('ENVIRONMENT') or os.getenv('Environment', 'Dev')
    environment = environment.lower()
    env_config_name = f"{config_name}.{environment}"
    
    try:
        env_config = load_config(config_name=env_config_name)
        config = {**base_config, **env_config}
        logger.info(f"Config chargée: {config_name} + {env_config_name}")
        return config
    except Exception:
        logger.info(f"Config chargée: {config_name} (pas de config spécifique pour {environment})")
        return base_config


def get_services_names() -> list:
    """
    Récupère la liste des noms de services depuis la configuration globale.

    Returns:
        Liste des noms de services
    """
    config = load_global_config()
    services = config.get('services', {}).get('names', [])
    return services


def get_external_services_names() -> list:
    """
    Récupère la liste des noms de services externes depuis la configuration globale.

    Returns:
        Liste des noms de services externes
    """
    config = load_global_config()
    services = config.get('services', {}).get('external', [])
    return services


def get_apis_names() -> list:
    """
    Récupère la liste des noms d'APIs depuis la configuration globale.

    Returns:
        Liste des noms d'APIs
    """
    config = load_global_config()
    apis = config.get('services', {}).get('apis', [])
    return apis
