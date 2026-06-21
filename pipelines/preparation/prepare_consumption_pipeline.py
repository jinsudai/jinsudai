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
from datetime import datetime, timedelta
import pandas as pd

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.consumption.consumption_preparer import ConsumptionDataPreparer
from ml.connectors.weather.weather_api import WeatherAPI
from ml.connectors.holidays.holidays_api import HolidaysCombinedAPI
from ml.utils.s3_handler import S3Handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def combine_train_files_from_s3(
    end_date: str,
    window_years: int,
    s3_bucket: str,
    output_path: str
) -> dict:
    """
    Combine les fichiers train des X dernières années depuis S3.

    Args:
        end_date: Date de fin de la fenêtre (YYYY-MM-DD)
        window_years: Nombre d'années à inclure
        s3_bucket: Nom du bucket S3
        output_path: Chemin local de sortie pour le fichier combiné

    Returns:
        dict: Résultat avec status et chemins
    """
    try:
        logger.info(f"\n[COMBINAISON] Combinaison des fichiers train sur {window_years} ans")
        
        # Calculer la date de début de la fenêtre
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        start_date_obj = end_date_obj - timedelta(days=window_years * 365)
        
        logger.info(f"Fenêtre temporelle: {start_date_obj.strftime('%Y-%m-%d')} à {end_date}")
        
        # Initialiser le handler S3
        s3_handler = S3Handler(bucket=s3_bucket)
        
        if not s3_handler.s3_enabled:
            logger.warning("S3 non disponible, impossible de combiner les fichiers")
            return {
                "status": "error",
                "reason": "S3 not available"
            }
        
        # Lister tous les fichiers train dans consumption/
        files = s3_handler.list_files(prefix="consumption")
        train_files = [f for f in files if 'train' in f and f.endswith('.parquet')]
        
        if not train_files:
            logger.warning("Aucun fichier train trouvé sur S3")
            return {
                "status": "error",
                "reason": "No train files found on S3"
            }
        
        logger.info(f"{len(train_files)} fichiers train trouvés sur S3")
        
        # Télécharger et combiner les fichiers dans la fenêtre temporelle
        combined_dfs = []
        downloaded_files = []
        
        for s3_key in train_files:
            try:
                # Télécharger le fichier temporairement
                temp_path = Path(f"/tmp/{Path(s3_key).name}")
                result = s3_handler.download_file(
                    s3_key=s3_key,
                    local_path=str(temp_path),
                    overwrite=True
                )
                
                if result["status"] == "success":
                    df = pd.read_parquet(temp_path)
                    
                    # Vérifier si le fichier est dans la fenêtre temporelle
                    if 'Horodate' in df.columns:
                        df['Horodate'] = pd.to_datetime(df['Horodate'])
                        file_start = df['Horodate'].min()
                        file_end = df['Horodate'].max()
                        
                        # Vérifier si le fichier chevauche la fenêtre temporelle
                        if file_end >= start_date_obj and file_start <= end_date_obj:
                            combined_dfs.append(df)
                            downloaded_files.append(s3_key)
                            logger.info(f"  ✓ {s3_key} ({file_start.date()} à {file_end.date()})")
                        else:
                            logger.info(f"  ✗ {s3_key} (hors fenêtre temporelle)")
                    else:
                        logger.warning(f"  ⚠ {s3_key} (pas de colonne Horodate)")
                    
                    # Supprimer le fichier temporaire
                    temp_path.unlink()
                    
            except Exception as e:
                logger.warning(f"  ⚠ Erreur avec {s3_key}: {e}")
        
        if not combined_dfs:
            logger.warning("Aucun fichier dans la fenêtre temporelle")
            return {
                "status": "error",
                "reason": "No files in time window"
            }
        
        # Combiner les DataFrames
        combined_df = pd.concat(combined_dfs, ignore_index=True)
        
        # Supprimer les doublons basés sur Horodate
        if 'Horodate' in combined_df.columns:
            combined_df = combined_df.drop_duplicates(subset=['Horodate'], keep='last')
            combined_df = combined_df.sort_values('Horodate')
        
        # Sauvegarder le fichier combiné
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        combined_df.to_parquet(output_path_obj)
        
        logger.info(f"✅ Fichier combiné créé: {output_path}")
        logger.info(f"   Taille: {len(combined_df)} enregistrements")
        logger.info(f"   Période: {combined_df['Horodate'].min()} à {combined_df['Horodate'].max()}")
        
        return {
            "status": "success",
            "output_path": str(output_path),
            "record_count": len(combined_df),
            "source_files": downloaded_files
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la combinaison: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "reason": str(e)
        }


