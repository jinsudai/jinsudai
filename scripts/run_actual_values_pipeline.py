"""
Script simple pour exécuter le pipeline de mise à jour des valeurs réelles (sans Prefect).

Usage:
    python scripts/run_actual_values_pipeline.py --db_uri postgresql://user:password@host:port/database
"""
import argparse
import sys
from pathlib import Path

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.pipelines.Actual_values_pipeline import ActualValuesPipeline
from ml.config import load_config

def main():
    parser = argparse.ArgumentParser(description='Exécute le pipeline de mise à jour des valeurs réelles')
    parser.add_argument('--db_uri', type=str, required=False, help='URI de connexion PostgreSQL')
    parser.add_argument('--config_name', type=str, default='consumption', help='Nom de la config (consumption, solar_production)')
    
    args = parser.parse_args()
    
    print(f"=== Pipeline de mise à jour des valeurs réelles (sans Prefect) ===")
    print(f"Config: {args.config_name}")
    print()
    
    # Charger la config pour les valeurs par défaut
    config = load_config(config_name=args.config_name)
    
    if args.db_uri is None:
        db_uri = config.get('database', {}).get('uri')
    else:
        db_uri = args.db_uri
    
    if not db_uri:
        print(f"❌ Erreur: URI de base de données non fournie et non trouvée dans la config")
        sys.exit(1)
    
    try:
        # Initialiser le pipeline
        pipeline = ActualValuesPipeline(db_uri=db_uri)
        
        # Exécuter le pipeline complet
        success, results = pipeline.run_full_pipeline()
        
        if success:
            print(f"\n✅ Pipeline terminé avec succès")
            print(f"Enregistrements mis à jour: {pipeline.updated_count}")
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
