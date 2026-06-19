"""
Script simple pour exécuter le pipeline d'entraînement consommation.

Usage:
    python scripts/run_training_pipeline.py --features_path data/processed/consumption_features.parquet
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

from ml.workflows.consumption_flow import consumption_training_only_pipeline

def main():
    parser = argparse.ArgumentParser(description='Exécute le pipeline d\'entraînement consommation')
    parser.add_argument('--features_path', type=str, required=True, help='Chemin vers le fichier de features')
    parser.add_argument('--config_path', type=str, default='src/configs/consumption.yaml', help='Chemin vers la config')
    
    args = parser.parse_args()
    
    print(f"=== Pipeline d'entraînement consommation ===")
    print(f"Features: {args.features_path}")
    print(f"Config: {args.config_path}")
    print()
    
    # Vérifier que le fichier de features existe
    if not Path(args.features_path).exists():
        print(f"❌ Erreur: Le fichier features n'existe pas: {args.features_path}")
        sys.exit(1)
    
    try:
        result = consumption_training_only_pipeline(
            features_path=args.features_path,
            config_path=args.config_path
        )
        
        print(f"\n=== Résultat ===")
        print(f"Status: {result['status']}")
        
        if result['status'] == 'success':
            print(f"\n✅ Entraînement terminé avec succès")
            print(f"Métriques d'évaluation: {result['evaluation']['metrics']}")
            print(f"Model URI: {result['staging']['model_uri']}")
        else:
            print(f"\n❌ Erreur lors de l'entraînement")
            
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
