"""
Script simple pour exécuter le pipeline d'entraînement consommation.

Usage:
    python pipelines/training/training_pipeline.py --features_path data/processed/consumption_features.parquet
"""
import argparse
import sys
from pathlib import Path

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.utils.pipelines.training_pipeline import MLPipeline

def main():
    parser = argparse.ArgumentParser(description='Exécute le pipeline d\'entraînement consommation')
    parser.add_argument('--features_path', type=str, required=True, help='Chemin vers le fichier de features')
    parser.add_argument('--config_name', type=str, default='consumption', help='Nom de la config (consumption, solar_production)')
    
    args = parser.parse_args()
    
    print(f"=== Pipeline d'entraînement consommation ===")
    print(f"Features: {args.features_path}")
    print(f"Config: {args.config_name}")
    print()
    
    # Vérifier que le fichier de features existe
    if not Path(args.features_path).exists():
        print(f"❌ Erreur: Le fichier features n'existe pas: {args.features_path}")
        sys.exit(1)
    
    try:
        # Initialiser le pipeline
        pipeline = MLPipeline(config_name=args.config_name)
        
        # Exécuter le pipeline complet
        success = pipeline.run_full_pipeline(data_path=args.features_path)
        
        if success:
            print(f"\n✅ Pipeline terminé avec succès")
            print(f"Métriques: {pipeline.metrics}")
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
