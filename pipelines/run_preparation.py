"""
Script wrapper pour le pipeline de préparation des features.

Ce script utilise la classe PreparationPipeline pour:
- Télécharger le dernier fichier trained depuis S3
- Calculer automatiquement la plage de dates
- Préparer les features consommation
- Récupérer les données réelles depuis la base de données
- Upload sur S3

Usage:
    python pipelines/preparation_pipeline.py \
        --raw_path data/templates/raw_consumption.csv \
        --db_uri postgresql://... \
        --output_dir data/processed/
"""
import argparse
import sys
import os
from pathlib import Path

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.pipelines.preparation_pipeline import PreparationPipeline


def main():
    parser = argparse.ArgumentParser(
        description='Pipeline pour préparer les features consommation et les stocker sur S3'
    )
    parser.add_argument('--raw_path', type=str, required=False, help='Chemin vers le fichier brut PRM (optionnel si --db_uri ou --use_database)')
    parser.add_argument('--output_dir', type=str, default='data/processed/', help='Répertoire de sortie local')
    parser.add_argument('--s3_bucket', type=str, help='Nom du bucket S3 (défaut: depuis env)')
    parser.add_argument('--db_uri', type=str, help='URI de connexion PostgreSQL pour charger les données depuis la base')
    parser.add_argument('--db_limit', type=int, help='Nombre maximum d\'enregistrements à récupérer depuis la base')
    parser.add_argument('--use_database', action='store_true', help='Utiliser la base de données (lit PREDICTIONS_POSTGRES_URI depuis l\'environnement)')

    args = parser.parse_args()

    # Déterminer l'URI de la base de données
    db_uri = args.db_uri
    if args.use_database and not db_uri:
        db_uri = os.environ.get('PREDICTIONS_POSTGRES_URI')

    # Vérifier que soit raw_path soit db_uri soit use_database est fourni
    if not args.raw_path and not db_uri and not args.use_database:
        parser.error("Au moins l'un des arguments --raw_path, --db_uri ou --use_database doit être fourni")

    try:
        # Initialiser le pipeline
        pipeline = PreparationPipeline(
            s3_bucket=args.s3_bucket,
            db_uri=db_uri
        )

        # Exécuter le pipeline
        result = pipeline.run(
            raw_path=args.raw_path,
            output_dir=args.output_dir,
            db_limit=args.db_limit
        )

        if result["status"] == "success":
            print("\n✅ Pipeline terminé avec succès")
            sys.exit(0)
        else:
            print(f"\n❌ Pipeline échoué: {result.get('error')}")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
