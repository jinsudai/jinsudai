"""
Pipeline quotidien pour mettre à jour les prédictions avec les valeurs réelles.

Spécifications :
- Exécution quotidienne pour récupérer les valeurs de la veille
- Met à jour les enregistrements dans la base de données prediction
- Stocke les valeurs dans un nouveau champ (actual_value)
- Pour l'instant, les valeurs sont générées aléatoirement

Classe principale :
- IngestionPipeline : Orchestration de la mise à jour des valeurs réelles
"""
import logging
from datetime import datetime, timedelta
import random

from ..utils.data.database_handler import DatabaseHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IngestionPipeline:
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

            # Créer les tables si nécessaire
            if not self.db_handler.create_tables():
                logger.error("Impossible de créer les tables")
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
            return True

        logger.info(f"{len(self.previous_day_predictions)} prédictions récupérées pour la veille")
        return True

    def generate_random_actual_values(self, insert_if_missing=False):
        """
        Génère des valeurs aléatoires pour les prédictions de la veille

        Args:
            insert_if_missing: Si True, insère des enregistrements complets si aucune prédiction n'existe

        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 3: GÉNÉRATION DES VALEURS ALÉATOIRES ===")

        if self.previous_day_predictions is None or len(self.previous_day_predictions) == 0:
            if insert_if_missing:
                logger.info("Aucune prédiction trouvée - génération d'enregistrements complets")
                return self._generate_and_insert_records()
            else:
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

    def _generate_and_insert_records(self):
        """
        Génère et insère des enregistrements complets (prediction + actual_value)
        pour la veille lorsqu'aucune prédiction n'existe en base

        Returns:
            True si succès, False sinon
        """
        logger.info("=== GÉNÉRATION D'ENREGISTREMENTS COMPLETS ===")

        # Calculer les dates de la veille
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # Générer 48 enregistrements au pas de 30 minutes pour la veille
        target_timestamps = []
        actual_values = []

        for half_hour in range(48):
            timestamp = datetime.combine(yesterday, datetime.min.time()) + timedelta(minutes=30 * half_hour)
            target_timestamps.append(timestamp)

            # Générer une valeur réelle aléatoire entre 100 et 500
            actual_value = random.uniform(100, 500)
            actual_values.append(actual_value)

        logger.info(f"{len(target_timestamps)} enregistrements générés")

        # Insérer dans la base de données
        entity_id = "550e8400-e29b-41d4-a716-446655440000"

        if not self.db_handler.insert_predictions_with_actual_values(
            target_timestamps, actual_values, entity_id
        ):
            logger.error("Impossible d'insérer les enregistrements")
            return False

        self.updated_count = len(target_timestamps)
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
                logger.info(f"Exemple de valeurs mises à jour:\n{with_actual_values[['target_timestamp', 'prediction', 'actual_value']].head()}")

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

        # Si aucune prédiction trouvée, générer et insérer des enregistrements
        if self.previous_day_predictions is None or len(self.previous_day_predictions) == 0:
            logger.info("Aucune prédiction trouvée - génération et insertion d'enregistrements")
            if not self.generate_random_actual_values(insert_if_missing=True):
                return False, None
            results = self.verify_updates()
            return True, results

        if not predictions_result:
            return False, None

        # Vérifier si le SFTP est activé : si oui, utiliser le module SFTP pour ingérer
        sftp_enabled = self.config.get('sftp', {}).get('enabled', False)

        if sftp_enabled:
            logger.info("=== SFTP ACTIVÉ - LANCEMENT DE L'INGESTION SFTP ===")
            try:
                from ml.utils.data.sftp_ingestion_pipeline import (
                    run_sftp_ingestion_pipeline,
                    load_sftp_config
                )

                sftp_cfg = self.config.get('sftp', {})

                # Priorité: config > environnement
                if sftp_cfg.get('use_env_config', False):
                    try:
                        env_cfg = load_sftp_config()
                        result = run_sftp_ingestion_pipeline(
                            sftp_host=env_cfg['host'],
                            sftp_username=env_cfg['username'],
                            ssh_private_key_b64=env_cfg.get('ssh_private_key_b64'),
                            ssh_private_key_content=env_cfg.get('ssh_private_key_content'),
                            db_uri=self.db_uri,
                            remote_directory=env_cfg.get('remote_directory'),
                            archive_directory=env_cfg.get('archive_directory'),
                            passphrase=env_cfg.get('passphrase'),
                            sftp_port=env_cfg.get('port', 22),
                            sftp_timeout=env_cfg.get('timeout', 30),
                            file_pattern=env_cfg.get('file_pattern', '*.csv'),
                            temp_local_dir=env_cfg.get('temp_local_dir', '/tmp/sftp_temp')
                        )
                    except Exception as e:
                        logger.error(f"Erreur lors du chargement de la configuration SFTP depuis l'environnement: {e}")
                        logger.warning("Basculement vers génération aléatoire")
                        if not self.generate_random_actual_values(insert_if_missing=True):
                            return False, None
                        results = self.verify_updates()
                        return True, results
                else:
                    # Lire les paramètres SFTP depuis la config
                    host = sftp_cfg.get('host')
                    username = sftp_cfg.get('username')
                    if not host or not username:
                        logger.warning("Configuration SFTP incomplète dans config; basculement vers génération aléatoire")
                        if not self.generate_random_actual_values(insert_if_missing=True):
                            return False, None
                        results = self.verify_updates()
                        return True, results

                    result = run_sftp_ingestion_pipeline(
                        sftp_host=host,
                        sftp_username=username,
                        ssh_private_key_b64=sftp_cfg.get('ssh_private_key_b64'),
                        ssh_private_key_content=sftp_cfg.get('ssh_private_key_content'),
                        db_uri=self.db_uri,
                        remote_directory=sftp_cfg.get('remote_directory', '/data/incoming'),
                        archive_directory=sftp_cfg.get('archive_directory', '/data/archived'),
                        passphrase=sftp_cfg.get('passphrase'),
                        sftp_port=sftp_cfg.get('port', 22),
                        sftp_timeout=sftp_cfg.get('timeout', 30),
                        file_pattern=sftp_cfg.get('file_pattern', '*.csv'),
                        temp_local_dir=sftp_cfg.get('temp_local_dir', '/tmp/sftp_temp')
                    )

                # Interpréter le résultat de l'ingestion SFTP
                if result is None:
                    logger.error("Résultat de l'ingestion SFTP invalide")
                    return False, None

                status = result.get('status')
                if status == 'success':
                    logger.info("Ingestion SFTP réalisée avec succès")
                    results = self.verify_updates()
                    return True, results
                elif status == 'no_files':
                    logger.info("Aucun fichier récupéré depuis SFTP")
                    return True, None
                else:
                    logger.error(f"Erreur lors de l'ingestion SFTP: {result}")
                    return False, None

            except Exception as e:
                logger.error(f"Échec du flux SFTP: {e}")
                logger.warning("Basculement vers génération aléatoire")
                if not self.generate_random_actual_values(insert_if_missing=True):
                    return False, None

        results = self.verify_updates()

        logger.info("\n####################################################")
        logger.info(f"### PIPELINE TERMINÉ - {self.updated_count} ENREGISTREMENTS MIS À JOUR ###")
        logger.info("####################################################\n")

        return True, results
