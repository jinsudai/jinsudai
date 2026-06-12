"""Génération et préparation des données pour l'inférence."""
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from ml.config import DEFAULT_CONSUMPTION_CONFIG, get_nested, load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_feature_columns_from_config(config_name=DEFAULT_CONSUMPTION_CONFIG, config_path=None):
    """Récupère la liste des features depuis la configuration YAML."""
    config = load_config(config_path=config_path, config_name=config_name)
    feature_columns = get_nested(config, "data.feature_columns")
    if feature_columns is None:
        feature_columns = [
            "Horodate",
            "temperature_2m_mean",
            "relative_humidity_mean",
            "precipitation_sum",
            "is_vacances",
            "nom_vacances",
            "jour de la semaine",
            "jour férié"
        ]
        logger.warning("Aucune liste de feature_columns dans la configuration, valeurs par défaut utilisées")
    return feature_columns


def generate_inference_data(
    n_days=1,
    n_samples_per_day=48,
    feature_columns=None,
    start_date=None,
    seed=42,
    config_name=DEFAULT_CONSUMPTION_CONFIG,
    config_path=None,
):
    """Génère un jeu de données d'inférence pour n jours."""
    np.random.seed(seed)

    if start_date is None:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if feature_columns is None:
        feature_columns = _get_feature_columns_from_config(
            config_name=config_name,
            config_path=config_path,
        )

    total_samples = n_days * n_samples_per_day
    timestamps = [
        start_date + timedelta(minutes=int(1440 * i / n_samples_per_day) + 1440 * day)
        for day in range(n_days)
        for i in range(n_samples_per_day)
    ]

    data = {}
    for col in feature_columns:
        if col in ("prediction_timestamp", "Horodate", "horodate"): # A revoir pour être plus générique
            data[col] = timestamps
        elif col == "temperature_2m_mean":
            data[col] = np.random.normal(loc=20.0, scale=5.0, size=total_samples)
        elif col == "relative_humidity_mean":
            data[col] = np.random.uniform(40.0, 85.0, size=total_samples)
        elif col == "precipitation_sum":
            data[col] = np.random.exponential(scale=0.5, size=total_samples)
        elif col == "is_vacances":
            data[col] = np.random.choice([0, 1], size=total_samples, p=[0.9, 0.1])
        elif col == "nom_vacances":
            data[col] = ["" if is_vac == 0 else "vacances" for is_vac in data.get("is_vacances", np.zeros(total_samples, dtype=int))]
        elif col == "jour de la semaine":
            data[col] = [ts.strftime("%A") for ts in timestamps]
        elif col == "jour férié":
            data[col] = np.zeros(total_samples, dtype=int)
        else:
            data[col] = np.random.standard_normal(total_samples)

    df_inference = pd.DataFrame(data)
    logger.info(f"Données d'inférence générées: {df_inference.shape[0]} échantillons")
    return df_inference


def add_predictions_to_data(df_inference, predictions, confidence_scores=None):
    """Ajoute les prédictions au DataFrame d'inférence."""
    df_result = df_inference.copy()
    df_result["prediction"] = predictions

    if confidence_scores is not None:
        df_result["confidence"] = confidence_scores

    logger.info(f"Prédictions ajoutées au DataFrame: {df_result.shape}")
    return df_result
