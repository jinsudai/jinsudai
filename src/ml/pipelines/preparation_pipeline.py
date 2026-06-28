"""
Pipeline pour préparer les features de consommation et les stocker sur S3.

Ce pipeline:
1. Télécharge le dernier fichier trained depuis S3
2. Calcule la date de fin à partir de la dernière horodate du fichier
3. Charge les données brutes PRM
4. Récupère les données météo
5. Récupère les données vacances/jours fériés
6. Fusionne et prépare les features
7. Récupère les données réelles depuis la base de données
8. Sauvegarde localement en Parquet
9. Upload sur S3 si les credentials sont disponibles

Classe principale :
- PreparationPipeline : Orchestration de la préparation des features
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd

from ..utils.data.s3_handler import S3Handler
from ..utils.data.database_handler import DatabaseHandler
from ..consumption.consumption_preparer import ConsumptionDataPreparer
from ..connectors.weather.weather_api import WeatherAPI
from ..connectors.holidays.holidays_api import HolidaysCombinedAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PreparationPipeline:
    """Pipeline pour la préparation des features de consommation."""

    def __init__(
        self,
        s3_bucket: Optional[str] = None,
        db_uri: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise le pipeline de préparation.

        Args:
            s3_bucket: Nom du bucket S3 (défaut: depuis env)
            db_uri: URI de connexion PostgreSQL
            config: Configuration du projet
        """
        self.s3_bucket = s3_bucket
        self.db_uri = db_uri
        self.config = config or {}

        self.s3_handler = S3Handler(bucket=s3_bucket)
        self.db_handler = None
        self.trained_df = None
        self.features_df = None
        self.start_date = None
        self.end_date = None

        logger.info("Pipeline de préparation initialisé")

    def setup(self):
        """Configure le pipeline (BD) et télécharge le dernier fichier trained."""
        logger.info("=== ÉTAPE 1: CONFIGURATION ET TÉLÉCHARGEMENT ===")

        # Initialiser BD si l'URI est fournie
        if self.db_uri:
            self.db_handler = DatabaseHandler(self.db_uri)
            if not self.db_handler.verify_connection():
                logger.error("Impossible de se connecter à la base de données")
                return False
            logger.info("Base de données configurée")
        else:
            logger.info("Aucune URI de base de données fournie")

        # Télécharger le dernier fichier trained depuis S3
        logger.info("Téléchargement du dernier fichier trained depuis S3...")
        result = self.s3_handler.download_latest_train_file(
            prefix="consumption/prepared",
            prioritize_dated=True
        )

        if result["status"] != "success":
            logger.warning(f"Aucun fichier trained trouvé: {result.get('reason')}")
            logger.info("Utilisation de la date actuelle comme point de départ")
            self.start_date = datetime.now()
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            self.end_date = datetime.combine(yesterday, datetime.max.time())
            return True

        local_path = result["local_path"]
        logger.info(f"Fichier téléchargé: {local_path}")

        # Charger le dataframe
        try:
            self.trained_df = pd.read_parquet(local_path)
            logger.info(f"DataFrame chargé: {self.trained_df.shape}")
            logger.info(f"Colonnes: {self.trained_df.columns.tolist()}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du dataframe: {e}")
            self.start_date = datetime.now()
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            self.end_date = datetime.combine(yesterday, datetime.max.time())
            return True

        # Calculer la plage de dates à partir du dataframe
        if self.trained_df is not None and 'Horodate' in self.trained_df.columns:
            if not pd.api.types.is_datetime64_any_dtype(self.trained_df['Horodate']):
                self.trained_df['Horodate'] = pd.to_datetime(self.trained_df['Horodate'])

            last_horodate = self.trained_df['Horodate'].max()
            logger.info(f"Dernière horodate dans le fichier trained: {last_horodate}")

            self.start_date = last_horodate + timedelta(minutes=30)
        else:
            logger.warning("Aucun fichier trained ou colonne Horodate trouvée")
            logger.info("Utilisation de la date actuelle comme point de départ")
            self.start_date = datetime.now()

        # La date de fin est la veille à 23:59:59
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        self.end_date = datetime.combine(yesterday, datetime.max.time())

        logger.info(f"Plage de dates calculée: {self.start_date} à {self.end_date}")
        return True


    def generate_weather_data(self, output_dir: Path) -> Path:
        """
        Génère les données météo.

        Args:
            output_dir: Répertoire de sortie

        Returns:
            Path: Chemin vers le fichier météo
        """
        logger.info("=== ÉTAPE 2: GÉNÉRATION DES DONNÉES MÉTÉO ===")

        start_date_str = self.start_date.strftime('%Y-%m-%d')
        end_date_str = self.end_date.strftime('%Y-%m-%d')
        weather_path = output_dir / f"weather_{start_date_str}_to_{end_date_str}.parquet"

        try:
            weather_api = WeatherAPI(
                latitude=43.5297,
                longitude=5.4474,
                location_name="Aix en Provence"
            )
            weather_df = weather_api.fetch_historical(
                start_date=start_date_str,
                end_date=end_date_str,
                hourly=True
            )
            # S'assurer que la colonne Horodate existe
            if 'Horodate' not in weather_df.columns:
                weather_df['Horodate'] = pd.to_datetime(weather_df.index)
            weather_df.to_parquet(weather_path)
            logger.info(f"Météo générée: {weather_path}")
            return weather_path
        except Exception as e:
            logger.error(f"Erreur génération météo: {e}")
            raise

    def generate_holidays_data(self, output_dir: Path) -> Path:
        """
        Génère les données vacances/jours fériés.

        Args:
            output_dir: Répertoire de sortie

        Returns:
            Path: Chemin vers le fichier vacances
        """
        logger.info("=== ÉTAPE 3: GÉNÉRATION DES DONNÉES VACANCES ===")

        start_date_str = self.start_date.strftime('%Y-%m-%d')
        end_date_str = self.end_date.strftime('%Y-%m-%d')
        holidays_path = output_dir / f"{start_date_str}_to_{end_date_str}_holidays.parquet"

        try:
            holidays_api = HolidaysCombinedAPI(zone="C")
            holidays_df = holidays_api.generate_holidays_dataframe(start_date_str, end_date_str)
            holidays_df.to_parquet(holidays_path)
            logger.info(f"Vacances générées: {holidays_path}")
            return holidays_path
        except Exception as e:
            logger.error(f"Erreur génération vacances: {e}")
            raise

    def prepare_features(
        self,
        weather_path: Path,
        holidays_path: Path,
        output_dir: Path,
        raw_path: Optional[str] = None,
        db_limit: Optional[int] = None
    ) -> Path:
        """
        Prépare les features consommation.

        Args:
            weather_path: Chemin vers le fichier météo
            holidays_path: Chemin vers le fichier vacances
            output_dir: Répertoire de sortie
            raw_path: Chemin vers le fichier brut PRM (optionnel)
            db_limit: Nombre maximum d'enregistrements à récupérer depuis la base

        Returns:
            Path: Chemin vers le fichier train
        """
        logger.info("=== ÉTAPE 4: PRÉPARATION DES FEATURES ===")

        start_date_str = self.start_date.strftime('%Y-%m-%d')
        end_date_str = self.end_date.strftime('%Y-%m-%d')
        train_path = output_dir / f"{start_date_str}_to_{end_date_str}_train.parquet"

        try:
            preparer = ConsumptionDataPreparer()
            self.features_df = preparer.prepare(
                raw_path=raw_path,
                weather_path=str(weather_path),
                holidays_path=str(holidays_path) if holidays_path else None,
                output_path=str(train_path),
                db_uri=self.db_uri,
                db_limit=db_limit,
                use_database=self.db_uri is not None
            )
            logger.info(f"Features préparées: {train_path}")
            logger.info(f"Shape: {self.features_df.shape}")
            return train_path
        except Exception as e:
            logger.error(f"Erreur préparation features: {e}")
            raise

    def fetch_actual_values(self):
        """
        Récupère les données réelles depuis la base de données et les fusionne avec les features.

        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 5: RÉCUPÉRATION DES DONNÉES RÉELLES ===")

        if self.db_handler is None:
            logger.info("Base de données non disponible, pas de récupération de données réelles")
            return True

        if self.features_df is None:
            logger.error("Aucun dataframe de features disponible")
            return False

        try:
            # Extraire la dernière horodate du dataframe
            if 'Horodate' in self.features_df.columns:
                if not pd.api.types.is_datetime64_any_dtype(self.features_df['Horodate']):
                    self.features_df['Horodate'] = pd.to_datetime(self.features_df['Horodate'])

                last_horodate = self.features_df['Horodate'].max()
                logger.info(f"Dernière horodate dans le dataframe: {last_horodate}")

                # Calculer la date de début pour récupérer les données réelles
                start_date_actual = last_horodate + timedelta(minutes=30)

                logger.info(f"Récupération des données réelles du {start_date_actual} au {self.end_date}")

                # Récupérer les prédictions avec les valeurs réelles
                actuals_df = self.db_handler.get_predictions_by_date(
                    start_date=start_date_actual,
                    end_date=self.end_date
                )

                if actuals_df is not None and len(actuals_df) > 0:
                    logger.info(f"{len(actuals_df)} enregistrements avec valeurs réelles récupérés")

                    # Filtrer pour ne garder que les enregistrements avec des valeurs réelles
                    actuals_with_values = actuals_df[actuals_df['actual_value'].notna()]
                    logger.info(f"{len(actuals_with_values)} enregistrements avec des valeurs réelles non nulles")

                    if len(actuals_with_values) > 0:
                        # Ajouter les données réelles au dataframe de features
                        if 'target_timestamp' in actuals_with_values.columns:
                            actuals_with_values = actuals_with_values.rename(columns={'target_timestamp': 'Horodate'})

                        # S'assurer que Horodate est au même format
                        if not pd.api.types.is_datetime64_any_dtype(actuals_with_values['Horodate']):
                            actuals_with_values['Horodate'] = pd.to_datetime(actuals_with_values['Horodate'])

                        # Fusionner les dataframes
                        self.features_df = pd.merge(
                            self.features_df,
                            actuals_with_values[['Horodate', 'actual_value']],
                            on='Horodate',
                            how='left'
                        )

                        logger.info(f"DataFrame après fusion: {self.features_df.shape}")
                        logger.info(f"Colonnes: {self.features_df.columns.tolist()}")
                    else:
                        logger.warning("Aucune valeur réelle non nulle trouvée")
                else:
                    logger.warning("Aucune donnée réelle trouvée dans la base")
            else:
                logger.warning("Colonne 'Horodate' non trouvée dans le dataframe")

            return True
        except Exception as e:
            logger.error(f"Erreur récupération données réelles: {e}")
            return False

    def upload_to_s3(self, train_path: Path, weather_path: Path) -> Dict[str, Any]:
        """
        Upload les fichiers sur S3.

        Args:
            train_path: Chemin vers le fichier train
            weather_path: Chemin vers le fichier météo

        Returns:
            dict: Résultat de l'upload
        """
        logger.info("=== ÉTAPE 6: UPLOAD SUR S3 ===")

        if not self.s3_handler.s3_enabled:
            logger.info("S3 non disponible, pas d'upload")
            return {"status": "skipped", "reason": "S3 not available"}

        try:
            # Upload du fichier weather
            weather_filename = weather_path.name
            s3_key_weather = f"weather/{weather_filename}"
            s3_result_weather = self.s3_handler.upload_file(
                local_path=str(weather_path),
                s3_key=s3_key_weather,
                metadata={"type": "weather"}
            )

            # Upload du fichier train
            train_filename = train_path.name
            s3_key_train = f"consumption/prepared/{train_filename}"
            s3_result_train = self.s3_handler.upload_file(
                local_path=str(train_path),
                s3_key=s3_key_train,
                metadata={"type": "train"}
            )

            return {
                "status": "success",
                "weather": s3_result_weather,
                "train": s3_result_train
            }
        except Exception as e:
            logger.error(f"Erreur upload S3: {e}")
            return {"status": "error", "error": str(e)}

    def run(
        self,
        raw_path: Optional[str] = None,
        output_dir: str = "data/processed/",
        db_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Exécute le pipeline complet.

        Args:
            raw_path: Chemin vers le fichier brut PRM (optionnel)
            output_dir: Répertoire de sortie local
            db_limit: Nombre maximum d'enregistrements à récupérer depuis la base

        Returns:
            dict: Résultat du pipeline
        """
        logger.info("####################################################")
        logger.info("### PIPELINE DE PRÉPARATION DES FEATURES ###")
        logger.info(f"### Date/Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ###")
        logger.info("####################################################\n")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # ÉTAPE 1: Configuration et téléchargement du fichier trained
        if not self.setup():
            return {"status": "error", "step": "setup", "error": "Configuration failed"}

        # Vérifier que la plage de dates est valide
        if self.start_date > self.end_date:
            logger.warning("La date de début est après la date de fin")
            logger.info("Aucune nouvelle donnée à traiter")
            return {"status": "success", "message": "No new data to process"}

        # ÉTAPE 2: Générer les données météo
        try:
            weather_path = self.generate_weather_data(output_dir)
        except Exception as e:
            return {"status": "error", "step": "weather", "error": str(e)}

        # ÉTAPE 3: Générer les données vacances
        try:
            holidays_path = self.generate_holidays_data(output_dir)
        except Exception as e:
            return {"status": "error", "step": "holidays", "error": str(e)}

        # ÉTAPE 4: Préparer les features
        try:
            train_path = self.prepare_features(weather_path, holidays_path, output_dir, raw_path, db_limit)
        except Exception as e:
            return {"status": "error", "step": "features", "error": str(e)}

        # ÉTAPE 5: Récupérer les données réelles
        if not self.fetch_actual_values():
            logger.warning("Erreur lors de la récupération des données réelles, continuation...")

        # ÉTAPE 6: Upload sur S3
        s3_result = self.upload_to_s3(train_path, weather_path)

        logger.info("\n####################################################")
        logger.info("### PIPELINE TERMINÉ AVEC SUCCÈS ###")
        logger.info("####################################################\n")

        return {
            "status": "success",
            "local_paths": {
                "weather": str(weather_path),
                "holidays": str(holidays_path),
                "train": str(train_path)
            },
            "s3": s3_result,
            "dates": {
                "start": self.start_date.strftime('%Y-%m-%d'),
                "end": self.end_date.strftime('%Y-%m-%d')
            }
        }
