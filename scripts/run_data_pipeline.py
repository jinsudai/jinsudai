"""
Script simple pour exécuter le pipeline de génération de données consommation.

Usage:
    python scripts/run_data_pipeline.py --start_date 2024-01-01 --end_date 2024-01-31
"""
import argparse
import sys
from pathlib import Path

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Désactiver la connexion Prefect pour l'exécution locale
import os
os.environ['PREFECT_API_URL'] = 'http://localhost:4200/api'
os.environ['PREFECT_LOCAL_MODE'] = 'true'

from ml.workflows.consumption_flow import consumption_data_pipeline

def main():
    parser = argparse.ArgumentParser(description='Exécute le pipeline de données consommation')
    parser.add_argument('--start_date', type=str, default='2024-01-01', help='Date de début (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default='2024-01-31', help='Date de fin (YYYY-MM-DD)')
    parser.add_argument('--raw_path', type=str, default='data/templates/raw_consumption.csv', help='Chemin vers le fichier brut')
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
    
    try:
        result = consumption_data_pipeline(
            start_date=args.start_date,
            end_date=args.end_date,
            raw_path=args.raw_path,
            output_dir=args.output_dir
        )
        
        print(f"\n=== Résultat ===")
        print(f"Status: {result['status']}")
        
        if result['status'] == 'success':
            print(f"\n✅ Pipeline de données terminé avec succès")
            print(f"Weather: {result['weather_path']}")
            print(f"Holidays: {result['holidays_path']}")
            print(f"Features: {result['features_path']}")
            print(f"\nVous pouvez maintenant lancer le training avec:")
            print(f"python scripts/run_training_pipeline.py --features_path {result['features_path']}")
        else:
            print(f"\n❌ Erreur lors du pipeline de données")
            
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
