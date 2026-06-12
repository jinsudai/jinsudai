"""
Exemple d'utilisation du connector SFTP pour récupérer les valeurs réelles et mettre à jour la base de données.

Ce script démontre comment utiliser le connector SFTP pour:
1. Télécharger des fichiers depuis un serveur SFTP
2. Extraire les valeurs réelles de consommation
3. Mettre à jour la base de données avec ces valeurs
4. Archiver les fichiers traités sur le serveur SFTP

Usage:
    # Configuration des variables d'environnement
    export SFTP_HOST="sftp.example.com"
    export SFTP_USERNAME="your_username"
    export SFTP_PPK_PATH="/path/to/your/key.ppk"
    export SFTP_PASSPHRASE="your_passphrase"
    export DB_URI="postgresql://user:pass@host:port/database"
    
    # Exécuter le script
    python example_usage.py
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ml.connectors.sftp.sftp_connector import SFTPConnector
from ml.connectors.sftp.sftp_data_processor import SFTPDataProcessor
from ml.connectors.sftp.sftp_tasks import (
    process_sftp_actual_values_task,
    process_single_sftp_file_task,
    list_sftp_files_task
)
from ml.utils.notifications.email_notifier import EmailNotifier
from ml.config.global_config import (
    load_global_config,
    get_email_config,
    get_sftp_config,
    get_database_uri,
    create_email_notifier_from_config
)
from ml.config import load_config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_sftp_usage():
    """
    Exemple basique d'utilisation du connector SFTP.
    """
    print("\n" + "="*60)
    print("EXEMPLE 1: Utilisation basique du connector SFTP")
    print("="*60 + "\n")
    
    # Configuration (à remplacer par vos valeurs ou variables d'environnement)
    sftp_config = {
        "host": os.getenv("SFTP_HOST", "sftp.example.com"),
        "username": os.getenv("SFTP_USERNAME", "sftp_user"),
        "ppk_key_path": os.getenv("SFTP_PPK_PATH", "/path/to/key.ppk"),
        "passphrase": os.getenv("SFTP_PASSPHRASE", None),
        "port": 22,
        "timeout": 30
    }
    
    # Créer le connector
    connector = SFTPConnector(**sftp_config)
    
    # Utiliser le context manager pour la connexion automatique
    with connector:
        # Lister les fichiers dans un répertoire
        files = connector.list_files("/data/incoming", pattern="*.csv")
        print(f"Fichiers trouvés: {len(files)}")
        
        for file_info in files:
            print(f"  - {file_info['filename']} ({file_info['size']} octets)")
        
        # Télécharger un fichier spécifique
        if files:
            remote_file = files[0]['path']
            local_file = f"/tmp/{files[0]['filename']}"
            
            downloaded = connector.download_file(remote_file, local_file)
            print(f"Fichier téléchargé: {downloaded}")
            
            # Archiver le fichier après traitement
            archived = connector.archive_file(remote_file, "/archived")
            print(f"Fichier archivé: {archived}")


def example_sftp_data_processor():
    """
    Exemple d'utilisation du processeur de données SFTP pour mettre à jour la base de données.
    """
    print("\n" + "="*60)
    print("EXEMPLE 2: Processeur de données SFTP (mise à jour BD)")
    print("="*60 + "\n")
    
    # Configuration
    sftp_config = {
        "sftp_host": os.getenv("SFTP_HOST", "sftp.example.com"),
        "sftp_username": os.getenv("SFTP_USERNAME", "sftp_user"),
        "ppk_key_path": os.getenv("SFTP_PPK_PATH", "/path/to/key.ppk"),
        "passphrase": os.getenv("SFTP_PASSPHRASE", None),
        "db_uri": os.getenv("DB_URI", "postgresql://user:pass@localhost:5432/jinsudai")
    }
    
    # Créer le processeur
    processor = SFTPDataProcessor(**sftp_config)
    
    # Configurer le processeur
    if not processor.setup():
        print("Erreur lors de la configuration du processeur")
        return
    
    # Traiter un répertoire complet
    results = processor.process_directory(
        remote_directory="/data/incoming",
        archive_directory="/archived",
        file_pattern="*.csv"
    )
    
    # Afficher le résumé
    summary = processor.get_processing_summary(results)
    print(f"\nRésumé du traitement:")
    print(f"  Fichiers traités: {summary['total_files']}")
    print(f"  Succès: {summary['successful']}")
    print(f"  Échecs: {summary['failed']}")
    print(f"  Enregistrements traités: {summary['total_records_processed']}")
    print(f"  Prédictions mises à jour: {summary['total_predictions_updated']}")
    print(f"  Fichiers archivés: {summary['files_archived']}")
    print(f"  Taux de succès: {summary['success_rate']:.2%}")


def example_sftp_with_email_notifications():
    """
    Exemple d'utilisation du processeur SFTP avec notifications par email.
    """
    print("\n" + "="*60)
    print("EXEMPLE 3: Processeur SFTP avec notifications email")
    print("="*60 + "\n")
    
    # Configuration SFTP
    sftp_config = {
        "sftp_host": os.getenv("SFTP_HOST", "sftp.example.com"),
        "sftp_username": os.getenv("SFTP_USERNAME", "sftp_user"),
        "ppk_key_path": os.getenv("SFTP_PPK_PATH", "/path/to/key.ppk"),
        "passphrase": os.getenv("SFTP_PASSPHRASE", None),
        "db_uri": os.getenv("DB_URI", "postgresql://user:pass@localhost:5432/jinsudai")
    }
    
    # Configuration Email
    email_config = {
        "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "sender_email": os.getenv("SENDER_EMAIL", "sender@example.com"),
        "sender_password": os.getenv("SENDER_PASSWORD", "password"),
        "recipient_emails": os.getenv("RECIPIENT_EMAILS", "recipient@example.com").split(","),
        "use_tls": True
    }
    
    # Créer le notificateur email
    email_notifier = EmailNotifier(**email_config)
    
    # Créer le processeur avec notifications email
    processor = SFTPDataProcessor(
        **sftp_config,
        email_notifier=email_notifier
    )
    
    # Configurer le processeur
    if not processor.setup():
        print("Erreur lors de la configuration du processeur")
        return
    
    # Traiter un répertoire complet
    # Les notifications seront envoyées automatiquement:
    # - Lors de la réception de chaque fichier
    # - Après le traitement de chaque fichier (succès ou échec)
    # - À la fin du traitement par lots
    results = processor.process_directory(
        remote_directory="/data/incoming",
        archive_directory="/archived",
        file_pattern="*.csv"
    )
    
    # Afficher le résumé
    summary = processor.get_processing_summary(results)
    print(f"\nRésumé du traitement:")
    print(f"  Fichiers traités: {summary['total_files']}")
    print(f"  Succès: {summary['successful']}")
    print(f"  Échecs: {summary['failed']}")
    print(f"  Enregistrements traités: {summary['total_records_processed']}")
    print(f"  Prédictions mises à jour: {summary['total_predictions_updated']}")
    print(f"  Fichiers archivés: {summary['files_archived']}")
    print(f"  Taux de succès: {summary['success_rate']:.2%}")
    print(f"\n✅ Notifications email envoyées pour chaque événement")


def example_with_config():
    """
    Exemple d'utilisation avec la configuration YAML.
    """
    print("\n" + "="*60)
    print("EXEMPLE 4: Utilisation avec configuration YAML")
    print("="*60 + "\n")
    
    # Charger la configuration
    config = load_config(config_name="consumption")
    sftp_config = config.get("sftp", {})
    
    # Vérifier si SFTP est activé
    if not sftp_config.get("enabled", False):
        print("L'intégration SFTP est désactivée dans la configuration")
        return
    
    # Récupérer l'URI de la base de données depuis les variables d'environnement
    db_uri = os.getenv("DB_URI", "postgresql://user:pass@localhost:5432/jinsudai")
    
    # Créer le processeur avec la configuration
    processor = SFTPDataProcessor(
        sftp_host=sftp_config["host"],
        sftp_username=sftp_config["username"],
        ppk_key_path=sftp_config["ppk_key_path"],
        db_uri=db_uri,
        passphrase=sftp_config.get("passphrase"),
        sftp_port=sftp_config.get("port", 22),
        sftp_timeout=sftp_config.get("timeout", 30)
    )
    
    # Configurer et traiter
    if processor.setup():
        results = processor.process_directory(
            remote_directory=sftp_config["remote_directory"],
            archive_directory=sftp_config["archive_directory"],
            file_pattern=sftp_config.get("file_pattern", "*.csv"),
            temp_local_dir=sftp_config.get("temp_local_dir", "/tmp/sftp_temp")
        )
        
        summary = processor.get_processing_summary(results)
        print(f"Traitement terminé: {summary}")


def example_prefect_task():
    """
    Exemple d'utilisation avec les tâches Prefect.
    """
    print("\n" + "="*60)
    print("EXEMPLE 5: Utilisation avec tâches Prefect")
    print("="*60 + "\n")
    
    # Configuration
    task_config = {
        "sftp_host": os.getenv("SFTP_HOST", "sftp.example.com"),
        "sftp_username": os.getenv("SFTP_USERNAME", "sftp_user"),
        "ppk_key_path": os.getenv("SFTP_PPK_PATH", "/path/to/key.ppk"),
        "passphrase": os.getenv("SFTP_PASSPHRASE", None),
        "db_uri": os.getenv("DB_URI", "postgresql://user:pass@localhost:5432/jinsudai"),
        "remote_directory": "/data/incoming",
        "archive_directory": "/archived"
    }
    
    # Exécuter la tâche de traitement
    try:
        result = process_sftp_actual_values_task(**task_config)
        
        print(f"\nRésultat de la tâche:")
        print(f"  Fichiers traités: {result['summary']['total_files']}")
        print(f"  Succès: {result['summary']['successful']}")
        print(f"  Prédictions mises à jour: {result['summary']['total_predictions_updated']}")
        
    except Exception as e:
        print(f"Erreur lors de l'exécution de la tâche: {e}")


def example_list_files():
    """
    Exemple pour lister les fichiers disponibles sur SFTP.
    """
    print("\n" + "="*60)
    print("EXEMPLE 6: Lister les fichiers sur SFTP")
    print("="*60 + "\n")
    
    # Configuration
    config = {
        "sftp_host": os.getenv("SFTP_HOST", "sftp.example.com"),
        "sftp_username": os.getenv("SFTP_USERNAME", "sftp_user"),
        "ppk_key_path": os.getenv("SFTP_PPK_PATH", "/path/to/key.ppk"),
        "passphrase": os.getenv("SFTP_PASSPHRASE", None),
        "remote_directory": "/data/incoming"
    }
    
    # Lister les fichiers
    try:
        files = list_sftp_files_task(**config)
        
        print(f"Fichiers disponibles dans {config['remote_directory']}:")
        for file_info in files:
            file_type = "DIR" if file_info['is_directory'] else "FILE"
            print(f"  [{file_type}] {file_info['filename']} ({file_info['size']} octets)")
        
    except Exception as e:
        print(f"Erreur lors de la liste des fichiers: {e}")


def example_with_global_config():
    """
    Exemple d'utilisation avec la configuration globale (config.yaml) et resend_client.
    """
    print("\n" + "="*60)
    print("EXEMPLE 7: Utilisation avec config globale et Resend")
    print("="*60 + "\n")
    
    try:
        # Charger la configuration globale
        global_config = load_global_config()
        print(f"Configuration globale chargée")
        print(f"  Provider email: {global_config['email']['provider']}")
        print(f"  Environnement: {global_config.get('environment', 'dev')}")
        
        # Récupérer les configurations spécifiques
        email_config = get_email_config()
        sftp_config = get_sftp_config()
        db_uri = get_database_uri()
        
        # Créer le notificateur email depuis la configuration globale
        email_notifier = create_email_notifier_from_config()
        
        if email_notifier:
            print(f"✅ Notificateur email créé (provider: {email_config['provider']})")
        else:
            print("⚠️  Notificateur email non créé (désactivé dans la config)")
        
        # Configuration SFTP depuis la config globale
        sftp_processor_config = {
            "sftp_host": sftp_config.get("host"),
            "sftp_username": sftp_config.get("username"),
            "ppk_key_path": sftp_config.get("ppk_key_path"),
            "passphrase": sftp_config.get("passphrase"),
            "db_uri": db_uri,
            "email_notifier": email_notifier
        }
        
        # Créer le processeur SFTP avec la configuration globale
        processor = SFTPDataProcessor(**sftp_processor_config)
        
        if processor.setup():
            print("✅ Processeur SFTP configuré avec succès")
            
            # Traiter les fichiers (exemple)
            # results = processor.process_directory(
            #     remote_directory=sftp_config["remote_directory"],
            #     archive_directory=sftp_config["archive_directory"],
            #     file_pattern=sftp_config["file_pattern"]
            # )
            print("Prêt à traiter les fichiers avec Resend comme provider email")
        
    except FileNotFoundError as e:
        print(f"❌ Fichier de configuration global introuvable: {e}")
        print("   Assurez-vous que config.yaml existe à la racine du projet")
    except Exception as e:
        print(f"❌ Erreur lors de l'utilisation de la configuration globale: {e}")


def main():
    """
    Fonction principale pour exécuter les exemples.
    """
    print("\n" + "="*60)
    print("EXEMPLES D'UTILISATION DU CONNECTOR SFTP")
    print("="*60)
    
    # Vérifier les variables d'environnement
    if not os.getenv("SFTP_HOST"):
        print("\n⚠️  Attention: Variables d'environnement SFTP non définies")
        print("   Définissez les variables suivantes:")
        print("   - SFTP_HOST")
        print("   - SFTP_USERNAME")
        print("   - SFTP_PPK_PATH")
        print("   - SFTP_PASSPHRASE (optionnel)")
        print("   - DB_URI")
        print("   - SMTP_SERVER (pour les notifications email)")
        print("   - SENDER_EMAIL (pour les notifications email)")
        print("   - SENDER_PASSWORD (pour les notifications email)")
        print("   - RECIPIENT_EMAILS (pour les notifications email)")
        print("\n   Les exemples utiliseront des valeurs par défaut.\n")
    
    # Exécuter les exemples (commentez ceux que vous ne voulez pas exécuter)
    
    try:
        # Exemple 1: Utilisation basique
        # example_basic_sftp_usage()
        pass
    except Exception as e:
        print(f"Erreur dans l'exemple 1: {e}")
    
    try:
        # Exemple 2: Processeur de données
        # example_sftp_data_processor()
        pass
    except Exception as e:
        print(f"Erreur dans l'exemple 2: {e}")
    
    try:
        # Exemple 3: Processeur SFTP avec notifications email
        # example_sftp_with_email_notifications()
        pass
    except Exception as e:
        print(f"Erreur dans l'exemple 3: {e}")
    
    try:
        # Exemple 4: Utilisation avec configuration YAML
        # example_with_config()
        pass
    except Exception as e:
        print(f"Erreur dans l'exemple 4: {e}")
    
    try:
        # Exemple 5: Tâches Prefect
        # example_prefect_task()
        pass
    except Exception as e:
        print(f"Erreur dans l'exemple 5: {e}")
    
    try:
        # Exemple 6: Lister les fichiers
        # example_list_files()
        pass
    except Exception as e:
        print(f"Erreur dans l'exemple 6: {e}")
    
    try:
        # Exemple 7: Utilisation avec config globale et Resend
        # example_with_global_config()
        pass
    except Exception as e:
        print(f"Erreur dans l'exemple 7: {e}")
    
    print("\n" + "="*60)
    print("EXEMPLES TERMINÉS")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
