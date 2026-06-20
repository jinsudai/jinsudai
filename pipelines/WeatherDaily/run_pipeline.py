"""
Script d'entrée pour le pipeline de mise à jour météo quotidienne (sans Prefect).

Usage:
    python run_pipeline.py --days_ahead 7
"""
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import logging

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from ml.connectors.weather.weather_tasks import generate_weather_parquet_task
from ml.connectors.s3.s3_tasks import upload_file_to_s3_task
from ml.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_weather_daily_simple(
    config_path: str = "src/configs/consumption.yaml",
    weather_source_path: str = None,
    weather_prod_path: str = None,
    days_ahead: int = 7,
    upload_to_s3: bool = False,
    s3_bucket: str = None,
    s3_prefix: str = None,
    aws_access_key_id: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = "us-east-1",
    endpoint_url: str = None
) -> dict:
    """
    Pipeline simple pour mettre à jour les données météo quotidiennes (sans Prefect).
    """
    # Charger la config
    config = load_config(config_path=config_path)
    
    # Valeurs par défaut depuis la config
    if s3_bucket is None:
        s3_bucket = config.get('s3', {}).get('bucket', 'data-store')
    if s3_prefix is None:
        s3_prefix = config.get('s3', {}).get('prefix', 'weather')
    
    # Définir les chemins par défaut
    if weather_source_path is None:
        weather_source_path = config.get('data', {}).get('weather_file', 'data/source/weather_raw.parquet')
    if weather_prod_path is None:
        weather_prod_path = config.get('data', {}).get('weather_file', 'data/processed/weather.parquet')
    
    # Coordonnées météo depuis la config
    latitude = config.get('data', {}).get('weather_latitude', 43.5297)
    longitude = config.get('data', {}).get('weather_longitude', 5.4474)
    location_name = config.get('data', {}).get('weather_location', 'Aix en Provence')
    
    logger.info("=== MISE À JOUR MÉTÉO QUOTIDIENNE ===")
    logger.info(f"Location: {location_name} ({latitude}, {longitude})")
    
    # 1. Déterminer la date de début
    source_path = Path(weather_source_path)
    if source_path.exists():
        existing_df = pd.read_parquet(source_path)
        if 'date' in existing_df.columns:
            last_date = pd.to_datetime(existing_df['date']).max()
            start_date = last_date + timedelta(days=1)
        else:
            start_date = datetime.now() - timedelta(days=30)
            logger.warning("Colonne 'date' non trouvée, utilisation de la date par défaut")
    else:
        start_date = datetime.now() - timedelta(days=30)
        logger.info(f"Pas de fichier source existant, création à partir du {start_date}")
    
    # 2. Déterminer la date de fin
    end_date = datetime.now() + timedelta(days=days_ahead)
    logger.info(f"Période: {start_date.strftime('%Y-%m-%d')} à {end_date.strftime('%Y-%m-%d')}")
    
    try:
        # 3. Récupérer les nouvelles données météo
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
        
        # 4. Fusionner avec le fichier source existant
        new_weather_df = pd.read_parquet(temp_output_path)
        if source_path.exists():
            existing_source_df = pd.read_parquet(source_path)
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
        
        # 5. Sauvegarder le fichier source
        combined_source_df.to_parquet(weather_source_path, index=False)
        logger.info(f"Fichier source mis à jour: {weather_source_path}")
        
        # 6. Traiter et sauvegarder le fichier prod
        prod_df = combined_source_df.copy()
        prod_df.to_parquet(weather_prod_path, index=False)
        logger.info(f"Fichier prod mis à jour: {weather_prod_path}")
        
        # 7. Nettoyer le fichier temporaire
        Path(temp_output_path).unlink(missing_ok=True)
        
        n_new_records = len(new_weather_df)
        n_total_records = len(combined_source_df)
        logger.info(f"Weather mis à jour: {n_new_records} nouveaux enregistrements, {n_total_records} total")
        
        # 8. Upload sur S3 (optionnel)
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
                    logger.info(f"Upload S3 réussi: source={source_upload['s3_uri']}, prod={prod_upload['s3_uri']}")
                else:
                    logger.warning("Upload S3 partiellement ou totalement échoué")
        
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

def main():
    parser = argparse.ArgumentParser(description='Exécute le pipeline de mise à jour météo quotidienne')
    parser.add_argument('--config_path', type=str, default='src/configs/consumption.yaml', help='Chemin vers la config')
    parser.add_argument('--weather_source_path', type=str, default=None, help='Chemin vers le fichier source brut')
    parser.add_argument('--weather_prod_path', type=str, default=None, help='Chemin vers le fichier prod traité')
    parser.add_argument('--days_ahead', type=int, default=7, help='Nombre de jours à récupérer en avance')
    parser.add_argument('--upload_to_s3', action='store_true', help='Uploader les fichiers sur S3')
    parser.add_argument('--s3_bucket', type=str, default=None, help='Nom du bucket S3 (défaut: data-store)')
    parser.add_argument('--s3_prefix', type=str, default=None, help='Préfixe S3 pour les fichiers (défaut: weather)')
    parser.add_argument('--aws_access_key_id', type=str, default=None, help='AWS access key ID')
    parser.add_argument('--aws_secret_access_key', type=str, default=None, help='AWS secret access key')
    parser.add_argument('--aws_region', type=str, default='us-east-1', help='AWS region')
    parser.add_argument('--endpoint_url', type=str, default=None, help='URL endpoint custom pour S3-compatible services')
    
    args = parser.parse_args()
    
    print(f"=== Exécution du pipeline de mise à jour météo quotidienne ===")
    print(f"Jours en avance: {args.days_ahead}")
    if args.upload_to_s3:
        print(f"Upload S3 activé: bucket={args.s3_bucket}, prefix={args.s3_prefix}")
    
    result = update_weather_daily_simple(
        config_path=args.config_path,
        weather_source_path=args.weather_source_path,
        weather_prod_path=args.weather_prod_path,
        days_ahead=args.days_ahead,
        upload_to_s3=args.upload_to_s3,
        s3_bucket=args.s3_bucket,
        s3_prefix=args.s3_prefix,
        aws_access_key_id=args.aws_access_key_id,
        aws_secret_access_key=args.aws_secret_access_key,
        aws_region=args.aws_region,
        endpoint_url=args.endpoint_url
    )
    
    print(f"\n=== Résultat ===")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Fichier source: {result.get('source_path')}")
        print(f"Fichier prod: {result.get('prod_path')}")
        print(f"Nouveaux enregistrements: {result.get('n_new_records')}")
        print(f"Total enregistrements: {result.get('n_total_records')}")
        
        if result.get('s3_info'):
            print(f"\n=== Upload S3 ===")
            if result['s3_info'].get('source', {}).get('status') == 'success':
                print(f"Source: {result['s3_info']['source']['s3_uri']}")
            if result['s3_info'].get('prod', {}).get('status') == 'success':
                print(f"Prod: {result['s3_info']['prod']['s3_uri']}")
    
    return result

if __name__ == "__main__":
    main()
