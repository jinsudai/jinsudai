"""
Flow Prefect pour la mise à jour quotidienne des données météo.

Ce flow est destiné à être exécuté quotidiennement pour mettre à jour
le fichier weather.parquet avec les nouvelles données météo.
"""
from prefect import flow
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import pandas as pd
import logging

from ml.connectors.weather.weather_tasks import generate_weather_parquet_task
from ml.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@flow(
    name="update_weather_daily",
    description="Met à jour quotidiennement le fichier weather.parquet avec les nouvelles données météo"
)
def update_weather_daily_flow(
    config_path: str = "src/configs/consumption.yaml",
    weather_output_path: Optional[str] = None,
    days_ahead: int = 7
) -> dict:
    """
    Flow Prefect : Met à jour le fichier weather.parquet quotidiennement.
    
    Ce flow:
    1. Récupère la dernière date du fichier weather.parquet existant
    2. Récupère les nouvelles données météo depuis cette date
    3. Met à jour le fichier weather.parquet en ajoutant les nouvelles données
    
    Args:
        config_path: Chemin vers la config consommation
        weather_output_path: Chemin vers le fichier weather.parquet (optionnel, lu depuis config)
        days_ahead: Nombre de jours à récupérer en avance (défaut: 7)
    
    Returns:
        dict: Contient status, start_date, end_date, n_new_records
    """
    # Charger la configuration
    config = load_config(config_path)
    
    # Récupérer les paramètres depuis la config
    latitude = config.get('data', {}).get('weather_latitude', 43.5297)
    longitude = config.get('data', {}).get('weather_longitude', 5.4474)
    location_name = config.get('data', {}).get('weather_location', 'Aix en Provence')
    
    if weather_output_path is None:
        weather_output_path = config.get('data', {}).get('weather_file', 'data/processed/weather.parquet')
    
    logger.info(f"Début de la mise à jour quotidienne de weather pour {location_name}")
    
    # 1. Déterminer la date de début
    weather_path = Path(weather_output_path)
    
    if weather_path.exists():
        # Récupérer la dernière date du fichier existant
        existing_df = pd.read_parquet(weather_path)
        if 'date' in existing_df.columns:
            last_date = pd.to_datetime(existing_df['date']).max()
            start_date = last_date + timedelta(days=1)
        else:
            # Fallback: utiliser la date actuelle - 30 jours
            start_date = datetime.now() - timedelta(days=30)
            logger.warning("Colonne 'date' non trouvée, utilisation de la date par défaut")
    else:
        # Pas de fichier existant, utiliser une date par défaut (30 jours en arrière)
        start_date = datetime.now() - timedelta(days=30)
        logger.info(f"Pas de fichier weather existant, création à partir du {start_date}")
    
    # 2. Déterminer la date de fin (aujourd'hui + days_ahead)
    end_date = datetime.now() + timedelta(days=days_ahead)
    
    logger.info(f"Période de mise à jour: {start_date.strftime('%Y-%m-%d')} à {end_date.strftime('%Y-%m-%d')}")
    
    # 3. Récupérer les nouvelles données météo
    try:
        temp_output_path = f"data/temp/weather_update_{location_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        
        generate_weather_parquet_task(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            output_path=temp_output_path,
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            validate=True
        )
        
        # 4. Fusionner avec les données existantes
        new_weather_df = pd.read_parquet(temp_output_path)
        
        if weather_path.exists():
            existing_df = pd.read_parquet(weather_path)
            # Supprimer les doublons (basés sur la date)
            if 'date' in existing_df.columns and 'date' in new_weather_df.columns:
                existing_df['date'] = pd.to_datetime(existing_df['date'])
                new_weather_df['date'] = pd.to_datetime(new_weather_df['date'])
                combined_df = pd.concat([existing_df, new_weather_df])
                combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
                combined_df = combined_df.sort_values('date')
            else:
                combined_df = pd.concat([existing_df, new_weather_df])
        else:
            combined_df = new_weather_df
        
        # 5. Sauvegarder le fichier mis à jour
        combined_df.to_parquet(weather_output_path, index=False)
        
        # 6. Nettoyer le fichier temporaire
        Path(temp_output_path).unlink(missing_ok=True)
        
        n_new_records = len(new_weather_df)
        n_total_records = len(combined_df)
        
        logger.info(f"✅ Weather mis à jour: {n_new_records} nouveaux enregistrements, {n_total_records} total")
        
        return {
            "status": "success",
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "n_new_records": n_new_records,
            "n_total_records": n_total_records,
            "output_path": str(weather_output_path)
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de weather: {e}")
        return {
            "status": "error",
            "error": str(e),
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d')
        }


if __name__ == "__main__":
    # Exécution manuelle pour tester
    result = update_weather_daily_flow()
    print(f"Résultat: {result}")
