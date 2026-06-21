"""
Pipeline quotidien pour mettre à jour les prédictions avec les valeurs réelles.

Spécifications :
- Exécution quotidienne pour récupérer les valeurs de la veille
- Met à jour les enregistrements dans la base de données prediction
- Stocke les valeurs dans un nouveau champ (actual_value)
- Pour l'instant, les valeurs sont générées aléatoirement

Classe principale :
- ActualValuesPipeline : Orchestration de la mise à jour des valeurs réelles
"""
import logging
from datetime import datetime, timedelta
import random

from .database_handler import DatabaseHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActualValuesPipeline:
    """Pipeline pour la mise à jour quotidienne des valeurs réelles"""

    def __init__(self, db_uri, config=None):
        """
        Initialise le pipeline

        Args:
            db_uri: URI de connexion PostgreSQL
            config: Configuration du projet (pour vérifier sftp.enabled)
        """
        self.db_uri = db_uri
        self.config = config or {}
        self.db_handler = None
        self.previous_day_predictions = None
        self.updated_count = 0

        logger.info("Pipeline de valeurs réelles initialisé")

    def setup(self):
        """Configure le pipeline (BD)"""
        logger.info("=== ÉTAPE 1: CONFIGURATION ===")

        # Initialiser BD
        if self.db_uri:
            self.db_handler = DatabaseHandler(self.db_uri)
            if not self.db_handler.verify_connection():
                logger.error("Impossible de se connecter à la base de données")
                return False

            # Ajouter la colonne actual_value si elle n'existe pas
            if not self.db_handler.add_actual_value_column():
                logger.error("Impossible d'ajouter la colonne actual_value")
                return False

            logger.info("Base de données configurée")
        else:
            logger.warning("Aucune URI de base de données fournie")
            return False

        return True

    def get_previous_day_predictions(self):
        """
        Récupère les prédictions de la veille

        Returns:
            True si succès, False si erreur critique, None si aucune prédiction
        """
        logger.info("=== ÉTAPE 2: RÉCUPÉRATION DES PRÉDICTIONS DE LA VEILLE ===")

        # Calculer les dates de la veille
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # Définir la plage de temps pour la veille (de 00:00 à 23:59)
        start_date = datetime.combine(yesterday, datetime.min.time())
        end_date = datetime.combine(yesterday, datetime.max.time())

        logger.info(f"Récupération des prédictions du {yesterday}")
        logger.info(f"Plage de temps: {start_date} à {end_date}")

        # Récupérer les prédictions
        self.previous_day_predictions = self.db_handler.get_predictions_by_date(
            start_date=start_date,
            end_date=end_date
        )

        if self.previous_day_predictions is None or len(self.previous_day_predictions) == 0:
            logger.warning(f"Aucune prédiction trouvée pour la date {yesterday}")
            logger.info("Pipeline terminé avec succès - aucune mise à jour nécessaire")
            return None  # Retourne None pour indiquer aucune prédiction (pas une erreur)

        logger.info(f"{len(self.previous_day_predictions)} prédictions récupérées pour la veille")
        return True

    def generate_random_actual_values(self):
        """
        Génère des valeurs aléatoires pour les prédictions de la veille

        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 3: GÉNÉRATION DES VALEURS ALÉATOIRES ===")

        if self.previous_day_predictions is None or len(self.previous_day_predictions) == 0:
            logger.error("Aucune prédiction à traiter")
            return False

        # Générer des valeurs aléatoires autour de la valeur prédite
        # Pour simuler des valeurs réelles réalistes
        prediction_ids = []
        actual_values = []

        for _, row in self.previous_day_predictions.iterrows():
            prediction_value = row['prediction']

            # Générer une valeur aléatoire avec une variation de ±20%
            variation = random.uniform(-0.2, 0.2)
            actual_value = prediction_value * (1 + variation)

            # S'assurer que la valeur est positive
            actual_value = max(0, actual_value)

            prediction_ids.append(row['prediction_id'])
            actual_values.append(actual_value)

        logger.info(f"{len(actual_values)} valeurs aléatoires générées")

        # Mettre à jour la base de données
        if not self.db_handler.update_actual_values(prediction_ids, actual_values):
            logger.error("Impossible de mettre à jour les valeurs réelles")
            return False

        self.updated_count = len(actual_values)
        return True

    def verify_updates(self):
        """
        Vérifie les mises à jour effectuées

        Returns:
            DataFrame des prédictions mises à jour ou None
        """
        logger.info("=== ÉTAPE 4: VÉRIFICATION DES MISES À JOUR ===")

        # Récupérer à nouveau les prédictions de la veille pour vérifier
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        start_date = datetime.combine(yesterday, datetime.min.time())
        end_date = datetime.combine(yesterday, datetime.max.time())

        updated_predictions = self.db_handler.get_predictions_by_date(
            start_date=start_date,
            end_date=end_date
        )

        if updated_predictions is not None:
            # Vérifier que les valeurs actual_value sont présentes
            with_actual_values = updated_predictions[updated_predictions['actual_value'].notna()]
            logger.info(f"{len(with_actual_values)} prédictions avec des valeurs réelles")

            if len(with_actual_values) > 0:
                logger.info(f"Exemple de valeurs mises à jour:\n{with_actual_values[['prediction_timestamp', 'prediction', 'actual_value']].head()}")

        return updated_predictions

    def run_full_pipeline(self):
        """
        Exécute le pipeline complet

        Returns:
            Tuple (succès: bool, DataFrame des prédictions mises à jour ou None)
        """
        logger.info("####################################################")
        logger.info("### PIPELINE DE MISE À JOUR DES VALEURS RÉELLES ###")
        logger.info(f"### Date/Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ###")
        logger.info("####################################################\n")

        # Exécuter chaque étape
        if not self.setup():
            return False, None

        predictions_result = self.get_previous_day_predictions()

        # Si aucune prédiction trouvée, retourner succès (pas une erreur)
        if predictions_result is None:
            logger.info("Pipeline terminé avec succès - aucune prédiction à mettre à jour")
            return True, None

        if not predictions_result:
            return False, None

        # Vérifier si le SFTP est activé avant de générer des valeurs aléatoires
        sftp_enabled = self.config.get('sftp', {}).get('enabled', False)

        if sftp_enabled:
            logger.info("=== SFTP ACTIVÉ - PAS DE GÉNÉRATION ALÉATOIRE ===")
            logger.warning("Le SFTP est activé dans la configuration. Les valeurs réelles doivent être récupérées depuis le SFTP.")
            logger.info("Pipeline terminé avec succès - aucune génération aléatoire nécessaire")
            return True, None

        if not self.generate_random_actual_values():
            return False, None

        results = self.verify_updates()

        logger.info("\n####################################################")
        logger.info(f"### PIPELINE TERMINÉ - {self.updated_count} ENREGISTREMENTS MIS À JOUR ###")
        logger.info("####################################################\n")

        return True, results
