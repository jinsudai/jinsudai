"""
Fonctions pour les vacances scolaires et jours fériés.

Ce module contient les fonctions qui encapsulent les appels aux API
des vacances scolaires et jours fériés.

Exemple d'utilisation :
    from ml.connectors.holidays.holidays_tasks import (
        generate_holidays_parquet,
        fetch_vacances,
        fetch_jours_feries
    )
"""

from pathlib import Path
from typing import Optional
import logging

from .holidays_api import VacancesAPI, JoursFeriesAPI, HolidaysCombinedAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_vacances(
    year: int,
    zone: str = "C",
    types: Optional[list] = None
) -> str:
    """
    Récupère les vacances scolaires.

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


def fetch_jours_feries(
    year: Optional[int] = None
) -> str:
    """
    Récupère les jours fériés.

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


def generate_holidays_parquet(
    start_date: str,
    end_date: str,
    output_path: str,
    zone: str = "C"
) -> str:
    """
    Génère un fichier Parquet avec vacances + jours fériés.

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


def generate_holidays_dataframe(
    start_date: str,
    end_date: str,
    zone: str = "C"
) -> str:
    """
    Génère un DataFrame en mémoire (pour utilisation directe).

    Utilisé lorsque le DataFrame doit être passé directement à une autre fonction
    sans sauvegarde intermédiaire.

    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        zone: Zone scolaire (A, B ou C)

    Returns:
        str: Chemin temporaire
    """
    api = HolidaysCombinedAPI(zone=zone)
    api.generate_holidays_dataframe(start_date=start_date, end_date=end_date)

    # On retourne un chemin temporaire
    # En pratique, le DataFrame sera passé directement
    temp_path = f"temp://holidays_df_{start_date}_to_{end_date}"
    logger.info("DataFrame holidays généré (en mémoire)")
    return temp_path
