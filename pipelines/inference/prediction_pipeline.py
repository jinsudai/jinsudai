"""
Script simple pour exécuter le pipeline de prédiction (sans Prefect).

Usage:
    python pipelines/prediction/prediction_pipeline.py --n_days 3
"""
import argparse
import os
import sys
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

# Charger les variables d'environnement
load_dotenv(find_dotenv(".env"), override=True)
load_dotenv(find_dotenv(".env.secrets"), override=True)

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.pipelines.Prediction_pipeline import PredictionPipeline
from ml.config.global_config import load_config_with_environment

def main():
    parser = argparse.ArgumentParser(description='Exécute le pipeline de prédiction')
    parser.add_argument('--model_name', type=str, default=None, help='Nom du modèle dans MLflow (utilise la config par défaut)')
    parser.add_argument('--config_name', type=str, default='consumption', help='Nom de la config (consumption, solar_production)')
    parser.add_argument('--n_days', type=int, default=3, help='Nombre de jours de prédictions')
    parser.add_argument('--n_samples_per_day', type=int, default=48, help='Nombre d\'échantillons par jour')
    parser.add_argument('--alias_prod', type=str, default='prod', help='Alias pour la production')
    parser.add_argument('--db_uri', type=str, required=False, help='URI de connexion PostgreSQL (optionnel)')
    
    args = parser.parse_args()
    
    # Charger la config pour les valeurs par défaut (avec environnement)
    from ml.config.global_config import load_config_with_environment
    config = load_config_with_environment(args.config_name)
    
    # Utiliser le nom du modèle depuis la config si non fourni
    if args.model_name is None:
        args.model_name = config.get('mlflow', {}).get('model_name', 'model')
    
    print(f"=== Pipeline de prédiction (sans Prefect) ===")
    print(f"Modèle: {args.model_name}")
    print(f"Config: {args.config_name}")
    print(f"Jours: {args.n_days}")
    print(f"Échantillons/jour: {args.n_samples_per_day}")
    print()
    
    mlflow_uri = config.get('mlflow', {}).get('tracking_uri')
    experiment_name = config.get('mlflow', {}).get('experiment_name')
    
    if args.db_uri is None:
        db_uri = os.getenv('PREDICTIONS_POSTGRES_URI') or config.get('database', {}).get('uri')
    else:
        db_uri = args.db_uri
    
    try:
        # Initialiser le pipeline
        pipeline = PredictionPipeline(
            mlflow_uri=mlflow_uri,
            experiment_name=experiment_name,
            db_uri=db_uri
        )
        
        # Exécuter le pipeline complet
        success, results = pipeline.run_full_pipeline(
            model_name=args.model_name,
            feature_columns=None,
            n_days=args.n_days,
            n_samples_per_day=args.n_samples_per_day,
            alias_prod=args.alias_prod
        )
        
        if success:
            print(f"\n✅ Pipeline terminé avec succès")
            df_predictions = pipeline.get_predictions_df()
            if df_predictions is not None:
                print(f"Prédictions générées: {len(df_predictions)} échantillons")
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
