"""
Script pour générer des prédictions à partir d'une date spécifique.

Usage:
    python scripts/generate_predictions_from_date.py --start-date "2024-01-15" --n-days 3
    python scripts/generate_predictions_from_date.py --start-date "2024-01-15 14:30" --n-days 7 --config-name consumption
"""
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

# Charger les variables d'environnement
load_dotenv(find_dotenv(".env"), override=True)
load_dotenv(find_dotenv(".env.secrets"), override=True)

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.pipelines.inference import InferencePipeline
from ml.config.global_config import load_config_with_environment
from ml.utils.data.data_prediction import generate_inference_data


def main():
    parser = argparse.ArgumentParser(description='Génère des prédictions à partir d\'une date spécifique')
    parser.add_argument('--start-date', type=str, required=True, 
                        help='Date de début (format: "YYYY-MM-DD" ou "YYYY-MM-DD HH:MM")')
    parser.add_argument('--n-days', type=int, default=3, help='Nombre de jours de prédictions')
    parser.add_argument('--n-samples-per-day', type=int, default=48, help='Nombre d\'échantillons par jour')
    parser.add_argument('--model-name', type=str, default=None, help='Nom du modèle dans MLflow')
    parser.add_argument('--config-name', type=str, default='consumption', help='Nom de la config (consumption, solar_production)')
    parser.add_argument('--alias-prod', type=str, default='prod', help='Alias pour la production')
    parser.add_argument('--db-uri', type=str, required=False, help='URI de connexion PostgreSQL (optionnel)')
    parser.add_argument('--output-csv', type=str, required=False, help='Chemin pour sauvegarder les prédictions en CSV (optionnel)')
    parser.add_argument('--skip-model', action='store_true', help='Générer uniquement les données d\'inférence sans charger le modèle')
    
    args = parser.parse_args()
    
    # Parser la date de début
    try:
        if len(args.start_date.split()) == 1:
            # Format: YYYY-MM-DD (utilise 00:00 comme heure par défaut)
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        else:
            # Format: YYYY-MM-DD HH:MM
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d %H:%M")
    except ValueError as e:
        print(f"❌ Erreur de format de date: {e}")
        print("Formats acceptés: 'YYYY-MM-DD' ou 'YYYY-MM-DD HH:MM'")
        sys.exit(1)
    
    # Charger la config
    config = load_config_with_environment(args.config_name)
    
    # Utiliser le nom du modèle depuis la config si non fourni
    if args.model_name is None:
        args.model_name = config.get('mlflow', {}).get('model_name', 'model')
    
    print(f"=== Génération de prédictions ===")
    print(f"Date de début: {start_date}")
    print(f"Jours: {args.n_days}")
    print(f"Échantillons/jour: {args.n_samples_per_day}")
    print(f"Modèle: {args.model_name}")
    print(f"Config: {args.config_name}")
    print()
    
    mlflow_uri = config.get('mlflow', {}).get('tracking_uri')
    experiment_name = config.get('mlflow', {}).get('experiment_name')
    
    if args.db_uri is None:
        db_uri = os.getenv('PREDICTIONS_POSTGRES_URI') or config.get('database', {}).get('uri')
    else:
        db_uri = args.db_uri
    
    try:
        # Si skip-model, générer uniquement les données d'inférence
        if args.skip_model:
            print(f"=== Mode: Génération des données d'inférence uniquement ===")
            df_inference = generate_inference_data(
                n_days=args.n_days,
                n_samples_per_day=args.n_samples_per_day,
                feature_columns=None,
                start_date=start_date,
                config_name=args.config_name
            )
            
            if df_inference is None or len(df_inference) == 0:
                print("❌ Erreur lors de la génération des données d'inférence")
                sys.exit(1)
            
            print(f"✅ Données générées: {len(df_inference)} échantillons")
            print(f"Premier timestamp: {df_inference['Horodate'].iloc[0]}")
            print(f"Dernier timestamp: {df_inference['Horodate'].iloc[-1]}")
            
            if args.output_csv:
                df_inference.to_csv(args.output_csv, index=False)
                print(f"✅ Données sauvegardées dans: {args.output_csv}")
            
            print(f"\nAperçu des données:")
            print(df_inference.head(10).to_string())
            sys.exit(0)
        
        # Initialiser le pipeline
        pipeline = InferencePipeline(
            mlflow_uri=mlflow_uri,
            experiment_name=experiment_name,
            db_uri=db_uri,
            config=config
        )
        
        # Setup et chargement du modèle
        if not pipeline.setup():
            print("❌ Erreur lors de la configuration du pipeline")
            sys.exit(1)
        
        if not pipeline.load_model(args.model_name, alias_prod=args.alias_prod):
            print("❌ Erreur lors du chargement du modèle")
            sys.exit(1)
        
        # Générer les données d'inférence avec la date spécifique
        print(f"=== Génération des données d'inférence à partir du {start_date} ===")
        df_inference = generate_inference_data(
            n_days=args.n_days,
            n_samples_per_day=args.n_samples_per_day,
            feature_columns=None,
            start_date=start_date,
            config_name=args.config_name
        )
        
        if df_inference is None or len(df_inference) == 0:
            print("❌ Erreur lors de la génération des données d'inférence")
            sys.exit(1)
        
        print(f"Données générées: {len(df_inference)} échantillons")
        print(f"Premier timestamp: {df_inference['Horodate'].iloc[0]}")
        print(f"Dernier timestamp: {df_inference['Horodate'].iloc[-1]}")
        print()
        
        # Charger les données dans le pipeline
        if not pipeline.set_inference_data(df_inference):
            print("❌ Erreur lors du chargement des données dans le pipeline")
            sys.exit(1)
        
        # Exécuter les prédictions
        if not pipeline.run_predictions(feature_columns=None):
            print("❌ Erreur lors de l'exécution des prédictions")
            sys.exit(1)
        
        df_predictions = pipeline.get_predictions_df()
        print(f"✅ Prédictions générées: {len(df_predictions)} échantillons")
        print()
        
        # Sauvegarder en CSV si demandé
        if args.output_csv:
            df_predictions.to_csv(args.output_csv, index=False)
            print(f"✅ Prédictions sauvegardées dans: {args.output_csv}")
        
        # Stocker en base de données si URI fournie
        if db_uri:
            if not pipeline.store_predictions():
                print("❌ Erreur lors du stockage en base de données")
                sys.exit(1)
            print("✅ Prédictions stockées en base de données")
            
            # Vérifier les résultats
            recent = pipeline.verify_results()
            if recent is not None:
                print(f"\nPrédictions récentes en base:\n{recent.to_string()}")
        
        print(f"\n=== Résumé ===")
        print(f"Prédictions générées du {df_predictions['Horodate'].iloc[0]} au {df_predictions['Horodate'].iloc[-1]}")
        print(f"Total: {len(df_predictions)} échantillons")
        
        # Afficher un aperçu des prédictions
        print(f"\nAperçu des prédictions:")
        print(df_predictions[['Horodate', 'prediction']].head(10).to_string(index=False))
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
