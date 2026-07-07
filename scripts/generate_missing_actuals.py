"""
Script pour générer les valeurs réelles manquantes en utilisant les méthodes existantes.

Ce script génère des valeurs réelles aléatoires basées sur les prédictions existantes,
uniquement pour les enregistrements qui ont une prédiction mais pas de valeur réelle.

Usage:
    # Générer pour toutes les prédictions sans valeurs réelles
    python scripts/generate_missing_actuals.py
    
    # Générer pour une plage de dates spécifique
    python scripts/generate_missing_actuals.py --start-date "2026-07-01" --end-date "2026-07-07"
    
    # Générer pour une version de modèle spécifique
    python scripts/generate_missing_actuals.py --model-version "35"
    
    # Mode dry-run (simulation)
    python scripts/generate_missing_actuals.py --dry-run
"""
import argparse
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from dotenv import find_dotenv, load_dotenv
import pandas as pd

# Charger les variables d'environnement
load_dotenv(find_dotenv(".env"), override=True)
load_dotenv(find_dotenv(".env.secrets"), override=True)

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.utils.data.database_handler import DatabaseHandler


class ActualValuesGenerator:
    """Classe pour générer les valeurs réelles manquantes"""
    
    def __init__(self, db_uri=None):
        self.db_handler = DatabaseHandler(db_uri)
        self.generated_count = 0
    
    def verify_connection(self):
        """Vérifie la connexion à la base de données"""
        if not self.db_handler.verify_connection():
            print("❌ Impossible de se connecter à la base de données")
            return False
        return True
    
    def get_predictions_without_actuals(self, start_date=None, end_date=None, model_version=None):
        """
        Récupère les prédictions sans valeurs réelles
        
        Args:
            start_date: Date de début (optionnel)
            end_date: Date de fin (optionnel)
            model_version: Version du modèle (optionnel)
        
        Returns:
            DataFrame des prédictions sans valeurs réelles ou None
        """
        conditions = ["actual_value IS NULL", "prediction IS NOT NULL"]
        params = []
        
        if start_date and end_date:
            conditions.append("target_timestamp >= %s")
            conditions.append("target_timestamp <= %s")
            params.extend([start_date, end_date])
        
        if model_version:
            conditions.append("model_version = %s")
            params.append(model_version)
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
        SELECT prediction_id, target_timestamp, prediction, model_version
        FROM consumption_predictions
        WHERE {where_clause}
        ORDER BY target_timestamp ASC
        """
        
        try:
            with self.db_handler._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, tuple(params))
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
            
            if rows:
                return pd.DataFrame(rows, columns=columns)
            return None
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des prédictions: {e}")
            return None
    
    def generate_actual_values(self, df_predictions, variation_percent=20):
        """
        Génère des valeurs réelles basées sur les prédictions
        
        Args:
            df_predictions: DataFrame des prédictions
            variation_percent: Pourcentage de variation (défaut: 20%)
        
        Returns:
            Tuple (prediction_ids, actual_values)
        """
        prediction_ids = []
        actual_values = []
        
        for _, row in df_predictions.iterrows():
            prediction_value = row['prediction']
            
            # Skip if prediction is None
            if prediction_value is None:
                print(f"⚠️  Prédiction None pour prediction_id {row['prediction_id']} - ignoré")
                continue
            
            # Générer une valeur aléatoire avec une variation de ±variation_percent%
            variation = random.uniform(-variation_percent / 100, variation_percent / 100)
            actual_value = prediction_value * (1 + variation)
            
            # S'assurer que la valeur est positive
            actual_value = max(0, actual_value)
            
            prediction_ids.append(row['prediction_id'])
            actual_values.append(actual_value)
        
        return prediction_ids, actual_values
    
    def update_actual_values(self, prediction_ids, actual_values, dry_run=False):
        """
        Met à jour les valeurs réelles dans la base de données
        
        Args:
            prediction_ids: Liste des IDs de prédictions
            actual_values: Liste des valeurs réelles
            dry_run: Si True, simule la mise à jour sans exécuter
        
        Returns:
            Nombre de mises à jour effectuées
        """
        if not prediction_ids:
            print("❌ Aucune valeur à mettre à jour")
            return 0
        
        if dry_run:
            print(f"🔒 Mode DRY-RUN: {len(prediction_ids)} valeurs seraient mises à jour")
            return len(prediction_ids)
        
        try:
            success = self.db_handler.update_actual_values(prediction_ids, actual_values)
            if success:
                self.generated_count += len(prediction_ids)
                return len(prediction_ids)
            return 0
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour des valeurs réelles: {e}")
            return 0
    
    def generate_for_date_range(self, start_date, end_date, variation_percent=20, dry_run=False):
        """
        Génère les valeurs réelles pour une plage de dates
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            variation_percent: Pourcentage de variation
            dry_run: Si True, simule sans exécuter
        
        Returns:
            Nombre de valeurs générées
        """
        print(f"=== Génération pour la plage {start_date} → {end_date} ===")
        
        df_predictions = self.get_predictions_without_actuals(start_date, end_date)
        
        if df_predictions is None or len(df_predictions) == 0:
            print(f"ℹ️  Aucune prédiction sans valeur réelle trouvée pour cette période")
            return 0
        
        print(f"🔍 {len(df_predictions)} prédictions sans valeur réelle trouvées")
        
        prediction_ids, actual_values = self.generate_actual_values(df_predictions, variation_percent)
        
        if not prediction_ids:
            print("❌ Aucune valeur générée")
            return 0
        
        print(f"📊 {len(prediction_ids)} valeurs réelles générées (variation ±{variation_percent}%)")
        
        if dry_run:
            print(f"🔒 Mode DRY-RUN: Aperçu des valeurs qui seraient générées:")
            for i in range(min(5, len(prediction_ids))):
                print(f"   ID {prediction_ids[i]}: {actual_values[i]:.2f} kWh")
            if len(prediction_ids) > 5:
                print(f"   ... et {len(prediction_ids) - 5} autres")
            return len(prediction_ids)
        
        # Confirmer
        response = input(f"⚠️  Confirmer la mise à jour de {len(prediction_ids)} valeurs réelles ? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Mise à jour annulée")
            return 0
        
        return self.update_actual_values(prediction_ids, actual_values, dry_run=False)
    
    def generate_for_model_version(self, model_version, variation_percent=20, dry_run=False):
        """
        Génère les valeurs réelles pour une version de modèle
        
        Args:
            model_version: Version du modèle
            variation_percent: Pourcentage de variation
            dry_run: Si True, simule sans exécuter
        
        Returns:
            Nombre de valeurs générées
        """
        print(f"=== Génération pour le modèle version {model_version} ===")
        
        df_predictions = self.get_predictions_without_actuals(model_version=model_version)
        
        if df_predictions is None or len(df_predictions) == 0:
            print(f"ℹ️  Aucune prédiction sans valeur réelle trouvée pour ce modèle")
            return 0
        
        print(f"🔍 {len(df_predictions)} prédictions sans valeur réelle trouvées")
        
        prediction_ids, actual_values = self.generate_actual_values(df_predictions, variation_percent)
        
        if not prediction_ids:
            print("❌ Aucune valeur générée")
            return 0
        
        print(f"📊 {len(prediction_ids)} valeurs réelles générées (variation ±{variation_percent}%)")
        
        if dry_run:
            print(f"🔒 Mode DRY-RUN: Aperçu des valeurs qui seraient générées:")
            for i in range(min(5, len(prediction_ids))):
                print(f"   ID {prediction_ids[i]}: {actual_values[i]:.2f} kWh")
            if len(prediction_ids) > 5:
                print(f"   ... et {len(prediction_ids) - 5} autres")
            return len(prediction_ids)
        
        # Confirmer
        response = input(f"⚠️  Confirmer la mise à jour de {len(prediction_ids)} valeurs réelles ? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Mise à jour annulée")
            return 0
        
        return self.update_actual_values(prediction_ids, actual_values, dry_run=False)
    
    def generate_all_missing(self, variation_percent=20, dry_run=False):
        """
        Génère les valeurs réelles pour toutes les prédictions sans valeurs réelles
        
        Args:
            variation_percent: Pourcentage de variation
            dry_run: Si True, simule sans exécuter
        
        Returns:
            Nombre de valeurs générées
        """
        print(f"=== Génération pour toutes les prédictions sans valeur réelle ===")
        
        df_predictions = self.get_predictions_without_actuals()
        
        if df_predictions is None or len(df_predictions) == 0:
            print(f"ℹ️  Aucune prédiction sans valeur réelle trouvée")
            return 0
        
        print(f"🔍 {len(df_predictions)} prédictions sans valeur réelle trouvées")
        print(f"📅 Période: {df_predictions['target_timestamp'].min()} → {df_predictions['target_timestamp'].max()}")
        
        prediction_ids, actual_values = self.generate_actual_values(df_predictions, variation_percent)
        
        if not prediction_ids:
            print("❌ Aucune valeur générée")
            return 0
        
        print(f"📊 {len(prediction_ids)} valeurs réelles générées (variation ±{variation_percent}%)")
        
        if dry_run:
            print(f"🔒 Mode DRY-RUN: Aperçu des valeurs qui seraient générées:")
            for i in range(min(5, len(prediction_ids))):
                print(f"   ID {prediction_ids[i]}: {actual_values[i]:.2f} kWh")
            if len(prediction_ids) > 5:
                print(f"   ... et {len(prediction_ids) - 5} autres")
            return len(prediction_ids)
        
        # Confirmer
        response = input(f"⚠️  Confirmer la mise à jour de {len(prediction_ids)} valeurs réelles ? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Mise à jour annulée")
            return 0
        
        return self.update_actual_values(prediction_ids, actual_values, dry_run=False)


def main():
    
    parser = argparse.ArgumentParser(description='Génère les valeurs réelles manquantes basées sur les prédictions')
    parser.add_argument('--db-uri', type=str, required=False, help='URI de connexion PostgreSQL (optionnel)')
    parser.add_argument('--dry-run', action='store_true', help='Simulation sans mise à jour réelle')
    parser.add_argument('--variation', type=int, default=20, help='Pourcentage de variation (défaut: 20%)')
    
    # Filtres
    parser.add_argument('--start-date', type=str, help='Date de début (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='Date de fin (YYYY-MM-DD)')
    parser.add_argument('--model-version', type=str, help='Version du modèle')
    
    args = parser.parse_args()
    
    # Récupérer l'URI de la base de données
    if args.db_uri is None:
        db_uri = os.getenv('PREDICTIONS_POSTGRES_URI')
        if not db_uri:
            print("❌ URI de base de données non fournie (utilisez --db-uri ou PREDICTIONS_POSTGRES_URI)")
            sys.exit(1)
    else:
        db_uri = args.db_uri
    
    print(f"=== Génération des valeurs réelles manquantes ===")
    if args.dry_run:
        print("🔒 MODE DRY-RUN: Aucune mise à jour réelle ne sera effectuée")
    print()
    
    # Initialiser le générateur
    generator = ActualValuesGenerator(db_uri)
    
    # Vérifier la connexion
    if not generator.verify_connection():
        sys.exit(1)
    
    # Exécuter la génération selon les filtres
    total_generated = 0
    
    if args.start_date and args.end_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
            total_generated = generator.generate_for_date_range(
                start_date, end_date, args.variation, args.dry_run
            )
        except ValueError as e:
            print(f"❌ Erreur de format de date: {e}")
            sys.exit(1)
    
    elif args.model_version:
        total_generated = generator.generate_for_model_version(
            args.model_version, args.variation, args.dry_run
        )
    
    else:
        total_generated = generator.generate_all_missing(args.variation, args.dry_run)
    
    # Résumé
    if not args.dry_run and total_generated > 0:
        print(f"\n✅ {total_generated} valeurs réelles générées et mises à jour")


if __name__ == "__main__":
    main()
