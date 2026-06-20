"""
Script simple pour exécuter le pipeline d'ingestion SFTP (sans Prefect).

Usage:
    python pipelines/sftp_ingestion/sftp_ingestion_pipeline.py --sftp_host example.com --sftp_username user
"""
import argparse
import sys
from pathlib import Path

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.utils.pipelines.sftp_ingestion_pipeline import run_sftp_ingestion_pipeline, load_sftp_config
from ml.config import load_config

def main():
    parser = argparse.ArgumentParser(description='Exécute le pipeline d\'ingestion SFTP')
    parser.add_argument('--sftp_host', type=str, required=False, help='Hôte SFTP')
    parser.add_argument('--sftp_username', type=str, required=False, help='Nom d\'utilisateur SFTP')
    parser.add_argument('--ssh_private_key_b64', type=str, required=False, help='Clé privée SSH encodée en base64')
    parser.add_argument('--ssh_private_key_content', type=str, required=False, help='Contenu de la clé privée SSH')
    parser.add_argument('--db_uri', type=str, required=False, help='URI de connexion PostgreSQL')
    parser.add_argument('--remote_directory', type=str, default='/data/incoming', help='Répertoire distant SFTP')
    parser.add_argument('--archive_directory', type=str, default='/data/archived', help='Répertoire d\'archive SFTP')
    parser.add_argument('--passphrase', type=str, required=False, help='Phrase de passe pour la clé SSH')
    parser.add_argument('--sftp_port', type=int, default=22, help='Port SFTP')
    parser.add_argument('--sftp_timeout', type=int, default=30, help='Timeout SFTP')
    parser.add_argument('--file_pattern', type=str, default='*.csv', help='Pattern de fichiers')
    parser.add_argument('--temp_local_dir', type=str, default='/tmp/sftp_temp', help='Répertoire temporaire local')
    parser.add_argument('--config_name', type=str, default='consumption', help='Nom de la config (consumption, solar_production)')
    parser.add_argument('--use_env_config', action='store_true', help='Utiliser la configuration depuis les variables d\'environnement')
    
    args = parser.parse_args()
    
    print(f"=== Pipeline d'ingestion SFTP (sans Prefect) ===")
    print(f"Config: {args.config_name}")
    print()
    
    try:
        if args.use_env_config:
            # Charger la configuration depuis les variables d'environnement
            print("Chargement de la configuration SFTP depuis les variables d'environnement...")
            sftp_config = load_sftp_config()
            
            result = run_sftp_ingestion_pipeline(
                sftp_host=sftp_config['host'],
                sftp_username=sftp_config['username'],
                ssh_private_key_b64=sftp_config.get('ssh_private_key_b64'),
                ssh_private_key_content=sftp_config.get('ssh_private_key_content'),
                db_uri=args.db_uri,
                remote_directory=sftp_config['remote_directory'],
                archive_directory=sftp_config['archive_directory'],
                passphrase=sftp_config.get('passphrase'),
                sftp_port=sftp_config['port'],
                sftp_timeout=sftp_config['timeout'],
                file_pattern=sftp_config['file_pattern'],
                temp_local_dir=sftp_config['temp_local_dir']
            )
        else:
            # Utiliser les arguments en ligne de commande
            if not args.sftp_host or not args.sftp_username:
                print(f"❌ Erreur: sftp_host et sftp_username sont requis si use_env_config n'est pas activé")
                sys.exit(1)
            
            # Charger la config pour les valeurs par défaut
            config = load_config(config_name=args.config_name)
            
            if args.db_uri is None:
                db_uri = config.get('database', {}).get('uri')
            else:
                db_uri = args.db_uri
            
            result = run_sftp_ingestion_pipeline(
                sftp_host=args.sftp_host,
                sftp_username=args.sftp_username,
                ssh_private_key_b64=args.ssh_private_key_b64,
                ssh_private_key_content=args.ssh_private_key_content,
                db_uri=db_uri,
                remote_directory=args.remote_directory,
                archive_directory=args.archive_directory,
                passphrase=args.passphrase,
                sftp_port=args.sftp_port,
                sftp_timeout=args.sftp_timeout,
                file_pattern=args.file_pattern,
                temp_local_dir=args.temp_local_dir
            )
        
        if result['status'] == 'success':
            print(f"\n✅ Pipeline terminé avec succès")
            print(f"Fichiers traités: {result['files_count']}")
            print(f"Résumé: {result['summary']}")
        elif result['status'] == 'no_files':
            print(f"\nℹ️ Aucun fichier à traiter")
        else:
            print(f"\n❌ Erreur lors de l'exécution du pipeline")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