def prepare_consumption_features_pipeline(
    start_date: str,
    end_date: str,
    raw_path: str,
    output_dir: str = "data/processed/",
    upload_to_s3: bool = True,
    s3_bucket: str = None,
    s3_prefix: str = "consumption/features/",
    window_years: int = 3
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
        window_years: Nombre d'années de données à combiner pour le fichier train (défaut: 3)
        
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
    
    # Vérifier si le fichier existe et a la bonne structure
    weather_valid = False
    if weather_path.exists():
        try:
            existing_weather = pd.read_parquet(weather_path)
            if 'Horodate' in existing_weather.columns:
                weather_valid = True
                logger.info(f"  ℹ️ Fichier météo existe déjà avec colonne Horodate: {weather_path}")
            else:
                logger.warning(f"  ⚠️ Fichier météo existe mais sans colonne Horodate, régénération...")
        except Exception as e:
            logger.warning(f"  ⚠️ Erreur lecture fichier météo existant: {e}")
    
    if not weather_valid:
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
            # S'assurer que la colonne Horodate existe
            if 'Horodate' not in weather_df.columns:
                weather_df['Horodate'] = pd.to_datetime(weather_df.index)
            weather_df.to_parquet(weather_path)
            logger.info(f"  ✅ Météo générée: {weather_path}")
        except Exception as e:
            logger.error(f"  ❌ Erreur génération météo: {e}")
            return {"status": "error", "step": "weather", "error": str(e)}
    
    # 2. Générer les données vacances/jours fériés
    logger.info("\n[2/4] Génération des données vacances/jours fériés...")
    holidays_path = output_dir / f"holidays_{start_date}_to_{end_date}.parquet"
    
    # Vérifier si le fichier existe et a la bonne structure
    holidays_valid = False
    if holidays_path.exists():
        try:
            existing_holidays = pd.read_parquet(holidays_path)
            if 'Horodate' in existing_holidays.columns:
                holidays_valid = True
                logger.info(f"  ℹ️ Fichier vacances existe déjà avec colonne Horodate: {holidays_path}")
            else:
                logger.warning(f"  ⚠️ Fichier vacances existe mais sans colonne Horodate, régénération...")
        except Exception as e:
            logger.warning(f"  ⚠️ Erreur lecture fichier vacances existant: {e}")
    
    if not holidays_valid:
        try:
            holidays_api = HolidaysCombinedAPI(zone="C")
            holidays_df = holidays_api.generate_holidays_dataframe(start_date, end_date)
            holidays_df.to_parquet(holidays_path)
            logger.info(f"  ✅ Vacances générées: {holidays_path}")
        except Exception as e:
            logger.error(f"  ❌ Erreur génération vacances: {e}")
            return {"status": "error", "step": "holidays", "error": str(e)}
    
    # 3. Préparer les features consommation
    logger.info("\n[3/4] Préparation des features consommation...")
    train_path = output_dir / f"{start_date}_to_{end_date}_train.parquet"
    
    try:
        preparer = ConsumptionDataPreparer()
        features_df = preparer.prepare(
            raw_path=raw_path,
            weather_path=str(weather_path),
            holidays_path=str(holidays_path) if holidays_path else None,
            output_path=str(train_path)
        )
        logger.info(f"  ✅ Features préparées: {train_path}")
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
            
            # Upload du fichier weather avec le préfixe weather
            s3_key_weather = f"weather/{start_date}_to_{end_date}_weather.parquet"
            s3_result_weather = s3_handler.upload_file(
                local_path=str(weather_path),
                s3_key=s3_key_weather,
                metadata={
                    "start_date": start_date,
                    "end_date": end_date,
                    "source": "prepare_consumption_pipeline",
                    "type": "weather"
                }
            )
            
            # Upload du fichier train avec le préfixe consumption
            s3_key_train = f"consumption/{start_date}_to_{end_date}_train.parquet"
            s3_result_train = s3_handler.upload_file(
                local_path=str(train_path),
                s3_key=s3_key_train,
                metadata={
                    "start_date": start_date,
                    "end_date": end_date,
                    "source": "prepare_consumption_pipeline",
                    "type": "train"
                }
            )
            
            # Combiner les résultats
            s3_result = {
                "status": "success",
                "weather": s3_result_weather,
                "train": s3_result_train
            }
            
            if s3_result_weather["status"] == "success":
                logger.info(f"  ✅ Upload S3 weather réussi: {s3_result_weather['s3_uri']}")
            elif s3_result_weather["status"] == "skipped":
                logger.info(f"  ℹ️ Upload S3 weather ignoré: {s3_result_weather['reason']}")
            else:
                logger.warning(f"  ⚠️ Upload S3 weather échoué: {s3_result_weather['reason']}")
            
            if s3_result_train["status"] == "success":
                logger.info(f"  ✅ Upload S3 train réussi: {s3_result_train['s3_uri']}")
            elif s3_result_train["status"] == "skipped":
                logger.info(f"  ℹ️ Upload S3 train ignoré: {s3_result_train['reason']}")
            else:
                logger.warning(f"  ⚠️ Upload S3 train échoué: {s3_result_train['reason']}")
        except Exception as e:
            logger.error(f"  ❌ Erreur upload S3: {e}")
            s3_result = {"status": "error", "error": str(e)}
    
    # 5. Combinaison des fichiers train sur X années
    combined_result = None
    if upload_to_s3 and s3_bucket:
        logger.info(f"\n[5/5] Combinaison des fichiers train sur {window_years} ans...")
        try:
            # Calculer les dates de la fenêtre combinée
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            start_date_obj = end_date_obj - timedelta(days=window_years * 365)
            
            # Nom du fichier combiné
            combined_train_path = output_dir / f"{start_date_obj.strftime('%Y-%m-%d')}_to_{end_date}_train_combined.parquet"
            
            # Combiner les fichiers depuis S3
            combined_result = combine_train_files_from_s3(
                end_date=end_date,
                window_years=window_years,
                s3_bucket=s3_bucket,
                output_path=str(combined_train_path)
            )
            
            if combined_result["status"] == "success":
                logger.info(f"  ✅ Combinaison réussie: {combined_train_path}")
                
                # Upload du fichier combiné sur S3
                s3_handler = S3Handler(bucket=s3_bucket)
                s3_key_combined = f"consumption/{start_date_obj.strftime('%Y-%m-%d')}_to_{end_date}_train_combined.parquet"
                s3_result_combined = s3_handler.upload_file(
                    local_path=str(combined_train_path),
                    s3_key=s3_key_combined,
                    metadata={
                        "start_date": start_date_obj.strftime('%Y-%m-%d'),
                        "end_date": end_date,
                        "window_years": window_years,
                        "source": "prepare_consumption_pipeline",
                        "type": "train_combined"
                    }
                )
                
                if s3_result_combined["status"] == "success":
                    logger.info(f"  ✅ Upload S3 combiné réussi: {s3_result_combined['s3_uri']}")
                    combined_result["s3"] = s3_result_combined
                else:
                    logger.warning(f"  ⚠️ Upload S3 combiné échoué: {s3_result_combined.get('reason')}")
            else:
                logger.warning(f"  ⚠️ Combinaison échouée: {combined_result.get('reason')}")
                
        except Exception as e:
            logger.error(f"  ❌ Erreur lors de la combinaison: {e}")
            combined_result = {"status": "error", "error": str(e)}
    
    # Résultat final
    result = {
        "status": "success",
        "local_paths": {
            "weather": str(weather_path),
            "holidays": str(holidays_path) if holidays_path else None,
            "train": str(train_path),
            "train_combined": str(combined_train_path) if combined_result and combined_result.get("status") == "success" else None
        },
        "s3": s3_result,
        "combined": combined_result,
        "dates": {
            "start": start_date,
            "end": end_date
        }
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE TERMINÉ AVEC SUCCÈS")
    logger.info("=" * 60)
    logger.info(f"\nFichier train local: {train_path}")
    if combined_result and combined_result.get("status") == "success":
        logger.info(f"Fichier train combiné local: {combined_result['output_path']}")
    if s3_result and s3_result.get("status") == "success":
        if 'weather' in s3_result:
            logger.info(f"Fichier weather S3: {s3_result['weather'].get('s3_uri')}")
        if 'train' in s3_result:
            logger.info(f"Fichier train S3: {s3_result['train'].get('s3_uri')}")
    
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
