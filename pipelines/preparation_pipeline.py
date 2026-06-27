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
from ml.connectors.holidays.holidays_api import HolidaysCombinedAPI
from ml.utils.data.s3_handler import S3Handler
from ml.utils.data.database_handler import DatabaseHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def prepare_consumption_features_pipeline(
    start_date: str,
    end_date: str,
    raw_path: str = None,
    output_dir: str = "data/processed/",
    upload_to_s3: bool = True,
    s3_bucket: str = None,
    s3_prefix: str = "consumption/features/",
    db_uri: str = None,
    db_limit: int = None,
    use_database: bool = True
) -> dict:
    """
    Pipeline complet pour préparer les features consommation.
    
    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        raw_path: Chemin vers le fichier brut PRM (optionnel si db_uri ou use_database)
        output_dir: Répertoire de sortie local
        upload_to_s3: Si True, upload sur S3
        s3_bucket: Nom du bucket S3 (défaut: depuis env)
        s3_prefix: Préfixe S3 pour les fichiers
        db_uri: URI de connexion PostgreSQL pour charger les données depuis la base
                (prioritaire sur raw_path si fourni)
        db_limit: Nombre maximum d'enregistrements à récupérer depuis la base
        use_database: Si True, charge les données depuis la base de données en utilisant
                     la variable d'environnement PREDICTIONS_POSTGRES_URI (ou db_uri si fourni)
        
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
    holidays_path = output_dir / f"{start_date}_to_{end_date}_holidays.parquet"
    
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
    logger.info("\n[3/6] Préparation des features consommation...")
    train_path = output_dir / f"{start_date}_to_{end_date}_train.parquet"
    
    try:
        preparer = ConsumptionDataPreparer()
        features_df = preparer.prepare(
            raw_path=raw_path,
            weather_path=str(weather_path),
            holidays_path=str(holidays_path) if holidays_path else None,
            output_path=str(train_path),
            db_uri=db_uri,
            db_limit=db_limit,
            use_database=use_database
        )
        logger.info(f"  ✅ Features préparées: {train_path}")
        logger.info(f"  ℹ️ Shape: {features_df.shape}")
        logger.info(f"  ℹ️ Head: {features_df.head(5)}")
    except Exception as e:
        logger.error(f"  ❌ Erreur préparation features: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "step": "features", "error": str(e)}
    
    # 4. Concaténer avec les fichiers train existants sur S3 (si upload activé)
    if upload_to_s3:
        logger.info("\n[4/7] Concaténation avec les fichiers train existants sur S3...")
        try:
            import pandas as pd

            # Initialiser le handler S3
            s3_handler = S3Handler(bucket=s3_bucket)

            if s3_handler.s3_enabled:
                # Télécharger tous les fichiers train existants depuis le préfixe dédié
                concat_temp_dir = output_dir / "temp_concat"
                concat_temp_dir.mkdir(parents=True, exist_ok=True)

                files = s3_handler.list_files(prefix="consumption/prepared")
                train_files = [f for f in files if 'train' in f and f.endswith('.parquet')]

                if train_files:
                    logger.info(f"  {len(train_files)} fichiers train existants trouvés dans consumption/prepared")

                    # Télécharger tous les fichiers existants
                    downloaded_files = []
                    for s3_key in train_files:
                        filename = s3_key.split('/')[-1]
                        temp_file = concat_temp_dir / filename
                        result = s3_handler.download_file(s3_key=s3_key, local_path=str(temp_file), overwrite=True)
                        if result["status"] == "success":
                            downloaded_files.append(temp_file)

                    # Concaténer avec le nouveau dataframe
                    if downloaded_files:
                        logger.info(f"  Concaténation de {len(downloaded_files)} fichiers existants + nouveau dataframe...")
                        dfs = []
                        for file in downloaded_files:
                            df = pd.read_parquet(file)
                            logger.info(f"  Fichier {file.name}: {len(df)} enregistrements")
                            dfs.append(df)
                        logger.info(f"  Nouveau dataframe: {len(features_df)} enregistrements")

                        # Ajouter le nouveau dataframe
                        dfs.append(features_df)

                        concatenated_df = pd.concat(dfs, ignore_index=True)
                        logger.info(f"  DataFrame concaténé: {len(concatenated_df)} enregistrements")

                        # Remplacer features_df par le dataframe concaténé
                        features_df = concatenated_df

                        # Extraire les dates réelles du dataframe concaténé
                        if 'Horodate' in concatenated_df.columns:
                            # S'assurer que la colonne est au format datetime
                            if not pd.api.types.is_datetime64_any_dtype(concatenated_df['Horodate']):
                                concatenated_df['Horodate'] = pd.to_datetime(concatenated_df['Horodate'])

                            min_date = concatenated_df['Horodate'].min()
                            max_date = concatenated_df['Horodate'].max()
                            min_date_str = min_date.strftime('%Y-%m-%d')
                            max_date_str = max_date.strftime('%Y-%m-%d')
                            logger.info(f"  Dates du dataframe concaténé: {min_date_str} à {max_date_str}")

                            # Mettre à jour le nom du fichier avec les dates réelles
                            train_path = output_dir / f"{min_date_str}_to_{max_date_str}_train.parquet"
                            logger.info(f"  Nom du fichier mis à jour: {train_path}")
                        else:
                            logger.warning("  ⚠️ Colonne 'Horodate' non trouvée, conservation du nom original")

                        # Sauvegarder le fichier concaténé
                        features_df.to_parquet(train_path)
                        logger.info(f"  Fichier concaténé sauvegardé: {train_path}")

                        # Nettoyer les fichiers temporaires
                        for file in downloaded_files:
                            file.unlink()
                        concat_temp_dir.rmdir()
                else:
                    logger.info("  ℹ️ Aucun fichier train existant dans consumption/prepared, pas de concaténation")
            else:
                logger.info("  ℹ️ S3 non disponible, pas de concaténation")
        except Exception as e:
            logger.error(f"  ❌ Erreur concaténation: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # 5. Récupérer les données réelles depuis la base de données
    if db_uri or use_database:
        logger.info("\n[5/7] Récupération des données réelles depuis la base de données...")
        try:
            import pandas as pd
            from datetime import datetime, timedelta

            # Initialiser le handler de base de données
            if db_uri:
                db_handler = DatabaseHandler(db_uri)
            elif use_database:
                import os
                db_uri_env = os.environ.get('PREDICTIONS_POSTGRES_URI')
                if db_uri_env:
                    db_handler = DatabaseHandler(db_uri_env)
                else:
                    logger.warning("  ⚠️ Variable d'environnement PREDICTIONS_POSTGRES_URI non trouvée")
                    db_handler = None
                if db_handler and not db_handler.verify_connection():
                    logger.warning("  ⚠️ Impossible de se connecter à la base de données")
                    db_handler = None
            else:
                db_handler = None

            if db_handler:
                # Extraire la dernière horodate du dataframe
                if 'Horodate' in features_df.columns:
                    if not pd.api.types.is_datetime64_any_dtype(features_df['Horodate']):
                        features_df['Horodate'] = pd.to_datetime(features_df['Horodate'])

                    last_horodate = features_df['Horodate'].max()
                    logger.info(f"  Dernière horodate dans le dataframe: {last_horodate}")

                    # Calculer la date de début pour récupérer les données réelles
                    # On récupère les données depuis la dernière horodate + 30 min jusqu'à la veille
                    start_date = last_horodate + timedelta(minutes=30)
                    today = datetime.now().date()
                    yesterday = today - timedelta(days=1)
                    end_date = datetime.combine(yesterday, datetime.max.time())

                    logger.info(f"  Récupération des données réelles du {start_date} au {end_date}")

                    # Récupérer les prédictions avec les valeurs réelles
                    actuals_df = db_handler.get_predictions_by_date(
                        start_date=start_date,
                        end_date=end_date
                    )

                    if actuals_df is not None and len(actuals_df) > 0:
                        logger.info(f"  {len(actuals_df)} enregistrements avec valeurs réelles récupérés")

                        # Filtrer pour ne garder que les enregistrements avec des valeurs réelles
                        actuals_with_values = actuals_df[actuals_df['actual_value'].notna()]
                        logger.info(f"  {len(actuals_with_values)} enregistrements avec des valeurs réelles non nulles")

                        if len(actuals_with_values) > 0:
                            # Ajouter les données réelles au dataframe de features
                            # On fusionne sur Horodate
                            if 'target_timestamp' in actuals_with_values.columns:
                                actuals_with_values = actuals_with_values.rename(columns={'target_timestamp': 'Horodate'})

                            # S'assurer que Horodate est au même format
                            if not pd.api.types.is_datetime64_any_dtype(actuals_with_values['Horodate']):
                                actuals_with_values['Horodate'] = pd.to_datetime(actuals_with_values['Horodate'])

                            # Fusionner les dataframes
                            features_df = pd.merge(
                                features_df,
                                actuals_with_values[['Horodate', 'actual_value']],
                                on='Horodate',
                                how='left'
                            )

                            logger.info(f"  DataFrame après fusion: {features_df.shape}")
                            logger.info(f"  Colonnes: {features_df.columns.tolist()}")
                        else:
                            logger.warning("  ⚠️ Aucune valeur réelle non nulle trouvée")
                    else:
                        logger.warning("  ⚠️ Aucune donnée réelle trouvée dans la base")
                else:
                    logger.warning("  ⚠️ Colonne 'Horodate' non trouvée dans le dataframe")
            else:
                logger.info("  ℹ️ Base de données non disponible, pas de récupération de données réelles")
        except Exception as e:
            logger.error(f"  ❌ Erreur récupération données réelles: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # 6. Archiver les anciens fichiers sur S3
    if upload_to_s3:
        logger.info("\n[6/7] Archivage des anciens fichiers sur S3...")
        try:
            s3_handler = S3Handler(bucket=s3_bucket)

            if s3_handler.s3_enabled:
                # Lister les fichiers existants dans consumption/prepared
                files = s3_handler.list_files(prefix="consumption/prepared")
                # Filtrer pour exclure le dossier archived
                old_files = [f for f in files if not f.startswith("consumption/archived/")]

                if old_files:
                    logger.info(f"  {len(old_files)} fichiers à archiver dans consumption/prepared")

                    # Déplacer chaque fichier vers consumption/archived/prepared/
                    for s3_key in old_files:
                        filename = s3_key.split('/')[-1]
                        archived_key = f"consumption/archived/prepared/{filename}"

                        # Copier vers archived
                        copy_result = s3_handler.copy_file(s3_key, archived_key)
                        if copy_result["status"] == "success":
                            logger.info(f"  ✅ Archivé: {s3_key} -> {archived_key}")
                            # Supprimer l'original
                            delete_result = s3_handler.delete_file(s3_key)
                            if delete_result["status"] != "success":
                                logger.warning(f"  ⚠️ Échec suppression original: {s3_key}")
                        else:
                            logger.warning(f"  ⚠️ Échec archivage: {s3_key}")
                else:
                    logger.info("  ℹ️ Aucun fichier à archiver")
            else:
                logger.info("  ℹ️ S3 non disponible, pas d'archivage")
        except Exception as e:
            logger.error(f"  ❌ Erreur archivage: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # 7. Upload sur S3
    s3_result = None
    if upload_to_s3:
        logger.info("\n[7/7] Upload sur S3...")
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
            
            # Upload du fichier train avec le préfixe consumption/prepared
            # Utiliser le nom de fichier réel (mis à jour avec les dates réelles après concaténation)
            train_filename = train_path.name
            s3_key_train = f"consumption/prepared/{train_filename}"
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
    
    # Résultat final
    result = {
        "status": "success",
        "local_paths": {
            "weather": str(weather_path),
            "holidays": str(holidays_path) if holidays_path else None,
            "train": str(train_path)
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
    logger.info(f"\nFichier train local: {train_path}")
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
    parser.add_argument('--raw_path', type=str, required=False, help='Chemin vers le fichier brut PRM (optionnel si --db_uri ou --use_database)')
    parser.add_argument('--output_dir', type=str, default='data/processed/', help='Répertoire de sortie local')
    parser.add_argument('--no_upload_s3', action='store_true', help='Désactiver l\'upload S3')
    parser.add_argument('--s3_bucket', type=str, help='Nom du bucket S3 (défaut: depuis env)')
    parser.add_argument('--s3_prefix', type=str, default='consumption/features/', help='Préfixe S3')
    parser.add_argument('--db_uri', type=str, help='URI de connexion PostgreSQL pour charger les données depuis la base')
    parser.add_argument('--db_limit', type=int, help='Nombre maximum d\'enregistrements à récupérer depuis la base')
    parser.add_argument('--use_database', action='store_true', help='Utiliser la base de données (lit PREDICTIONS_POSTGRES_URI depuis l\'environnement)')
    
    args = parser.parse_args()
    
    # Vérifier que soit raw_path soit db_uri soit use_database est fourni
    if not args.raw_path and not args.db_uri and not args.use_database:
        parser.error("Au moins l'un des arguments --raw_path, --db_uri ou --use_database doit être fourni")

    try:
        result = prepare_consumption_features_pipeline(
            start_date=args.start_date,
            end_date=args.end_date,
            raw_path=args.raw_path,
            output_dir=args.output_dir,
            upload_to_s3=not args.no_upload_s3,
            s3_bucket=args.s3_bucket,
            s3_prefix=args.s3_prefix,
            db_uri=args.db_uri,
            db_limit=args.db_limit,
            use_database=args.use_database
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
