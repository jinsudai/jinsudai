"""
Script de réentraînement conditionnel quotidien.

Logique:
- Chaque jour, vérifie:
  1. Si un drift a été détecté (métriques stockées)
  2. Si le dernier réentraînement date de > 3 jours
- Si l'une des conditions est remplie, lance le réentraînement

Usage:
    python scripts/run_retraining.py --config consumption
    python scripts/run_retraining.py --config consumption --force
    python scripts/run_retraining.py --config consumption --dry-run
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.config import load_config
from ml.pipelines.drift_detection_pipeline import DriftDetectionPipeline
from ml.pipelines.training_pipeline import MLPipeline
from ml.pipelines.database_handler import DatabaseHandler
from ml.utils.s3_handler import S3Handler
import mlflow


def check_last_retraining_date(model_name: str, tracking_uri: str) -> Optional[datetime]:
    """
    Vérifie la date du dernier réentraînement via MLflow.

    Args:
        model_name: Nom du modèle dans MLflow
        tracking_uri: URI de tracking MLflow

    Returns:
        Date du dernier réentraînement ou None si pas trouvé
    """
    try:
        mlflow.set_tracking_uri(tracking_uri)
        client = mlflow.tracking.MlflowClient()

        # Chercher le modèle avec l'alias 'prod'
        try:
            model_version = client.get_model_version(model_name, "prod")
            last_run = client.get_run(model_version.run_id)
            last_retraining_date = datetime.fromtimestamp(last_run.info.start_time / 1000)
            return last_retraining_date
        except Exception:
            # Pas de modèle en prod, chercher la dernière run
            experiment = client.get_experiment_by_name(f"{model_name}_experiment")
            if experiment:
                runs = client.search_runs(
                    experiment_ids=[experiment.experiment_id],
                    max_results=1,
                    order_by=["start_time DESC"]
                )
                if runs:
                    last_run = runs[0]
                    last_retraining_date = datetime.fromtimestamp(last_run.info.start_time / 1000)
                    return last_retraining_date

        return None
    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification du dernier réentraînement: {e}")
        return None


def check_drift_detected(db_handler: DatabaseHandler, hours: int = 24) -> bool:
    """
    Vérifie si un drift a été détecté dans les dernières X heures.

    Args:
        db_handler: Instance de DatabaseHandler
        hours: Nombre d'heures à regarder en arrière

    Returns:
        True si drift détecté, False sinon
    """
    try:
        if not db_handler or not db_handler.verify_connection():
            print("⚠️ Base de données non disponible, vérification drift impossible")
            return False

        # Récupérer les métriques de drift récentes
        drift_metrics = db_handler.get_recent_drift_metrics(hours=hours)

        if drift_metrics and len(drift_metrics) > 0:
            # Vérifier si au moins un drift a été détecté
            for metric in drift_metrics:
                if metric.get('overall_drift_detected', False):
                    print(f"✅ Drift détecté le {metric.get('timestamp')}")
                    return True

        print("ℹ️ Aucun drift détecté récemment")
        return False
    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification du drift: {e}")
        return False


def prepare_retraining_data(
    db_handler: DatabaseHandler = None,
    limit: int = 10000,
    use_s3: bool = True,
    s3_bucket: str = None,
    s3_prefix: str = "consumption/trained/"
) -> Optional[str]:
    """
    Prépare les données de production pour le réentraînement.

    Priorité:
    1. Télécharge le fichier le plus récent depuis S3 (prefix /consumption/trained/)
    2. Fallback sur la base de données + preparation pipeline (comme entraînement initial)

    Args:
        db_handler: Instance de DatabaseHandler (optionnel, fallback)
        limit: Nombre maximum d'enregistrements (pour fallback DB)
        use_s3: Si True, essaie d'abord S3
        s3_bucket: Nom du bucket S3 (optionnel, utilise config par défaut)
        s3_prefix: Préfixe S3 pour les fichiers trained (défaut: consumption/trained/)

    Returns:
        Chemin vers le fichier de données préparé ou None
    """
    try:
        # 1. Essayer de télécharger depuis S3
        if use_s3:
            print("📥 Tentative de téléchargement depuis S3...")
            try:
                config = load_config('config.yaml')
                s3_config = config.get('s3', {})

                bucket = s3_bucket or s3_config.get('bucket', 'data-store')
                prefix = s3_prefix

                print(f"   Bucket S3: {bucket}")
                print(f"   Préfixe S3: {prefix}")

                s3_handler = S3Handler(bucket=bucket)

                if s3_handler.s3_enabled:
                    # Lister les fichiers dans le prefix consumption/trained/
                    files = s3_handler.list_files(prefix=prefix)

                    # Filtrer les fichiers train.parquet
                    train_files = [f for f in files if 'train' in f and f.endswith('.parquet')]

                    if train_files:
                        # Trouver le plus récent
                        train_files_sorted = sorted(train_files, reverse=True)
                        latest_file = train_files_sorted[0]

                        print(f"   📂 Fichier le plus récent trouvé: {latest_file}")

                        # Télécharger le fichier
                        data_dir = project_root / 'data' / 'processed'
                        data_dir.mkdir(parents=True, exist_ok=True)

                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        local_path = data_dir / f'retraining_data_{timestamp}.parquet'

                        result = s3_handler.download_file(
                            s3_key=latest_file,
                            local_path=str(local_path),
                            overwrite=True
                        )

                        if result["status"] == "success":
                            print(f"✅ Données de réentraînement téléchargées depuis S3")
                            print(f"   Source: {latest_file}")
                            print(f"   Destination: {local_path}")
                            print(f"   Taille: {local_path.stat().st_size / 1024 / 1024:.2f} MB")
                            return str(local_path)
                        else:
                            print(f"⚠️ Échec du téléchargement S3: {result.get('reason')}")
                    else:
                        print(f"⚠️ Aucun fichier train.parquet trouvé dans s3://{bucket}/{prefix}")
                else:
                    print("⚠️ S3 non disponible (credentials manquants)")
            except Exception as e:
                print(f"⚠️ Erreur lors du téléchargement S3: {e}")

        # 2. Fallback sur la base de données + preparation pipeline
        print("📊 Fallback sur la base de données + preparation pipeline...")
        if not db_handler or not db_handler.verify_connection():
            print("⚠️ Base de données non disponible")
            return None

        # Récupérer les données de production avec valeurs réelles
        production_data = db_handler.get_production_data_for_retraining(limit=limit)

        if production_data is None or len(production_data) == 0:
            print("⚠️ Pas de données de production disponibles pour le réentraînement")
            return None

        print(f"   📊 {len(production_data)} enregistrements récupérés depuis la base")

        # Utiliser le même preparation pipeline que l'entraînement initial
        try:
            from ml.consumption.consumption_preparer import ConsumptionDataPreparer
            from ml.connectors.weather.weather_api import WeatherAPI
            from ml.connectors.holidays.holidays_api import HolidaysCombinedAPI

            # Déterminer la plage de dates
            production_data['prediction_timestamp'] = pd.to_datetime(production_data['prediction_timestamp'])
            start_date = production_data['prediction_timestamp'].min().strftime('%Y-%m-%d')
            end_date = production_data['prediction_timestamp'].max().strftime('%Y-%m-%d')

            print(f"   📅 Plage de dates: {start_date} à {end_date}")

            # Créer les fichiers météo et vacances
            data_dir = project_root / 'data' / 'processed'
            data_dir.mkdir(parents=True, exist_ok=True)

            weather_path = data_dir / f"weather_{start_date}_to_{end_date}.parquet"
            holidays_path = data_dir / f"holidays_{start_date}_to_{end_date}.parquet"

            # Générer météo
            print("   🌤️  Génération des données météo...")
            weather_api = WeatherAPI(latitude=43.5297, longitude=5.4474, location_name="Aix en Provence")
            weather_df = weather_api.fetch_historical(start_date=start_date, end_date=end_date, hourly=True)
            if 'Horodate' not in weather_df.columns:
                weather_df['Horodate'] = pd.to_datetime(weather_df.index)
            weather_df.to_parquet(weather_path)
            print(f"   ✅ Météo générée: {weather_path}")

            # Générer vacances
            print("   🏖️  Génération des données vacances...")
            holidays_api = HolidaysCombinedAPI(zone="C")
            holidays_df = holidays_api.generate_holidays_dataframe(start_date, end_date)
            holidays_df.to_parquet(holidays_path)
            print(f"   ✅ Vacances générées: {holidays_path}")

            # Préparer les features avec ConsumptionDataPreparer
            print("   🔧 Préparation des features...")
            preparer = ConsumptionDataPreparer()

            # Créer un fichier raw temporaire avec les données de production
            raw_path = data_dir / f"raw_production_{timestamp}.parquet"
            production_data.rename(columns={'prediction': 'Valeur'}, inplace=True)
            production_data.rename(columns={'prediction_timestamp': 'Horodate'}, inplace=True)
            production_data.to_parquet(raw_path, index=False)

            # Préparer les features
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            train_path = data_dir / f'retraining_data_{timestamp}.parquet'

            features_df = preparer.prepare(
                raw_path=str(raw_path),
                weather_path=str(weather_path),
                holidays_path=str(holidays_path),
                output_path=str(train_path)
            )

            print(f"✅ Données de réentraînement préparées: {len(features_df)} enregistrements")
            print(f"   Sauvegardées dans: {train_path}")

            # Nettoyer les fichiers temporaires
            raw_path.unlink(missing_ok=True)

            return str(train_path)

        except Exception as e:
            print(f"❌ Erreur lors de la préparation des features: {e}")
            import traceback
            traceback.print_exc()
            return None

    except Exception as e:
        print(f"❌ Erreur lors de la préparation des données: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_retraining(
    config_name: str,
    data_path: str,
    force: bool = False
) -> bool:
    """
    Lance le réentraînement du modèle.

    Args:
        config_name: Nom de la configuration
        data_path: Chemin vers les données d'entraînement
        force: Force le réentraînement même sans amélioration

    Returns:
        True si succès, False sinon
    """
    try:
        # Charger la config spécifique à l'environnement
        import os
        environment = os.getenv('Environment', 'Dev').lower()
        config_name_to_use = f"{config_name}.{environment}"

        print(f"=== LANCEMENT DU RÉENTRAÎNEMENT ===")
        print(f"Config: {config_name_to_use}")
        print(f"Données: {data_path}")
        print()

        # Initialiser le pipeline
        pipeline = MLPipeline(config_name=config_name_to_use)

        # Exécuter le pipeline complet
        success = pipeline.run_full_pipeline(data_path=data_path)

        if success:
            print(f"\n✅ Réentraînement terminé avec succès")
            print(f"Métriques: {pipeline.metrics}")

            # Vérifier le résultat de la promotion
            if hasattr(pipeline, 'promotion_result') and pipeline.promotion_result:
                if pipeline.promotion_result['success']:
                    print(f"✅ Modèle promu en production")
                else:
                    print(f"ℹ️ Modèle non promu: {pipeline.promotion_result['reason']}")
        else:
            print(f"\n❌ Erreur lors du réentraînement")
            return False

        return success
    except Exception as e:
        print(f"❌ Erreur lors du réentraînement: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Script de réentraînement conditionnel quotidien')
    parser.add_argument('--config', type=str, default='consumption',
                        help='Nom de la configuration (consumption, solar_production)')
    parser.add_argument('--force', action='store_true',
                        help='Force le réentraînement sans vérifier les conditions')
    parser.add_argument('--dry-run', action='store_true',
                        help='Vérifie les conditions sans lancer le réentraînement')
    parser.add_argument('--max-days', type=int, default=3,
                        help='Nombre maximum de jours sans réentraînement (défaut: 3)')
    parser.add_argument('--drift-hours', type=int, default=24,
                        help='Nombre d\'heures à regarder pour le drift (défaut: 24)')
    parser.add_argument('--data-limit', type=int, default=10000,
                        help='Limite d\'enregistrements pour les données de réentraînement')

    args = parser.parse_args()

    print(f"=== SCRIPT DE RÉENTRAÎNEMENT CONDITIONNEL ===")
    print(f"Config: {args.config}")
    print(f"Force: {args.force}")
    print(f"Dry-run: {args.dry_run}")
    print(f"Max jours sans réentraînement: {args.max_days}")
    print(f"Drift heures: {args.drift_hours}")
    print()

    # Charger la configuration
    config = load_config(config_name=args.config)
    model_name = config.get('mlflow', {}).get('model_name', 'model')
    tracking_uri = config.get('mlflow', {}).get('tracking_uri')
    db_uri = config.get('database', {}).get('uri')

    # Initialiser le handler de base de données
    db_handler = None
    if db_uri:
        try:
            db_handler = DatabaseHandler(db_uri=db_uri)
            print(f"✅ Base de données connectée")
        except Exception as e:
            print(f"⚠️ Impossible de se connecter à la base de données: {e}")

    # Vérifier les conditions
    should_retrain = False
    retrain_reason = []

    # Condition 1: Force
    if args.force:
        should_retrain = True
        retrain_reason.append("Force manuel")

    # Condition 2: Drift détecté
    if not should_retrain and db_handler:
        drift_detected = check_drift_detected(db_handler, hours=args.drift_hours)
        if drift_detected:
            should_retrain = True
            retrain_reason.append("Drift détecté")

    # Condition 3: Dernier réentraînement > X jours
    if not should_retrain:
        last_retraining = check_last_retraining_date(model_name, tracking_uri)
        if last_retraining:
            days_since_retraining = (datetime.now() - last_retraining).days
            print(f"ℹ️ Dernier réentraînement: {last_retraining.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"ℹ️ Jours depuis le dernier réentraînement: {days_since_retraining}")

            if days_since_retraining > args.max_days:
                should_retrain = True
                retrain_reason.append(f"Dernier réentraînement > {args.max_days} jours ({days_since_retraining} jours)")
        else:
            print("ℹ️ Aucun réentraînement précédent trouvé")
            should_retrain = True
            retrain_reason.append("Premier réentraînement")

    # Décision
    print()
    print("=" * 60)
    if should_retrain:
        print(f"✅ RÉENTRAÎNEMENT REQUIS")
        print(f"Raison(s): {', '.join(retrain_reason)}")
        print("=" * 60)

        if args.dry_run:
            print("🔍 MODE DRY-RUN - Réentraînement non exécuté")
            sys.exit(0)

        # Préparer les données (priorité S3 /consumption/trained/)
        data_path = prepare_retraining_data(
            db_handler=db_handler,
            limit=args.data_limit,
            use_s3=True,
            s3_prefix="consumption/trained/"
        )
        if not data_path:
            print("❌ Impossible de préparer les données de réentraînement")
            sys.exit(1)

        # Lancer le réentraînement
        success = run_retraining(args.config, data_path, force=args.force)

        if success:
            print("\n✅ RÉENTRAÎNEMENT TERMINÉ AVEC SUCCÈS")
            sys.exit(0)
        else:
            print("\n❌ RÉENTRAÎNEMENT ÉCHOUÉ")
            sys.exit(1)
    else:
        print(f"ℹ️ PAS DE RÉENTRAÎNEMENT REQUIS")
        print(f"Conditions non remplies")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
