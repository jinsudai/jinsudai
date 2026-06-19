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
from ml.connectors.s3.s3_tasks import upload_file_to_s3_task
from ml.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@flow(
    name="update_weather_daily",
    description="Met à jour quotidiennement les fichiers météo: source (brut) et prod (traité)"
)
def update_weather_daily_flow(
    config_path: str = "src/configs/consumption.yaml",
    weather_source_path: Optional[str] = None,
    weather_prod_path: Optional[str] = None,
    days_ahead: int = 7,
    upload_to_s3: bool = False,
    s3_bucket: Optional[str] = None,
    s3_prefix: Optional[str] = "weather",
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    aws_region: str = "us-east-1",
    endpoint_url: Optional[str] = None
) -> dict:
    """
    Flow Prefect : Met à jour quotidiennement les fichiers météo source et prod.
    
    Ce flow:
    1. Récupère la dernière date du fichier source existant
    2. Récupère les nouvelles données météo depuis cette date
    3. Sauvegarde les données brutes dans le fichier source
    4. Traite et valide les données
    5. Sauvegarde les données traitées dans le fichier prod
    6. (Optionnel) Upload les fichiers sur S3
    
    Args:
        config_path: Chemin vers la config consommation
        weather_source_path: Chemin vers le fichier source brut (optionnel)
        weather_prod_path: Chemin vers le fichier prod traité (optionnel)
        days_ahead: Nombre de jours à récupérer en avance (défaut: 7)
        upload_to_s3: Si True, upload les fichiers sur S3 (défaut: False)
        s3_bucket: Nom du bucket S3 (requis si upload_to_s3=True)
        s3_prefix: Préfixe S3 pour les fichiers (défaut: "weather")
        aws_access_key_id: AWS access key ID (optionnel)
        aws_secret_access_key: AWS secret access key (optionnel)
        aws_region: AWS region (défaut: us-east-1)
        endpoint_url: URL endpoint custom pour S3-compatible services (optionnel)
    
    Returns:
        dict: Contient status, start_date, end_date, n_new_records, paths, s3_info
    """
    # Charger la configuration
    config = load_config(config_path)
    
    # Récupérer les paramètres depuis la config
    latitude = config.get('data', {}).get('weather_latitude', 43.5297)
    longitude = config.get('data', {}).get('weather_longitude', 5.4474)
    location_name = config.get('data', {}).get('weather_location', 'Aix en Provence')
    
    # Définir les chemins par défaut
    if weather_source_path is None:
        weather_source_path = config.get('data', {}).get('weather_source_file', 'data/source/weather_raw.parquet')
    if weather_prod_path is None:
        weather_prod_path = config.get('data', {}).get('weather_file', 'data/processed/weather.parquet')
    
    logger.info(f"Début de la mise à jour quotidienne de weather pour {location_name}")
    logger.info(f"Fichier source: {weather_source_path}")
    logger.info(f"Fichier prod: {weather_prod_path}")
    
    # Créer les répertoires nécessaires
    Path(weather_source_path).parent.mkdir(parents=True, exist_ok=True)
    Path(weather_prod_path).parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Déterminer la date de début (basé sur le fichier source)
    source_path = Path(weather_source_path)
    
    if source_path.exists():
        # Récupérer la dernière date du fichier source existant
        existing_df = pd.read_parquet(source_path)
        if 'date' in existing_df.columns:
            last_date = pd.to_datetime(existing_df['date']).max()
            start_date = last_date + timedelta(days=1)
        else:
            # Fallback: utiliser la date actuelle - 30 jours
            start_date = datetime.now() - timedelta(days=30)
            logger.warning("Colonne 'date' non trouvée dans le fichier source, utilisation de la date par défaut")
    else:
        # Pas de fichier source existant, utiliser une date par défaut (30 jours en arrière)
        start_date = datetime.now() - timedelta(days=30)
        logger.info(f"Pas de fichier source existant, création à partir du {start_date}")
    
    # 2. Déterminer la date de fin (aujourd'hui + days_ahead)
    end_date = datetime.now() + timedelta(days=days_ahead)
    
    logger.info(f"Période de mise à jour: {start_date.strftime('%Y-%m-%d')} à {end_date.strftime('%Y-%m-%d')}")
    
    # 3. Récupérer les nouvelles données météo et sauvegarder dans le fichier source
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
        
        # 4. Fusionner avec le fichier source (données brutes)
        new_weather_df = pd.read_parquet(temp_output_path)
        
        if source_path.exists():
            existing_source_df = pd.read_parquet(source_path)
            # Supprimer les doublons (basés sur la date)
            if 'date' in existing_source_df.columns and 'date' in new_weather_df.columns:
                existing_source_df['date'] = pd.to_datetime(existing_source_df['date'])
                new_weather_df['date'] = pd.to_datetime(new_weather_df['date'])
                combined_source_df = pd.concat([existing_source_df, new_weather_df])
                combined_source_df = combined_source_df.drop_duplicates(subset=['date'], keep='last')
                combined_source_df = combined_source_df.sort_values('date')
            else:
                combined_source_df = pd.concat([existing_source_df, new_weather_df])
        else:
            combined_source_df = new_weather_df
        
        # 5. Sauvegarder le fichier source (données brutes)
        combined_source_df.to_parquet(weather_source_path, index=False)
        logger.info(f"✅ Fichier source mis à jour: {weather_source_path}")
        
        # 6. Traiter les données pour le fichier prod (copie simple pour l'instant)
        # À l'avenir, ajouter ici des transformations/validations spécifiques
        prod_df = combined_source_df.copy()
        
        # 7. Sauvegarder le fichier prod (données traitées)
        prod_df.to_parquet(weather_prod_path, index=False)
        logger.info(f"✅ Fichier prod mis à jour: {weather_prod_path}")
        
        # 8. Nettoyer le fichier temporaire
        Path(temp_output_path).unlink(missing_ok=True)
        
        n_new_records = len(new_weather_df)
        n_total_records = len(combined_source_df)
        
        logger.info(f"✅ Weather mis à jour: {n_new_records} nouveaux enregistrements, {n_total_records} total")
        
        # 9. Upload sur S3 (optionnel)
        s3_info = {}
        if upload_to_s3:
            if not s3_bucket:
                logger.warning("upload_to_s3=True mais s3_bucket non fourni, upload S3 ignoré")
            else:
                logger.info("=== Upload sur S3 ===")
                
                # Upload fichier source
                source_filename = Path(weather_source_path).name
                s3_source_key = f"{s3_prefix}/source/{source_filename}"
                source_upload = upload_file_to_s3_task(
                    file_path=weather_source_path,
                    bucket_name=s3_bucket,
                    s3_key=s3_source_key,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_region=aws_region,
                    endpoint_url=endpoint_url
                )
                s3_info["source"] = source_upload
                
                # Upload fichier prod
                prod_filename = Path(weather_prod_path).name
                s3_prod_key = f"{s3_prefix}/prod/{prod_filename}"
                prod_upload = upload_file_to_s3_task(
                    file_path=weather_prod_path,
                    bucket_name=s3_bucket,
                    s3_key=s3_prod_key,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_region=aws_region,
                    endpoint_url=endpoint_url
                )
                s3_info["prod"] = prod_upload
                
                if source_upload["status"] == "success" and prod_upload["status"] == "success":
                    logger.info(f"✅ Upload S3 réussi: source={source_upload['s3_uri']}, prod={prod_upload['s3_uri']}")
                else:
                    logger.warning("⚠️ Upload S3 partiellement ou totalement échoué")
        
        return {
            "status": "success",
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "n_new_records": n_new_records,
            "n_total_records": n_total_records,
            "source_path": str(weather_source_path),
            "prod_path": str(weather_prod_path),
            "s3_info": s3_info if upload_to_s3 else None
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
