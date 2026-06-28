"""Génération et préparation des données pour l'inférence."""
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from ml.config import DEFAULT_CONSUMPTION_CONFIG, get_nested, load_config
from ml.connectors.holidays.holidays_api import HolidaysCombinedAPI
from ml.connectors.weather.weather_api import WeatherAPI

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

    if start_date is None:
        # Default to current time rounded to next 30-minute interval
        now = datetime.now()
        minute = now.minute
        # Round to next 30-minute mark
        if minute < 30:
            start_date = now.replace(minute=30, second=0, microsecond=0)
        else:
            start_date = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    
    logger.info(f"Génération de données d'inférence: {n_days} jour(s) à partir de {start_date}")
    logger.info(f"Échantillons par jour: {n_samples_per_day}, Total échantillons: {n_days * n_samples_per_day}")

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

    # Récupérer la configuration
    config = load_config(config_path=config_path, config_name=config_name)

    # Générer les données de vacances avec l'API
    end_date = start_date + timedelta(days=n_days)
    holidays_zone = get_nested(config, "data.holidays_zone", "C")  # Défaut: zone C
    holidays_api = HolidaysCombinedAPI(zone=holidays_zone)
    holidays_df = holidays_api.generate_holidays_dataframe(
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    )

    # Créer un mapping Horodate -> données de vacances
    holidays_mapping = {}
    for _, row in holidays_df.iterrows():
        ts = row["Horodate"]
        holidays_mapping[ts] = {
            "is_vacances": row["is_vacances"],
            "nom_vacances": row["nom_vacances"],
            "jour de la semaine": row["jour de la semaine"],
            "jour férié": row["jour férié"]
        }

    # Récupérer les prévisions météo avec l'API
    weather_latitude = get_nested(config, "data.weather_latitude", 43.5297)  # Défaut: Aix en Provence
    weather_longitude = get_nested(config, "data.weather_longitude", 5.4474)
    weather_location = get_nested(config, "data.weather_location", "Aix en Provence")

    weather_api = WeatherAPI(
        latitude=weather_latitude,
        longitude=weather_longitude,
        location_name=weather_location
    )

    # Déterminer si on utilise des données horaires ou journalières
    hourly = n_samples_per_day > 1
    
    # Calculate exact days needed for weather forecast
    # Start from current time, so we need to calculate days until end of prediction period
    end_date = start_date + timedelta(days=n_days)
    days_needed = (end_date - start_date).days + 1  # +1 to include partial start day
    
    logger.info(f"Prévisions météo nécessaires: {days_needed} jour(s) du {start_date} au {end_date}")
    
    # Fetch weather data only for the necessary days
    # Open-Meteo provides up to 16 days forecast
    weather_df = weather_api.fetch_forecast(
        forecast_days=min(days_needed, 16),
        hourly=hourly
    )

    # Créer un mapping Horodate -> données météo
    # Weather API returns hourly data, so we need to map to 30-minute intervals
    # We'll create a mapping for both the hour and the half-hour
    weather_mapping = {}
    for _, row in weather_df.iterrows():
        ts = row["Horodate"]
        # Map to the hour (e.g., 23:00)
        weather_mapping[ts] = {
            "temperature_2m_mean": row["temperature_2m_mean"],
            "relative_humidity_mean": row["relative_humidity_mean"],
            "precipitation_sum": row["precipitation_sum"]
        }
        # Also map to the half-hour (e.g., 23:30) using same values
        ts_half_hour = ts.replace(minute=30)
        weather_mapping[ts_half_hour] = {
            "temperature_2m_mean": row["temperature_2m_mean"],
            "relative_humidity_mean": row["relative_humidity_mean"],
            "precipitation_sum": row["precipitation_sum"]
        }
    
    logger.info(f"Mapping météo créé avec {len(weather_mapping)} entrées (horaire + demi-heure)")

    data = {}
    for col in feature_columns:
        if col in ("target_timestamp", "Horodate", "horodate"):  # A revoir pour être plus générique
            data[col] = timestamps
        elif col == "temperature_2m_mean":
            # Map 30-minute timestamps to weather data (mapping includes both hour and half-hour)
            data[col] = [weather_mapping.get(ts, {}).get("temperature_2m_mean", 20.0) for ts in timestamps]
        elif col == "relative_humidity_mean":
            data[col] = [weather_mapping.get(ts, {}).get("relative_humidity_mean", 50.0) for ts in timestamps]
        elif col == "precipitation_sum":
            data[col] = [weather_mapping.get(ts, {}).get("precipitation_sum", 0.0) for ts in timestamps]
        elif col == "is_vacances":
            data[col] = [holidays_mapping.get(ts, {}).get("is_vacances", 0) for ts in timestamps]
        elif col == "nom_vacances":
            data[col] = [holidays_mapping.get(ts, {}).get("nom_vacances", "") for ts in timestamps]
        elif col == "jour de la semaine":
            data[col] = [holidays_mapping.get(ts, {}).get("jour de la semaine", ts.strftime("%A")) for ts in timestamps]
        elif col == "jour férié":
            data[col] = [holidays_mapping.get(ts, {}).get("jour férié", 0) for ts in timestamps]
        else:
            logger.info(f"Feature manquante: {col}")

    df_inference = pd.DataFrame(data)
    
    # Add date-based features that the model expects (Heure and Jour)
    # These features are created during training via transform_date_columns
    # but the model was trained with specific column names 'Heure' and 'Jour'
    if "Horodate" in df_inference.columns:
        df_inference["Heure"] = df_inference["Horodate"].dt.hour
        df_inference["Jour"] = df_inference["Horodate"].dt.day
        logger.info(f"Features temporelles ajoutées: Heure, Jour")
    
    logger.info(f"Données d'inférence générées: {df_inference.shape[0]} échantillons")
    logger.info(f"Colonnes finales: {list(df_inference.columns)}")
    return df_inference


def add_predictions_to_data(df_inference, predictions):
    """Ajoute les prédictions au DataFrame d'inférence."""
    df_result = df_inference.copy()
    df_result["prediction"] = predictions

    logger.info(f"Prédictions ajoutées au DataFrame: {df_result.shape}")
    return df_result
