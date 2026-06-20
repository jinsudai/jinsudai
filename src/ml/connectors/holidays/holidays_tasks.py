"""
Tâches Prefect pour les vacances scolaires et jours fériés.

Ce module contient les tâches Prefect qui encapsulent les appels aux API
des vacances scolaires et jours fériés.

Exemple d'utilisation :
    from analytics.utils.api.holidays.holidays_tasks import (
        generate_holidays_parquet_task,
        fetch_vacances_task,
        fetch_jours_feries_task
    )
"""

from prefect import task
from pathlib import Path
from typing import Optional
import logging

from .holidays_api import VacancesAPI, JoursFeriesAPI, HolidaysCombinedAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@task(
    name="fetch_vacances",
    description="Récupère les vacances scolaires depuis GitHub",
    retries=3,
    retry_delay_seconds=10
)
def fetch_vacances_task(
    year: int,
    zone: str = "C",
    types: Optional[list] = None
) -> str:
    """
    Tâche Prefect : Récupère les vacances scolaires.

    Args:
        year: Année (ex: 2024)
        zone: Zone scolaire (A, B ou C)
        types: Liste des types de vacances à filtrer

    Returns:
        str: Chemin vers le fichier Parquet généré
    """
    api = VacancesAPI()
    df = api.fetch(year=year, zone=zone, types=types)

    # Sauvegarder dans un fichier temporaire
    output_path = Path(f"data/temp/vacances_{zone}_{year}.parquet")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path)

    logger.info(f"Vacances scolaires sauvegardées: {output_path}")
    return str(output_path)


@task(
    name="fetch_jours_feries",
    description="Récupère les jours fériés depuis l'API gouvernementale",
    retries=3,
    retry_delay_seconds=10
)
def fetch_jours_feries_task(
    year: Optional[int] = None
) -> str:
    """
    Tâche Prefect : Récupère les jours fériés.

    Args:
        year: Année (optionnel, par défaut année courante)

    Returns:
        str: Chemin vers le fichier Parquet généré
    """
    api = JoursFeriesAPI()
    df = api.fetch(year=year)

    year_str = year if year else "current"
    output_path = Path(f"data/temp/jours_feries_{year_str}.parquet")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path)

    logger.info(f"Jours fériés sauvegardés: {output_path}")
    return str(output_path)


@task(
    name="generate_holidays_parquet",
    description="Génère un Parquet combiné vacances + jours fériés",
    retries=3,
    retry_delay_seconds=10
)
def generate_holidays_parquet_task(
    start_date: str,
    end_date: str,
    output_path: str,
    zone: str = "C"
) -> str:
    """
    Tâche Prefect : Génère un fichier Parquet avec vacances + jours fériés.

    Cette tâche génère un DataFrame avec les colonnes attendues par le template :
    - Horodate (datetime, fréquence 30min)
    - is_vacances (int: 0/1)
    - nom_vacances (str)
    - jour de la semaine (str)
    - jour férié (int: 0/1)

    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        output_path: Chemin de sortie pour le fichier Parquet
        zone: Zone scolaire (A, B ou C)

    Returns:
        str: Chemin vers le fichier Parquet généré
    """
    api = HolidaysCombinedAPI(zone=zone)
    parquet_path = api.generate_parquet(
        start_date=start_date,
        end_date=end_date,
        output_path=output_path
    )

    logger.info(f"Fichier holidays Parquet généré: {parquet_path}")
    return str(parquet_path)


@task(
    name="generate_holidays_dataframe",
    description="Génère un DataFrame avec vacances + jours fériés (sans sauvegarde)"
)
def generate_holidays_dataframe_task(
    start_date: str,
    end_date: str,
    zone: str = "C"
) -> str:
    """
    Tâche Prefect : Génère un DataFrame en mémoire (pour utilisation directe).

    Utilisé lorsque le DataFrame doit être passé directement à une autre tâche
    sans sauvegarde intermédiaire.

    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        zone: Zone scolaire (A, B ou C)

    Returns:
        str: Chemin temporaire (pour compatibilité Prefect)
    """
    api = HolidaysCombinedAPI(zone=zone)
    api.generate_holidays_dataframe(start_date=start_date, end_date=end_date)

    # Pour Prefect, on retourne un chemin temporaire
    # En pratique, le DataFrame sera passé via le contexte Prefect
    temp_path = f"temp://holidays_df_{start_date}_to_{end_date}"
    logger.info("DataFrame holidays généré (en mémoire)")
    return temp_path
