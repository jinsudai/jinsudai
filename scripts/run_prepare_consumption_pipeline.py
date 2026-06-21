"""
Script pour exécuter le pipeline de préparation des features consommation.

Usage:
    python scripts/run_prepare_consumption_pipeline.py --start_date 2024-01-01 --end_date 2024-01-31
"""
import argparse
import sys
from pathlib import Path

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from pipelines.preparation.prepare_consumption_pipeline import prepare_consumption_features_pipeline


def main():
    parser = argparse.ArgumentParser(
        description='Exécute le pipeline de préparation des features consommation avec stockage S3'
    )
    parser.add_argument('--start_date', type=str, required=True, help='Date de début (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, required=True, help='Date de fin (YYYY-MM-DD)')
    parser.add_argument('--raw_path', type=str, default='data/templates/raw_consumption.csv', help='Chemin vers le fichier brut PRM')
    parser.add_argument('--output_dir', type=str, default='data/processed/', help='Répertoire de sortie local')
    parser.add_argument('--no_upload_s3', action='store_true', help='Désactiver l\'upload S3')
    parser.add_argument('--s3_bucket', type=str, help='Nom du bucket S3 (défaut: depuis env AWS_BUCKET)')
    parser.add_argument('--s3_prefix', type=str, default='consumption/features/', help='Préfixe S3')
    
    args = parser.parse_args()
    
    print(f"=== Pipeline Préparation Features Consommation ===")
    print(f"Période: {args.start_date} à {args.end_date}")
    print(f"Fichier brut: {args.raw_path}")
    print(f"Répertoire sortie: {args.output_dir}")
    print(f"Upload S3: {not args.no_upload_s3}")
    print()
    
    # Vérifier que le fichier brut existe
    if not Path(args.raw_path).exists():
        print(f"❌ Erreur: Le fichier brut n'existe pas: {args.raw_path}")
        sys.exit(1)
    
    try:
        result = prepare_consumption_features_pipeline(
            start_date=args.start_date,
            end_date=args.end_date,
            raw_path=args.raw_path,
            output_dir=args.output_dir,
            upload_to_s3=not args.no_upload_s3,
            s3_bucket=args.s3_bucket,
            s3_prefix=args.s3_prefix
        )
        
        print(f"\n=== Résultat ===")
        print(f"Status: {result['status']}")
        
        if result['status'] == 'success':
            print(f"\n✅ Pipeline terminé avec succès")
            print(f"Weather: {result['local_paths']['weather']}")
            print(f"Holidays: {result['local_paths']['holidays']}")
            print(f"Features: {result['local_paths']['features']}")
            print(f"Train: {result['local_paths']['train']}")
            
            if result['s3'] and result['s3'].get('status') == 'success':
                print(f"\n✅ Upload S3 réussi")
                if 'features' in result['s3']:
                    print(f"S3 Features: {result['s3']['features'].get('s3_uri')}")
                if 'train' in result['s3']:
                    print(f"S3 Train: {result['s3']['train'].get('s3_uri')}")
            elif result['s3'] and result['s3'].get('status') == 'skipped':
                print(f"\nℹ️ Upload S3 ignoré: {result['s3']['reason']}")
            
            print(f"\nVous pouvez maintenant lancer le training avec:")
            print(f"python scripts/run_training_pipeline.py --features_path {result['local_paths']['train']}")
        else:
            print(f"\n❌ Erreur lors du pipeline: {result.get('error')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
