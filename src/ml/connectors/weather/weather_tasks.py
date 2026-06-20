"""
Tâches Prefect pour l'API météo.

Ce module contient les tâches Prefect qui encapsulent les appels à l'API Open-Meteo
pour générer des fichiers Parquet avec les données météo.

Exemple d'utilisation :
    from analytics.utils.api.weather.weather_tasks import (
        fetch_weather_task,
        generate_weather_parquet_task
    )
"""

from prefect import task
from pathlib import Path
from typing import Optional
import logging

from .weather_api import WeatherAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@task(
    name="fetch_weather",
    description="Récupère les données météo historiques depuis Open-Meteo",
    retries=3,
    retry_delay_seconds=30
)
def fetch_weather_task(
    start_date: str,
    end_date: str,
    latitude: float = 43.5297,  # Aix en Provence par défaut
    longitude: float = 5.4474,
    location_name: str = "Aix en Provence",
    hourly: bool = True
) -> str:
    """
    Tâche Prefect : Récupère les données météo historiques.

    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        latitude: Latitude de la localisation
        longitude: Longitude de la localisation
        location_name: Nom de la localisation
        hourly: Si True, récupère données horaires

    Returns:
        str: Chemin vers le fichier Parquet temporaire
    """
    api = WeatherAPI(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name
    )

    df = api.fetch_historical(start_date=start_date, end_date=end_date, hourly=hourly)

    # Sauvegarder temporairement
    temp_path = Path(f"data/temp/weather_{location_name}_{start_date}_to_{end_date}.parquet")
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(temp_path)

    logger.info(f"Données météo sauvegardées: {temp_path}")
    return str(temp_path)


@task(
    name="generate_weather_parquet",
    description="Génère un fichier Parquet avec les données météo",
    retries=3,
    retry_delay_seconds=30
)
def generate_weather_parquet_task(
    start_date: str,
    end_date: str,
    output_path: str,
    latitude: float = 43.5297,
    longitude: float = 5.4474,
    location_name: str = "Aix en Provence",
    validate: bool = True
) -> str:
    """
    Tâche Prefect : Génère un fichier Parquet avec les données météo.

    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        output_path: Chemin de sortie pour le fichier Parquet
        latitude: Latitude de la localisation
        longitude: Longitude de la localisation
        location_name: Nom de la localisation
        validate: Si True, valide les données avant sauvegarde

    Returns:
        str: Chemin vers le fichier Parquet généré
    """
    api = WeatherAPI(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name
    )

    # Récupérer les données
    api.fetch_historical(start_date=start_date, end_date=end_date, hourly=True)

    # Valider si demandé
    if validate:
        validation = api.validate_data()
        if not validation["is_valid"]:
            logger.warning(f"Données météo invalides: {validation['errors']}")
            if validation["errors"]:
                raise ValueError(f"Validation échouée: {validation['errors']}")
        if validation["warnings"]:
            logger.info(f"Avertissements météo: {validation['warnings']}")

    # Générer le Parquet
    api.generate_parquet(output_path=output_path)

    logger.info(f"Fichier météo Parquet généré: {output_path}")
    return output_path


@task(
    name="generate_weather_dataframe",
    description="Génère un DataFrame météo (sans sauvegarde)"
)
def generate_weather_dataframe_task(
    start_date: str,
    end_date: str,
    latitude: float = 43.5297,
    longitude: float = 5.4474,
    location_name: str = "Aix en Provence"
) -> str:
    """
    Tâche Prefect : Génère un DataFrame météo en mémoire.

    Utilisé lorsque le DataFrame doit être passé directement à une autre tâche
    sans sauvegarde intermédiaire.

    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        latitude: Latitude de la localisation
        longitude: Longitude de la localisation
        location_name: Nom de la localisation

    Returns:
        str: Chemin temporaire (pour compatibilité Prefect)
    """
    api = WeatherAPI(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name
    )

    df = api.fetch_historical(start_date=start_date, end_date=end_date, hourly=True)

    # Pour Prefect, on retourne un chemin temporaire
    temp_path = f"temp://weather_df_{location_name}_{start_date}_to_{end_date}"
    logger.info(f"DataFrame météo généré (en mémoire)")
    return temp_path
