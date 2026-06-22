"""
Script simple pour exécuter le pipeline de génération de données consommation.

Usage:
    python scripts/run_data_pipeline_simple.py --start_date 2024-01-01 --end_date 2024-01-31
"""
import argparse
import sys
from pathlib import Path
import pandas as pd

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.connectors.weather.weather_api import WeatherAPI
from ml.connectors.holidays.holidays_api import VacancesAPI, JoursFeriesAPI

def main():
    parser = argparse.ArgumentParser(description='Exécute le pipeline de données consommation')
    parser.add_argument('--start_date', type=str, default='2024-01-01', help='Date de début (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default='2024-01-31', help='Date de fin (YYYY-MM-DD)')
    parser.add_argument('--raw_path', type=str, default='data/templates/test_raw_consumption.csv', help='Chemin vers le fichier brut')
    parser.add_argument('--output_dir', type=str, default='data/processed/', help='Répertoire de sortie')
    
    args = parser.parse_args()
    
    print(f"=== Pipeline de données consommation ===")
    print(f"Période: {args.start_date} à {args.end_date}")
    print(f"Fichier brut: {args.raw_path}")
    print(f"Répertoire sortie: {args.output_dir}")
    print()
    
    # Vérifier que le fichier brut existe
    if not Path(args.raw_path).exists():
        print(f"❌ Erreur: Le fichier brut n'existe pas: {args.raw_path}")
        sys.exit(1)
    
    # Créer le répertoire de sortie
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        # 1. Générer weather
        print("=== Étape 1: Génération weather ===")
        weather_path = Path(args.output_dir) / f"weather_{args.start_date}_to_{args.end_date}.parquet"
        weather_api = WeatherAPI(latitude=43.5283, longitude=5.4497, location_name="Aix en Provence")
        weather_df = weather_api.fetch_historical(start_date=args.start_date, end_date=args.end_date, hourly=True)
        weather_df.to_parquet(weather_path)
        print(f"✅ Weather généré: {weather_path}")
        
        # 2. Générer holidays
        print("\n=== Étape 2: Génération holidays ===")
        holidays_path = Path(args.output_dir) / f"holidays_{args.start_date}_to_{args.end_date}.parquet"
        
        # Récupérer vacances
        vacances_api = VacancesAPI()
        start_year = int(args.start_date.split('-')[0])
        end_year = int(args.end_date.split('-')[0])
        
        vacances_dfs = []
        for year in range(start_year, end_year + 1):
            df_vacances = vacances_api.fetch(year=year, zone="B")
            vacances_dfs.append(df_vacances)
        
        vacances_df = pd.concat(vacances_dfs, ignore_index=True)
        
        # Récupérer jours fériés
        feries_api = JoursFeriesAPI()
        feries_dfs = []
        for year in range(start_year, end_year + 1):
            df_feries = feries_api.fetch(year=year)
            feries_dfs.append(df_feries)
        
        feries_df = pd.concat(feries_dfs, ignore_index=True)
        
        # Combiner et sauvegarder
        holidays_df = vacances_df  # Simplification pour l'instant
        holidays_df.to_parquet(holidays_path)
        print(f"✅ Holidays généré: {holidays_path}")
        
        # 3. Préparer features (simplifié - utiliser les données brutes pour l'instant)
        print("\n=== Étape 3: Préparation features ===")
        features_path = Path(args.output_dir) / f"consumption_features_{args.start_date}_to_{args.end_date}.parquet"
        
        # Pour l'instant, créer des features simplifiées pour tester
        # Ceci est une version simplifiée pour tester
        raw_df = pd.read_csv(args.raw_path, sep=';')  # Utiliser le bon séparateur
        
        # Créer des features numériques simples
        features_df = pd.DataFrame()
        
        # Extraire la valeur de consommation
        if 'Valeur' in raw_df.columns:
            features_df['Valeur'] = pd.to_numeric(raw_df['Valeur'], errors='coerce')
        
        # Ajouter quelques features basées sur les dates
        if 'Horodate' in raw_df.columns:
            features_df['Heure'] = pd.to_datetime(raw_df['Horodate'], errors='coerce').dt.hour
            features_df['Jour'] = pd.to_datetime(raw_df['Horodate'], errors='coerce').dt.day
            features_df['Mois'] = pd.to_datetime(raw_df['Horodate'], errors='coerce').dt.month
        
        # Supprimer les lignes avec des valeurs manquantes
        features_df = features_df.dropna()
        
        features_df.to_parquet(features_path)
        print(f"✅ Features générés (simplifiés): {features_path}")
        print(f"Colonnes: {features_df.columns.tolist()}")
        
        print(f"\n=== Résultat ===")
        print(f"✅ Pipeline terminé avec succès")
        print(f"Weather: {weather_path}")
        print(f"Holidays: {holidays_path}")
        print(f"Features: {features_path}")
        print(f"\nVous pouvez maintenant lancer le training avec:")
        print(f"python scripts/run_training_pipeline_simple.py --features_path {features_path}")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
