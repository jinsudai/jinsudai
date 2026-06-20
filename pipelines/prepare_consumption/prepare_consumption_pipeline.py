"""
Pipeline pour préparer les features de consommation et les stocker sur S3.

Ce pipeline:
1. Charge les données brutes PRM
2. Récupère les données météo
3. Récupère les données vacances/jours fériés
4. Fusionne et prépare les features
5. Sauvegarde localement en Parquet
6. Upload sur S3 si les credentials sont disponibles

Usage:
    python pipelines/prepare_consumption/prepare_consumption_pipeline.py \
        --start_date 2024-01-01 \
        --end_date 2024-01-31 \
        --raw_path data/templates/raw_consumption.csv
"""
import argparse
import sys
from pathlib import Path
import logging

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.consumption.consumption_preparer import ConsumptionDataPreparer
from ml.connectors.weather.weather_api import WeatherAPI
from ml.connectors.holidays.holidays_api import VacancesAPI, JoursFeriesAPI
from ml.utils.s3_handler import S3Handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def prepare_consumption_features_pipeline(
    start_date: str,
    end_date: str,
    raw_path: str,
    output_dir: str = "data/processed/",
    upload_to_s3: bool = True,
    s3_bucket: str = None,
    s3_prefix: str = "consumption/features/"
) -> dict:
    """
    Pipeline complet pour préparer les features consommation.
    
    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        raw_path: Chemin vers le fichier brut PRM
        output_dir: Répertoire de sortie local
        upload_to_s3: Si True, upload sur S3
        s3_bucket: Nom du bucket S3 (défaut: depuis env)
        s3_prefix: Préfixe S3 pour les fichiers
        
    Returns:
        dict: Résultat du pipeline avec chemins locaux et S3
    """
    logger.info("=" * 60)
    logger.info("PIPELINE PRÉPARATION FEATURES CONSOMMATION")
    logger.info("=" * 60)
    
    # Créer le répertoire de sortie
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Générer les données météo
    logger.info("\n[1/4] Génération des données météo...")
    weather_path = output_dir / f"weather_{start_date}_to_{end_date}.parquet"
    
    if weather_path.exists():
        logger.info(f"  ℹ️ Fichier météo existe déjà: {weather_path}")
    else:
        try:
            weather_api = WeatherAPI(
                latitude=43.5297,
                longitude=5.4474,
                location_name="Aix en Provence"
            )
            weather_df = weather_api.fetch_historical(
                start_date=start_date,
                end_date=end_date,
                hourly=True
            )
            weather_df.to_parquet(weather_path)
            logger.info(f"  ✅ Météo générée: {weather_path}")
        except Exception as e:
            logger.error(f"  ❌ Erreur génération météo: {e}")
            return {"status": "error", "step": "weather", "error": str(e)}
    
    # 2. Générer les données vacances/jours fériés
    logger.info("\n[2/4] Génération des données vacances/jours fériés...")
    holidays_path = output_dir / f"holidays_{start_date}_to_{end_date}.parquet"
    
    if holidays_path.exists():
        logger.info(f"  ℹ️ Fichier vacances existe déjà: {holidays_path}")
    else:
        try:
            start_year = int(start_date.split('-')[0])
            end_year = int(end_date.split('-')[0])
            
            vacances_api = VacancesAPI()
            vacances_dfs = []
            for year in range(start_year, end_year + 1):
                df_vacances = vacances_api.fetch(year=year, zone="C")
                vacances_dfs.append(df_vacances)
            vacances_df = vacances_dfs[0] if vacances_dfs else None
            
            feries_api = JoursFeriesAPI()
            feries_dfs = []
            for year in range(start_year, end_year + 1):
                df_feries = feries_api.fetch(year=year)
                feries_dfs.append(df_feries)
            feries_df = feries_dfs[0] if feries_dfs else None
            
            if vacances_df is not None:
                vacances_df.to_parquet(holidays_path)
                logger.info(f"  ✅ Vacances générées: {holidays_path}")
            else:
                logger.warning(f"  ⚠️ Pas de données vacances générées")
                holidays_path = None
        except Exception as e:
            logger.error(f"  ❌ Erreur génération vacances: {e}")
            return {"status": "error", "step": "holidays", "error": str(e)}
    
    # 3. Préparer les features consommation
    logger.info("\n[3/4] Préparation des features consommation...")
    features_path = output_dir / f"consumption_features_{start_date}_to_{end_date}.parquet"
    
    try:
        preparer = ConsumptionDataPreparer()
        features_df = preparer.prepare(
            raw_path=raw_path,
            weather_path=str(weather_path),
            holidays_path=str(holidays_path) if holidays_path else None,
            output_path=str(features_path)
        )
        logger.info(f"  ✅ Features préparées: {features_path}")
        logger.info(f"  ℹ️ Shape: {features_df.shape}")
    except Exception as e:
        logger.error(f"  ❌ Erreur préparation features: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "step": "features", "error": str(e)}
    
    # 4. Upload sur S3
    s3_result = None
    if upload_to_s3:
        logger.info("\n[4/4] Upload sur S3...")
        try:
            s3_handler = S3Handler(bucket=s3_bucket)
            s3_key = f"{s3_prefix}consumption_features_{start_date}_to_{end_date}.parquet"
            s3_result = s3_handler.upload_file(
                local_path=str(features_path),
                s3_key=s3_key,
                metadata={
                    "start_date": start_date,
                    "end_date": end_date,
                    "source": "prepare_consumption_pipeline"
                }
            )
            
            if s3_result["status"] == "success":
                logger.info(f"  ✅ Upload S3 réussi: {s3_result['s3_uri']}")
            elif s3_result["status"] == "skipped":
                logger.info(f"  ℹ️ Upload S3 ignoré: {s3_result['reason']}")
            else:
                logger.warning(f"  ⚠️ Upload S3 échoué: {s3_result['reason']}")
        except Exception as e:
            logger.error(f"  ❌ Erreur upload S3: {e}")
            s3_result = {"status": "error", "error": str(e)}
    
    # Résultat final
    result = {
        "status": "success",
        "local_paths": {
            "weather": str(weather_path),
            "holidays": str(holidays_path) if holidays_path else None,
            "features": str(features_path)
        },
        "s3": s3_result,
        "dates": {
            "start": start_date,
            "end": end_date
        }
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE TERMINÉ AVEC SUCCÈS")
    logger.info("=" * 60)
    logger.info(f"\nFichier features local: {features_path}")
    if s3_result and s3_result.get("status") == "success":
        logger.info(f"Fichier features S3: {s3_result['s3_uri']}")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Pipeline pour préparer les features consommation et les stocker sur S3'
    )
    parser.add_argument('--start_date', type=str, required=True, help='Date de début (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, required=True, help='Date de fin (YYYY-MM-DD)')
    parser.add_argument('--raw_path', type=str, required=True, help='Chemin vers le fichier brut PRM')
    parser.add_argument('--output_dir', type=str, default='data/processed/', help='Répertoire de sortie local')
    parser.add_argument('--no_upload_s3', action='store_true', help='Désactiver l\'upload S3')
    parser.add_argument('--s3_bucket', type=str, help='Nom du bucket S3 (défaut: depuis env)')
    parser.add_argument('--s3_prefix', type=str, default='consumption/features/', help='Préfixe S3')
    
    args = parser.parse_args()
    
    try:
        result = prepare_consumption_features_pipeline(
            start_date=args.start_date,
            end_date=args.end_date,
            raw_path=args.raw_path,
            output_dir=args.output_dir,
            upload_to_s3=not args.no_upload_s3,
            s3_bucket=args.s3_bucket,
            s3_prefix=args.s3_prefix
        )
        
        if result["status"] == "success":
            logger.info("\n✅ Pipeline terminé avec succès")
            sys.exit(0)
        else:
            logger.error(f"\n❌ Pipeline échoué: {result.get('error')}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
