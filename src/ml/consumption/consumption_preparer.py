"""
Préparation des données de consommation électrique.

Module spécifique au domaine CONSOMMATION qui utilise les utilitaires
partagés (utils/data/) pour transformer les données brutes PRM en
features prêtes pour l'entraînement.

Exemple d'utilisation :
    from analytics.consumption.consumption_preparer import ConsumptionDataPreparer

    preparer = ConsumptionDataPreparer()
    df = preparer.prepare(
        raw_path="data/test/test_raw_consumption.csv",
        weather_path="data/raw/weather.parquet",
        holidays_path="data/raw/holidays.parquet",
        output_path="data/processed/consumption_features.parquet"
    )
"""

import os

import pandas as pd
from pathlib import Path
from typing import Optional, Union
import logging

from ml.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Chemin par défaut vers la configuration
env = os.getenv('ENV', 'dev')  # Assurer que ENV est défini pour la config
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "configs" / f"consumption.{env}.yaml"


class ConsumptionDataPreparer:
    """
    Classe pour préparer les données de consommation électrique.

    Utilise les utilitaires partagés (utils/data/) et ajoute la logique
    spécifique au domaine consommation.
    """

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialise le préparateur de données consommation.

        Args:
            config_path: Chemin vers le fichier YAML de configuration.
                        Par défaut, utilise src/configs/consumption.yaml
        """
        self.config = load_config(config_name="consumption")

    def load_raw_consumption(self, raw_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
        """
        Charge les données brutes PRM de consommation.

        Args:
            raw_path: Chemin vers le fichier CSV brut (raw_template.csv).
                     Si non fourni, utilise la valeur depuis la config (data.raw_path).

        Returns:
            DataFrame avec uniquement Horodate et Valeur
        """
        # Utiliser la valeur de config si non fournie
        if raw_path is None:
            raw_path = self.config.get("data", {}).get("raw_path", "./data/templates/raw_template.csv")

        df = pd.read_csv(
            raw_path,
            sep=";",
            parse_dates=["Horodate", "Date de début", "Date de fin"],
            dayfirst=True,
            encoding="utf-8"
        )

        # Extraire uniquement Horodate et Valeur
        if "Horodate" not in df.columns or "Valeur" not in df.columns:
            available = list(df.columns)
            raise ValueError(f"Colonnes 'Horodate' ou 'Valeur' manquantes. Disponibles: {available}")

        # Nettoyer Valeur (convertir en numérique)
        target_col = self.config.get("data", {}).get("target_column", "Valeur")
        consumption_df = df[["Horodate", target_col]].copy()
        consumption_df[target_col] = pd.to_numeric(consumption_df[target_col], errors="coerce")
        consumption_df = consumption_df.dropna(subset=[target_col])

        logger.info(f"Données consommation chargées: {len(consumption_df)} enregistrements")
        return consumption_df

    def load_weather_data(self, weather_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
        """
        Charge les données météo depuis le Parquet.

        Args:
            weather_path: Chemin vers le fichier Parquet météo.
                        Si non fourni, utilise la valeur depuis la config (data.weather_file).

        Returns:
            DataFrame avec les données météo
        """
        print(f"Loading weather data from: {self.config.get('data', {}).get('weather_file')}")
        if weather_path is None:
            weather_path = self.config.get("data", {}).get("weather_file", "../data/processed/weather.parquet")
        df = pd.read_parquet(weather_path)
        logger.info(f"Données météo chargées: {len(df)} enregistrements")
        return df

    def load_holidays_data(self, holidays_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
        """
        Charge les données vacances/jours fériés depuis le Parquet.

        Args:
            holidays_path: Chemin vers le fichier Parquet calendrier.
                          Si non fourni, utilise la valeur depuis la config (data.holidays_file).

        Returns:
            DataFrame avec les données calendrier
        """
        if holidays_path is None:
            holidays_path = self.config.get("data", {}).get("holidays_file", "../data/processed/holidays.parquet")
        df = pd.read_parquet(holidays_path)
        logger.info(f"Données calendrier chargées: {len(df)} enregistrements")
        return df

    def load_consumption_from_database(self, db_uri: Optional[str] = None, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Charge les données de consommation depuis la base de données PostgreSQL.

        Args:
            db_uri: URI de connexion PostgreSQL. Si non fourni, utilise la variable d'environnement
                    PREDICTIONS_POSTGRES_URI, puis la config.
            limit: Nombre maximum d'enregistrements à récupérer.

        Returns:
            DataFrame avec Horodate et Valeur (actual_value)
        """
        from ml.pipelines.database_handler import DatabaseHandler
        import os

        if db_uri is None:
            db_uri = os.getenv('PREDICTIONS_POSTGRES_URI')

        if db_uri is None:
            db_uri = self.config.get("database", {}).get("uri")

        if not db_uri:
            raise ValueError("URI de base de données non fournie (paramètre, variable d'environnement PREDICTIONS_POSTGRES_URI ou config)")

        db_handler = DatabaseHandler(db_uri=db_uri)
        df = db_handler.get_production_data_for_retraining(limit=limit)

        if df is None or df.empty:
            raise ValueError("Aucune donnée trouvée dans la base de données")

        # Renommer les colonnes pour correspondre au format attendu
        df = df.rename(columns={"target_timestamp": "Horodate", "actual_value": "Valeur"})

        # Convertir Horodate en datetime si nécessaire
        if not pd.api.types.is_datetime64_any_dtype(df["Horodate"]):
            df["Horodate"] = pd.to_datetime(df["Horodate"])

        # Nettoyer Valeur (convertir en numérique)
        target_col = self.config.get("data", {}).get("target_column", "Valeur")
        df[target_col] = pd.to_numeric(df[target_col], errors="coerce")
        df = df.dropna(subset=[target_col])

        logger.info(f"Données consommation chargées depuis la base: {len(df)} enregistrements")
        return df

    def _clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Nettoie les noms de colonnes (espaces, accents)."""
        df = df.copy()
        df.columns = df.columns.str.strip().str.replace("  ", " ")
        return df

    def merge_datasets(
        self,
        consumption_df: pd.DataFrame,
        weather_df: pd.DataFrame,
        holidays_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Fusionne les 3 datasets sur la colonne Horodate.

        Args:
            consumption_df: DataFrame avec Horodate, Valeur
            weather_df: DataFrame avec données météo
            holidays_df: DataFrame avec données calendrier

        Returns:
            DataFrame fusionné avec toutes les colonnes du template
        """
        # Nettoyer les noms de colonnes
        weather_df = self._clean_column_names(weather_df)
        holidays_df = self._clean_column_names(holidays_df)

        # Normaliser les types de Horodate (forcer datetime)
        for df in [consumption_df, weather_df, holidays_df]:
            if "Horodate" in df.columns:
                df["Horodate"] = pd.to_datetime(df["Horodate"])

        # Fusionner consommation + météo
        merged_df = pd.merge(
            consumption_df,
            weather_df,
            on="Horodate",
            how="left"
        )

        # Fusionner avec calendrier
        merged_df = pd.merge(
            merged_df,
            holidays_df,
            on="Horodate",
            how="left"
        )

        # Remplir les NaN pour les colonnes calendrier
        merged_df["is_vacances"] = merged_df.get("is_vacances", 0).fillna(0).astype(int)
        merged_df["nom_vacances"] = merged_df.get("nom_vacances", "").fillna("")
        merged_df["jour de la semaine"] = merged_df.get("jour de la semaine", "").fillna("")
        merged_df["jour férié"] = merged_df.get("jour férié", 0).fillna(0).astype(int)

        # Remplir les NaN pour les colonnes météo (avec des valeurs par défaut)
        merged_df["temperature_2m_mean"] = merged_df.get("temperature_2m_mean", 15.0).fillna(15.0)
        merged_df["relative_humidity_mean"] = merged_df.get("relative_humidity_mean", 70.0).fillna(70.0)
        merged_df["precipitation_sum"] = merged_df.get("precipitation_sum", 0.0).fillna(0.0)

        logger.info(f"Datasets fusionnés: {len(merged_df)} enregistrements")
        return merged_df

    def validate_against_template(self, df: pd.DataFrame) -> bool:
        """
        Valide que le DataFrame correspond à la configuration.

        Args:
            df: DataFrame à valider

        Returns:
            bool: True si valide

        Raises:
            ValueError: Si validation échoue
        """
        # Récupérer la configuration
        data_config = self.config.get("data", {})
        required_features = data_config.get("feature_columns", [])
        target_col = data_config.get("target_column", "Valeur")

        # Colonnes attendues = Horodate + target + features
        expected_columns = ["Horodate", target_col] + required_features
        # Ajouter nom_vacances qui est utilisé dans le template
        if "nom_vacances" not in expected_columns:
            expected_columns.append("nom_vacances")

        # Vérifier colonnes
        missing = [col for col in expected_columns if col not in df.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes vs configuration: {missing}")

        # Vérifier qu'il n'y a pas de colonnes en trop
        extra = [col for col in df.columns if col not in expected_columns]
        if extra:
            logger.warning(f"Colonnes supplémentaires: {extra}")

        # Vérifier types des features
        float_features = ["temperature_2m_mean", "relative_humidity_mean", "precipitation_sum"]
        int_features = ["is_vacances", "jour férié"]
        str_features = ["nom_vacances", "jour de la semaine"]

        for col in float_features:
            if col in df.columns:
                actual_type = str(df[col].dtype)
                if actual_type not in ["float64", "float32"]:
                    logger.warning(f"Type inattendu pour {col}: {actual_type} (attendu: float)")

        for col in int_features:
            if col in df.columns:
                actual_type = str(df[col].dtype)
                if actual_type not in ["int64", "int32"]:
                    logger.warning(f"Type inattendu pour {col}: {actual_type} (attendu: int)")

        for col in str_features:
            if col in df.columns:
                actual_type = str(df[col].dtype)
                if actual_type not in ["object", "string"]:
                    logger.warning(f"Type inattendu pour {col}: {actual_type} (attendu: string)")

        # Vérifier Horodate
        if "Horodate" in df.columns:
            actual_type = str(df["Horodate"].dtype)
            if actual_type not in ["datetime64[ns]", "datetime64"]:
                logger.warning(f"Type inattendu pour Horodate: {actual_type} (attendu: datetime)")

        # Vérifier valeurs manquantes (max 5%)
        cols_to_check = ["Horodate", target_col] + required_features
        for col in cols_to_check:
            if col in df.columns and col not in ["nom_vacances"]:
                null_pct = df[col].isnull().mean() * 100
                if null_pct > 5:
                    raise ValueError(f"{col} a {null_pct:.1f}% de valeurs manquantes (max 5%)")
                elif null_pct > 0:
                    logger.warning(f"{col} a {null_pct:.2f}% de valeurs manquantes")

        # Vérifier que target n'a pas de NaN
        if target_col in df.columns and df[target_col].isnull().any():
            raise ValueError(f"La colonne '{target_col}' contient des valeurs manquantes")

        logger.info("✅ Validation contre configuration réussie")
        return True

    def prepare(
        self,
        raw_path: Optional[Union[str, Path]] = None,
        weather_path: Optional[Union[str, Path]] = None,
        holidays_path: Optional[Union[str, Path]] = None,
        output_path: Optional[Union[str, Path]] = None,
        db_uri: Optional[str] = None,
        db_limit: Optional[int] = None,
        use_database: bool = False
    ) -> pd.DataFrame:
        """
        Pipeline complet de préparation des données consommation.

        Args:
            raw_path: Chemin vers le fichier brut PRM (raw_template.csv).
                     Si non fourni, utilise la valeur depuis la config (data.raw_path).
            weather_path: Chemin vers le Parquet météo. Si non fourni, utilise config (data.weather_file).
            holidays_path: Chemin vers le Parquet vacances/jours fériés. Si non fourni, utilise config (data.holidays_file).
            output_path: Chemin pour sauvegarder le résultat. Si non fourni, utilise config (data.train_path).
            db_uri: URI de connexion PostgreSQL pour charger les données depuis la base.
                    Si fourni, prioritaire sur raw_path.
            db_limit: Nombre maximum d'enregistrements à récupérer depuis la base.
            use_database: Si True, force l'utilisation de la base de données (utilise db_uri si fourni,
                         sinon variable d'environnement PREDICTIONS_POSTGRES_URI).

        Returns:
            DataFrame: Données prêtes pour l'entraînement
        """
        # 1. Charger données brutes consommation (depuis fichier ou base de données)
        if use_database or db_uri:
            logger.info("Chargement des données depuis la base de données PostgreSQL")
            consumption_df = self.load_consumption_from_database(db_uri=db_uri, limit=db_limit)
        else:
            consumption_df = self.load_raw_consumption(raw_path)

        # 2. Charger données météo
        weather_df = self.load_weather_data(weather_path)

        # 3. Charger données calendrier
        holidays_df = self.load_holidays_data(holidays_path)

        # 4. Fusionner
        features_df = self.merge_datasets(consumption_df, weather_df, holidays_df)

        # 5. Valider contre template
        self.validate_against_template(features_df)

        # 6. Sauvegarder si demandé
        if output_path is None:
            output_path = self.config.get("data", {}).get("train_path", "data/processed/consumption/train.parquet")

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            features_df.to_parquet(output_path)
            logger.info(f"✅ Features consommation sauvegardées: {output_path}")

        return features_df
