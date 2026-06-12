"""
Flow Prefect pour la génération annuelle du fichier holidays.parquet.

Ce flow génère un fichier Parquet combinant vacances scolaires et jours fériés
pour une année complète. Ce fichier est utilisé par les autres pipelines pour
les features calendar.

Exemple d'utilisation :
    from ml.workflows.holidays_flow import holidays_annual_pipeline
    
    # Exécuter le pipeline pour une année
    result = holidays_annual_pipeline(year=2024)
"""

from prefect import flow
from pathlib import Path
from typing import Dict, Any
import logging

from ml.connectors.holidays.holidays_tasks import generate_holidays_parquet_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@flow(
    name="holidays-annual-pipeline",
    description="Génère le fichier holidays.parquet pour une année complète"
)
def holidays_annual_pipeline(
    year: int,
    output_dir: str = "data/processed/",
    zone: str = "C"
) -> Dict[str, Any]:
    """
    Pipeline annuel pour générer le fichier holidays.parquet.
    
    Ce flow génère un fichier Parquet contenant :
    - Horodate (datetime, fréquence 30min)
    - is_vacances (int: 0/1)
    - nom_vacances (str)
    - jour de la semaine (str)
    - jour férié (int: 0/1)
    
    Args:
        year: Année à générer (ex: 2024)
        output_dir: Répertoire de sortie pour le fichier Parquet
        zone: Zone scolaire (A, B ou C)
    
    Returns:
        Dict avec le chemin du fichier généré et les métadonnées
    """
    logger.info(f"=== Pipeline annuel holidays pour l'année {year} ===")
    
    # Définir les dates de début et fin de l'année
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # Définir le chemin de sortie
    output_path = Path(output_dir) / f"holidays_{year}.parquet"
    
    logger.info(f"Génération du fichier holidays du {start_date} au {end_date}")
    logger.info(f"Zone scolaire: {zone}")
    logger.info(f"Chemin de sortie: {output_path}")
    
    # Générer le fichier Parquet
    parquet_path = generate_holidays_parquet_task(
        start_date=start_date,
        end_date=end_date,
        output_path=str(output_path),
        zone=zone
    )
    
    logger.info(f"✅ Fichier holidays.parquet généré: {parquet_path}")
    
    return {
        "status": "success",
        "year": year,
        "zone": zone,
        "output_path": str(parquet_path),
        "start_date": start_date,
        "end_date": end_date
    }


if __name__ == "__main__":
    # Test du pipeline
    import sys
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    
    result = holidays_annual_pipeline(year=year)
    print(f"Résultat: {result}")
