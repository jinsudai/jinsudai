"""
Script pour télécharger le dernier fichier train.parquet depuis S3.

Usage:
    python scripts/download_latest_train_from_s3.py --environment dev
    python scripts/download_latest_train_from_s3.py --environment prod --output_path data/latest_train.parquet
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.utils.s3_handler import S3Handler
from ml.config import load_config


def download_latest_train_from_s3(
    environment: str = "dev",
    output_path: str = None,
    bucket: str = None,
    prefix: str = None
) -> dict:
    """
    Télécharge le dernier fichier train.parquet depuis S3.
    
    Args:
        environment: Environnement (dev, test, prod)
        output_path: Chemin local de destination (optionnel)
        bucket: Nom du bucket S3 (optionnel, utilise config par défaut)
        prefix: Préfixe S3 (optionnel, utilise config par défaut)
    
    Returns:
        dict: Résultat de l'opération
    """
    print(f"=== Téléchargement du dernier train.parquet depuis S3 ===")
    print(f"Environnement: {environment}")
    
    # Charger la configuration
    config = load_config('config.yaml')
    s3_config = config.get('s3', {})
    
    # Utiliser les paramètres fournis ou ceux de la config
    bucket = bucket or s3_config.get('bucket', 'data-store')
    prefix = prefix or s3_config.get('prefix', 'weather')
    
    # Déterminer le préfixe spécifique pour l'environnement
    env_prefix = f"{prefix}/{environment}"
    
    print(f"Bucket S3: {bucket}")
    print(f"Préfixe S3: {env_prefix}")
    
    # Initialiser le handler S3
    s3_handler = S3Handler(bucket=bucket)
    
    if not s3_handler.s3_enabled:
        print("❌ S3 non disponible (credentials manquants)")
        return {
            "status": "error",
            "reason": "S3 credentials not available"
        }
    
    # Lister les fichiers train.parquet
    print(f"Recherche des fichiers train.parquet dans s3://{bucket}/{env_prefix}/...")
    files = s3_handler.list_files(prefix=env_prefix)
    
    # Filtrer les fichiers train.parquet
    train_files = [f for f in files if 'train' in f and f.endswith('.parquet')]
    
    if not train_files:
        print(f"❌ Aucun fichier train.parquet trouvé dans s3://{bucket}/{env_prefix}/")
        return {
            "status": "error",
            "reason": "No train.parquet files found"
        }
    
    print(f"📂 {len(train_files)} fichier(s) train.parquet trouvé(s):")
    for f in train_files:
        print(f"  - {f}")
    
    # Trouver le plus récent (basé sur le nom de fichier qui contient généralement la date)
    # On suppose que les fichiers sont nommés avec un timestamp
    train_files_sorted = sorted(train_files, reverse=True)
    latest_file = train_files_sorted[0]
    
    print(f"\n📥 Fichier le plus récent: {latest_file}")
    
    # Déterminer le chemin local de destination
    if output_path is None:
        # Utiliser le chemin par défaut selon l'environnement
        if environment == "prod":
            output_path = "data/prod/train_consumption.parquet"
        elif environment == "test":
            output_path = "data/test/train_consumption.parquet"
        else:
            output_path = "data/dev/train_consumption.parquet"
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"📂 Destination locale: {output_path}")
    
    # Télécharger le fichier
    result = s3_handler.download_file(
        s3_key=latest_file,
        local_path=str(output_path),
        overwrite=True
    )
    
    if result["status"] == "success":
        print(f"✅ Fichier téléchargé avec succès: {output_path}")
        print(f"   Taille: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
    else:
        print(f"❌ Erreur lors du téléchargement: {result.get('reason')}")
    
    return result


def main():
    parser = argparse.ArgumentParser(description='Télécharge le dernier train.parquet depuis S3')
    parser.add_argument('--environment', type=str, default='dev', 
                        help='Environnement (dev, test, prod)')
    parser.add_argument('--output_path', type=str, default=None, 
                        help='Chemin local de destination (optionnel)')
    parser.add_argument('--bucket', type=str, default=None, 
                        help='Nom du bucket S3 (optionnel)')
    parser.add_argument('--prefix', type=str, default=None, 
                        help='Préfixe S3 (optionnel)')
    
    args = parser.parse_args()
    
    try:
        result = download_latest_train_from_s3(
            environment=args.environment,
            output_path=args.output_path,
            bucket=args.bucket,
            prefix=args.prefix
        )
        
        if result["status"] == "success":
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
