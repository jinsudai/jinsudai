"""
Script pour nettoyer les données corrompues en base de données PostgreSQL.

Usage:
    # Supprimer par plage de dates
    python scripts/clean_corrupted_data.py --start-date "2024-01-01" --end-date "2024-01-31"
    
    # Supprimer par ID de modèle
    python scripts/clean_corrupted_data.py --model-version "35"
    
    # Supprimer par run_id
    python scripts/clean_corrupted_data.py --run-id "19ea681ec55e4aeaac12dea05510f0b1"
    
    # Supprimer les prédictions sans valeurs réelles (NULL)
    python scripts/clean_corrupted_data.py --null-actuals
    
    # Supprimer les prédictions aberrantes (valeurs extrêmes)
    python scripts/clean_corrupted_data.py --outliers --min-value 0 --max-value 10000
    
    # Mode dry-run (simulation sans suppression)
    python scripts/clean_corrupted_data.py --start-date "2024-01-01" --dry-run
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

from ml.utils.data.database_handler import DatabaseHandler


class DataCleaner:
    """Classe pour nettoyer les données corrompues en base de données"""
    
    def __init__(self, db_uri=None):
        self.db_handler = DatabaseHandler(db_uri)
        self.deleted_count = 0
    
    def verify_connection(self):
        """Vérifie la connexion à la base de données"""
        if not self.db_handler.verify_connection():
            print("❌ Impossible de se connecter à la base de données")
            return False
        return True
    
    def get_stats(self):
        """Récupère les statistiques actuelles de la base"""
        stats = self.db_handler.get_prediction_stats()
        if stats:
            print(f"📊 Statistiques actuelles: {stats['total_predictions']} prédictions")
        return stats
    
    def delete_by_date_range(self, start_date, end_date, dry_run=False):
        """
        Supprime les prédictions pour une plage de dates
        
        Args:
            start_date: Date de début (datetime ou string)
            end_date: Date de fin (datetime ou string)
            dry_run: Si True, simule la suppression sans exécuter
        """
        # D'abord compter les enregistrements affectés
        count_query = """
        SELECT COUNT(*) FROM consumption_predictions
        WHERE target_timestamp >= %s AND target_timestamp <= %s
        """
        
        try:
            # Phase 1: Compter avec une connexion temporaire
            with self.db_handler._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(count_query, (start_date, end_date))
                    count = cursor.fetchone()[0]
                    
                    if count == 0:
                        print(f"ℹ️  Aucune prédiction trouvée entre {start_date} et {end_date}")
                        return 0
                    
                    print(f"🔍 {count} prédictions trouvées entre {start_date} et {end_date}")
                    
                    if dry_run:
                        print(f"🔒 Mode DRY-RUN: {count} prédictions seraient supprimées")
                        return count
                    
            # Phase 2: Confirmation et suppression avec une nouvelle connexion
            response = input(f"⚠️  Confirmer la suppression de {count} prédictions ? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Suppression annulée")
                return 0
            
            # Supprimer avec une nouvelle connexion
            query = """
            DELETE FROM consumption_predictions
            WHERE target_timestamp >= %s AND target_timestamp <= %s
            """
            with self.db_handler._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (start_date, end_date))
                    conn.commit()
                    self.deleted_count += count
                    print(f"✅ {count} prédictions supprimées")
                    return count
                    
        except Exception as e:
            print(f"❌ Erreur lors de la suppression par date: {e}")
            return 0
    
    def delete_by_model_version(self, model_version, dry_run=False):
        """
        Supprime les prédictions pour une version de modèle spécifique
        
        Args:
            model_version: Version du modèle (string)
            dry_run: Si True, simule la suppression sans exécuter
        """
        query = """
        DELETE FROM consumption_predictions
        WHERE model_version = %s
        """
        
        count_query = """
        SELECT COUNT(*) FROM consumption_predictions
        WHERE model_version = %s
        """
        
        try:
            with self.db_handler._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(count_query, (model_version,))
                    count = cursor.fetchone()[0]
                    
                    if count == 0:
                        print(f"ℹ️  Aucune prédiction trouvée pour le modèle version {model_version}")
                        return 0
                    
                    print(f"🔍 {count} prédictions trouvées pour le modèle version {model_version}")
                    
                    if dry_run:
                        print(f"🔒 Mode DRY-RUN: {count} prédictions seraient supprimées")
                        return count
                    
                    response = input(f"⚠️  Confirmer la suppression de {count} prédictions ? (yes/no): ")
                    if response.lower() != 'yes':
                        print("❌ Suppression annulée")
                        return 0
                    
                    cursor.execute(query, (model_version,))
                    conn.commit()
                    self.deleted_count += count
                    print(f"✅ {count} prédictions supprimées")
                    return count
                    
        except Exception as e:
            print(f"❌ Erreur lors de la suppression par version de modèle: {e}")
            return 0
    
    def delete_by_run_id(self, run_id, dry_run=False):
        """
        Supprime les prédictions pour un run_id spécifique
        
        Args:
            run_id: ID du run MLflow
            dry_run: Si True, simule la suppression sans exécuter
        """
        query = """
        DELETE FROM consumption_predictions
        WHERE run_id = %s
        """
        
        count_query = """
        SELECT COUNT(*) FROM consumption_predictions
        WHERE run_id = %s
        """
        
        try:
            with self.db_handler._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(count_query, (run_id,))
                    count = cursor.fetchone()[0]
                    
                    if count == 0:
                        print(f"ℹ️  Aucune prédiction trouvée pour le run_id {run_id}")
                        return 0
                    
                    print(f"🔍 {count} prédictions trouvées pour le run_id {run_id}")
                    
                    if dry_run:
                        print(f"🔒 Mode DRY-RUN: {count} prédictions seraient supprimées")
                        return count
                    
                    response = input(f"⚠️  Confirmer la suppression de {count} prédictions ? (yes/no): ")
                    if response.lower() != 'yes':
                        print("❌ Suppression annulée")
                        return 0
                    
                    cursor.execute(query, (run_id,))
                    conn.commit()
                    self.deleted_count += count
                    print(f"✅ {count} prédictions supprimées")
                    return count
                    
        except Exception as e:
            print(f"❌ Erreur lors de la suppression par run_id: {e}")
            return 0
    
    def delete_null_actuals(self, dry_run=False):
        """
        Supprime les prédictions sans valeurs réelles (actual_value NULL)
        
        Args:
            dry_run: Si True, simule la suppression sans exécuter
        """
        query = """
        DELETE FROM consumption_predictions
        WHERE actual_value IS NULL
        """
        
        count_query = """
        SELECT COUNT(*) FROM consumption_predictions
        WHERE actual_value IS NULL
        """
        
        try:
            with self.db_handler._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(count_query)
                    count = cursor.fetchone()[0]
                    
                    if count == 0:
                        print(f"ℹ️  Aucune prédiction sans valeur réelle trouvée")
                        return 0
                    
                    print(f"🔍 {count} prédictions sans valeur réelle trouvées")
                    
                    if dry_run:
                        print(f"🔒 Mode DRY-RUN: {count} prédictions seraient supprimées")
                        return count
                    
                    response = input(f"⚠️  Confirmer la suppression de {count} prédictions sans valeur réelle ? (yes/no): ")
                    if response.lower() != 'yes':
                        print("❌ Suppression annulée")
                        return 0
                    
                    cursor.execute(query)
                    conn.commit()
                    self.deleted_count += count
                    print(f"✅ {count} prédictions supprimées")
                    return count
                    
        except Exception as e:
            print(f"❌ Erreur lors de la suppression des valeurs NULL: {e}")
            return 0
    
    def delete_outliers(self, min_value=None, max_value=None, dry_run=False):
        """
        Supprime les prédictions avec des valeurs aberrantes
        
        Args:
            min_value: Valeur minimale acceptable
            max_value: Valeur maximale acceptable
            dry_run: Si True, simule la suppression sans exécuter
        """
        conditions = []
        params = []
        
        if min_value is not None:
            conditions.append("prediction < %s")
            params.append(min_value)
        
        if max_value is not None:
            conditions.append("prediction > %s")
            params.append(max_value)
        
        if not conditions:
            print("❌ Spécifiez au moins min-value ou max-value")
            return 0
        
        where_clause = " OR ".join(conditions)
        
        query = f"""
        DELETE FROM consumption_predictions
        WHERE {where_clause}
        """
        
        count_query = f"""
        SELECT COUNT(*) FROM consumption_predictions
        WHERE {where_clause}
        """
        
        try:
            with self.db_handler._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(count_query, tuple(params))
                    count = cursor.fetchone()[0]
                    
                    if count == 0:
                        print(f"ℹ️  Aucune valeur aberrante trouvée")
                        return 0
                    
                    print(f"🔍 {count} prédictions avec valeurs aberrantes trouvées")
                    
                    if dry_run:
                        print(f"🔒 Mode DRY-RUN: {count} prédictions seraient supprimées")
                        return count
                    
                    response = input(f"⚠️  Confirmer la suppression de {count} prédictions aberrantes ? (yes/no): ")
                    if response.lower() != 'yes':
                        print("❌ Suppression annulée")
                        return 0
                    
                    cursor.execute(query, tuple(params))
                    conn.commit()
                    self.deleted_count += count
                    print(f"✅ {count} prédictions supprimées")
                    return count
                    
        except Exception as e:
            print(f"❌ Erreur lors de la suppression des valeurs aberrantes: {e}")
            return 0
    
    def delete_by_prediction_ids(self, prediction_ids, dry_run=False):
        """
        Supprime des prédictions par leurs IDs
        
        Args:
            prediction_ids: Liste des IDs de prédictions
            dry_run: Si True, simule la suppression sans exécuter
        """
        if not prediction_ids:
            print("❌ Aucun ID de prédiction fourni")
            return 0
        
        placeholders = ','.join(['%s'] * len(prediction_ids))
        query = f"""
        DELETE FROM consumption_predictions
        WHERE prediction_id IN ({placeholders})
        """
        
        count_query = f"""
        SELECT COUNT(*) FROM consumption_predictions
        WHERE prediction_id IN ({placeholders})
        """
        
        try:
            with self.db_handler._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(count_query, tuple(prediction_ids))
                    count = cursor.fetchone()[0]
                    
                    if count == 0:
                        print(f"ℹ️  Aucune prédiction trouvée pour les IDs fournis")
                        return 0
                    
                    print(f"🔍 {count} prédictions trouvées pour {len(prediction_ids)} IDs")
                    
                    if dry_run:
                        print(f"🔒 Mode DRY-RUN: {count} prédictions seraient supprimées")
                        return count
                    
                    response = input(f"⚠️  Confirmer la suppression de {count} prédictions ? (yes/no): ")
                    if response.lower() != 'yes':
                        print("❌ Suppression annulée")
                        return 0
                    
                    cursor.execute(query, tuple(prediction_ids))
                    conn.commit()
                    self.deleted_count += count
                    print(f"✅ {count} prédictions supprimées")
                    return count
                    
        except Exception as e:
            print(f"❌ Erreur lors de la suppression par IDs: {e}")
            return 0


def main():
    parser = argparse.ArgumentParser(description='Nettoie les données corrompues en base de données')
    parser.add_argument('--db-uri', type=str, required=False, help='URI de connexion PostgreSQL (optionnel)')
    parser.add_argument('--dry-run', action='store_true', help='Simulation sans suppression réelle')
    
    # Filtres
    parser.add_argument('--start-date', type=str, help='Date de début (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='Date de fin (YYYY-MM-DD)')
    parser.add_argument('--model-version', type=str, help='Version du modèle à supprimer')
    parser.add_argument('--run-id', type=str, help='Run ID MLflow à supprimer')
    parser.add_argument('--null-actuals', action='store_true', help='Supprimer les prédictions sans valeur réelle')
    parser.add_argument('--outliers', action='store_true', help='Supprimer les valeurs aberrantes')
    parser.add_argument('--min-value', type=float, help='Valeur minimale acceptable (pour outliers)')
    parser.add_argument('--max-value', type=float, help='Valeur maximale acceptable (pour outliers)')
    parser.add_argument('--prediction-ids', type=str, nargs='+', help='Liste des IDs de prédictions à supprimer')
    
    args = parser.parse_args()
    
    # Récupérer l'URI de la base de données
    if args.db_uri is None:
        db_uri = os.getenv('PREDICTIONS_POSTGRES_URI')
        if not db_uri:
            print("❌ URI de base de données non fournie (utilisez --db-uri ou PREDICTIONS_POSTGRES_URI)")
            sys.exit(1)
    else:
        db_uri = args.db_uri
    
    print(f"=== Nettoyage des données corrompues ===")
    if args.dry_run:
        print("🔒 MODE DRY-RUN: Aucune suppression réelle ne sera effectuée")
    print()
    
    # Initialiser le cleaner
    cleaner = DataCleaner(db_uri)
    
    # Vérifier la connexion
    if not cleaner.verify_connection():
        sys.exit(1)
    
    # Statistiques avant
    stats_before = cleaner.get_stats()
    
    # Exécuter les suppressions selon les filtres
    total_deleted = 0
    
    if args.start_date and args.end_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
            total_deleted += cleaner.delete_by_date_range(start_date, end_date, args.dry_run)
        except ValueError as e:
            print(f"❌ Erreur de format de date: {e}")
            sys.exit(1)
    
    elif args.model_version:
        total_deleted += cleaner.delete_by_model_version(args.model_version, args.dry_run)
    
    elif args.run_id:
        total_deleted += cleaner.delete_by_run_id(args.run_id, args.dry_run)
    
    elif args.null_actuals:
        total_deleted += cleaner.delete_null_actuals(args.dry_run)
    
    elif args.outliers:
        total_deleted += cleaner.delete_outliers(args.min_value, args.max_value, args.dry_run)
    
    elif args.prediction_ids:
        prediction_ids = [int(pid) for pid in args.prediction_ids]
        total_deleted += cleaner.delete_by_prediction_ids(prediction_ids, args.dry_run)
    
    else:
        print("❌ Aucun filtre spécifié. Utilisez --help pour voir les options disponibles.")
        sys.exit(1)
    
    # Statistiques après
    if not args.dry_run and total_deleted > 0:
        print()
        stats_after = cleaner.get_stats()
        if stats_before and stats_after:
            diff = stats_before['total_predictions'] - stats_after['total_predictions']
            print(f"📊 Résumé: {diff} prédictions supprimées")
            print(f"📊 Avant: {stats_before['total_predictions']} → Après: {stats_after['total_predictions']}")


if __name__ == "__main__":
    main()
