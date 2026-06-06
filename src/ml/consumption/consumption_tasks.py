"""
Tâches Prefect pour la préparation des données de consommation électrique.

Ce module contient les tâches Prefect qui encapsulent la préparation
des données de consommation à partir des fichiers bruts PRM.

Exemple d'utilisation :
    from analytics.consumption.consumption_tasks import prepare_consumption_features_task
    
    # Dans un flow Prefect
    features_path = prepare_consumption_features_task(
        raw_path="data/templates/raw_template.csv",
        weather_path="data/raw/weather.parquet",
        holidays_path="data/raw/holidays.parquet",
        output_path="data/processed/consumption_features.parquet"
    )
"""

from prefect import task
from pathlib import Path
from typing import Optional
import logging

from .consumption_preparer import ConsumptionDataPreparer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@task(
    name="prepare_consumption_features",
    description="Prépare les features consommation à partir des données brutes PRM, météo et calendrier",
    retries=2,
    retry_delay_seconds=30
)
def prepare_consumption_features_task(
    raw_path: str,
    weather_path: str,
    holidays_path: str,
    output_path: str
) -> str:
    """
    Tâche Prefect : Prépare les données de consommation pour l'entraînement.
    
    Cette tâche :
    1. Charge le fichier brut PRM (raw_template.csv)
    2. Extrait les colonnes Horodate et Valeur
    3. Fusionne avec les données météo
    4. Fusionne avec les données vacances/jours fériés
    5. Valide que le résultat correspond au template conso_features_template.csv
    6. Sauvegarde en Parquet
    
    Args:
        raw_path: Chemin vers le fichier brut PRM (ex: data/templates/raw_template.csv)
        weather_path: Chemin vers le Parquet météo (ex: data/raw/weather.parquet)
        holidays_path: Chemin vers le Parquet vacances (ex: data/raw/holidays.parquet)
        output_path: Chemin de sortie pour le fichier Parquet final (ex: data/processed/consumption_features.parquet)
    
    Returns:
        str: Chemin vers le fichier Parquet généré
        
    Raises:
        ValueError: Si validation échoue (colonnes manquantes, données invalides)
        FileNotFoundError: Si un fichier d'entrée est introuvable
    """
    preparer = ConsumptionDataPreparer()
    
    # Exécuter le pipeline de préparation
    features_df = preparer.prepare(
        raw_path=raw_path,
        weather_path=weather_path,
        holidays_path=holidays_path,
        output_path=output_path
    )
    
    logger.info(f"✅ Tâche terminée: {len(features_df)} enregistrements prêts pour l'entraînement")
    return output_path


@task(
    name="prepare_consumption_from_parquets",
    description="Prépare les features consommation à partir de Parquets existants",
    retries=2,
    retry_delay_seconds=30
)
def prepare_consumption_from_parquets_task(
    consumption_parquet: str,
    weather_parquet: str,
    holidays_parquet: str,
    output_path: str
) -> str:
    """
    Tâche Prefect : Prépare les données à partir de Parquets déjà générés.
    
    Alternative à prepare_consumption_features_task lorsque les données
    brutes sont déjà en format Parquet.
    
    Args:
        consumption_parquet: Parquet avec Horodate, Valeur
        weather_parquet: Parquet météo
        holidays_parquet: Parquet vacances/jours fériés
        output_path: Chemin de sortie
    
    Returns:
        str: Chemin vers le fichier Parquet généré
    """
    preparer = ConsumptionDataPreparer()
    
    # Non implémenté, mais pourrait être utile pour ne pas générer les features à partir du CSV brut à chaque fois
    # Exemple d'implémentation possible (désactivée) :
    # features_df = preparer.prepare_from_parquets(
    #     consumption_parquet=consumption_parquet,
    #     weather_parquet=weather_parquet,
    #     holidays_parquet=holidays_parquet,
    #     output_path=output_path
    # )
    # logger.info(f"✅ Tâche terminée (depuis Parquets): {len(features_df)} enregistrements")
    # return output_path

    print("⚠️ prepare_consumption_from_parquets_task n'est pas encore implémentée")
    return "not_implemented"


@task(
    name="validate_consumption_features",
    description="Valide qu'un DataFrame correspond au template consommation"
)
def validate_consumption_features_task(
    features_path: str
) -> bool:
    """
    Tâche Prefect : Valide un fichier de features consommation.
    
    Utilisé pour vérifier que les données sont prêtes avant l'entraînement.
    
    Args:
        features_path: Chemin vers le fichier Parquet à valider
    
    Returns:
        bool: True si valide
    """
    import pandas as pd
    from .consumption_preparer import ConsumptionDataPreparer, FEATURES_TEMPLATE_COLUMNS
    
    preparer = ConsumptionDataPreparer()
    df = pd.read_parquet(features_path)
    
    # Valider
    is_valid = preparer.validate_against_template(df)
    
    if is_valid:
        logger.info(f"✅ Validation réussie: {features_path}")
    else:
        logger.error(f"❌ Validation échouée: {features_path}")
    
    return is_valid
