"""
Script pour récupérer les données de consommation depuis PostgreSQL et les sauvegarder en CSV.

Usage:
    python scripts/fetch_consumption_from_db.py --db_uri postgresql://user:password@host:port/database --output_path data/processed/raw_consumption_latest.csv --start_date 2024-01-01 --end_date 2024-01-31
"""
import argparse
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

def main():
    parser = argparse.ArgumentParser(description='Récupère les données de consommation depuis PostgreSQL')
    parser.add_argument('--db_uri', type=str, required=False, help='URI de connexion PostgreSQL')
    parser.add_argument('--output_path', type=str, default='data/processed/raw_consumption_latest.csv', help='Chemin de sortie CSV')
    parser.add_argument('--start_date', type=str, required=False, help='Date de début (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, required=False, help='Date de fin (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    print(f"=== Récupération des données de consommation depuis PostgreSQL ===")
    print(f"Output: {args.output_path}")
    
    # Récupérer l'URI de la base de données
    import os
    db_uri = args.db_uri or os.getenv('PREDICTIONS_POSTGRES_URI')
    
    if not db_uri:
        print(f"❌ Erreur: URI de base de données non fournie")
        print(f"   Définissez la variable d'environnement PREDICTIONS_POSTGRES_URI ou utilisez --db_uri")
        sys.exit(1)
    
    try:
        import sqlalchemy
        from sqlalchemy import create_engine, text
        
        # Créer la connexion
        engine = create_engine(db_uri)
        
        # Déterminer la requête SQL
        if args.start_date and args.end_date:
            query = f"""
            SELECT * FROM consumption_predictions 
            WHERE target_timestamp >= '{args.start_date}' AND target_timestamp <= '{args.end_date}'
            ORDER BY target_timestamp ASC
            """
            print(f"Période: {args.start_date} à {args.end_date}")
        else:
            # Récupérer les données du dernier jour
            query = """
            SELECT * FROM consumption_predictions 
            WHERE target_timestamp = (SELECT MAX(target_timestamp) FROM consumption_predictions)
            ORDER BY target_timestamp ASC
            """
            print(f"Période: dernier jour disponible")
        
        # Exécuter la requête
        df = pd.read_sql(query, engine)
        
        if df.empty:
            print(f"❌ Erreur: Aucune donnée trouvée")
            sys.exit(1)
        
        print(f"✅ {len(df)} enregistrements récupérés")
        
        # Sauvegarder en CSV
        output_path = Path(args.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        print(f"✅ Fichier sauvegardé: {output_path}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
