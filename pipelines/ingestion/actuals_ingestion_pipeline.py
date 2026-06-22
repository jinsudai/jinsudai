"""
Script simple pour exécuter le pipeline de mise à jour des valeurs réelles.

Usage:
    python pipelines/actual_values/actual_values_pipeline.py --db_uri postgresql://user:password@host:port/database
"""
import argparse
import sys
import os
from pathlib import Path

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.pipelines.Actual_values_pipeline import ActualValuesPipeline
from ml.config.global_config import load_config_with_environment

def main():
    parser = argparse.ArgumentParser(description='Exécute le pipeline de mise à jour des valeurs réelles')
    parser.add_argument('--db_uri', type=str, required=False, help='URI de connexion PostgreSQL')
    parser.add_argument('--config_name', type=str, default='consumption', help='Nom de la config (consumption, solar_production)')
    
    args = parser.parse_args()
    
    print(f"=== Pipeline de mise à jour des valeurs réelles ===")
    print(f"Config: {args.config_name}")
    print()
    
    # Charger la config pour les valeurs par défaut (avec environnement)
    from ml.config.global_config import load_config_with_environment
    config = load_config_with_environment(args.config_name)
    
    # Priorité : argument CLI > variable d'environnement > config
    if args.db_uri is not None:
        db_uri = args.db_uri
    elif os.getenv('PREDICTIONS_POSTGRES_URI'):
        db_uri = os.getenv('PREDICTIONS_POSTGRES_URI')
    else:
        db_uri = config.get('database', {}).get('uri')
    
    if not db_uri:
        print(f"❌ Erreur: URI de base de données non fournie")
        print(f"   Définissez la variable d'environnement PREDICTIONS_POSTGRES_URI ou utilisez --db_uri")
        print(f"   Exemple: export PREDICTIONS_POSTGRES_URI='postgresql://user:password@host:port/database'")
        sys.exit(1)
    
    try:
        # Initialiser le pipeline avec la configuration
        pipeline = ActualValuesPipeline(db_uri=db_uri, config=config)
        
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
