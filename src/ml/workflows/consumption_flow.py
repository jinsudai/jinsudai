"""
Flow Prefect complet pour le pipeline de consommation électrique.

Ce flow orchestrer toutes les étapes :
1. Génération des données météo
2. Génération des données vacances/jours fériés
3. Préparation des features consommation
4. Entraînement du modèle
5. Évaluation du modèle
6. Monitoring (drift + performance)
7. Staging (Model Registry)

Exemple d'utilisation :
    from analytics.workflows.consumption_flow import consumption_full_pipeline
    
    # Exécuter le pipeline complet
    result = consumption_full_pipeline(
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
"""

from prefect import flow, task
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Importer les tâches domaine
from ml.consumption.consumption_tasks import prepare_consumption_features_task
from ml.consumption.training_tasks import (
    train_consumption_model_task,
    evaluate_consumption_model_task,
    monitor_consumption_model_task,
    stage_and_log_consumption_model_task
)

# Importer les tâches API
from ml.connectors.weather.weather_tasks import generate_weather_parquet_task
from ml.connectors.holidays.holidays_tasks import generate_holidays_parquet_task

# Importer les utilitaires
from ml.config import load_config
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@flow(
    name="consumption-full-pipeline",
    description="Pipeline complet : données brutes → modèle en production",
    retries=1,
    retry_delay_seconds=60
)
def consumption_full_pipeline(
    start_date: str = "2024-01-01",
    end_date: str = "2024-01-31",
    raw_path: str = "data/templates/raw_template.csv",
    output_dir: str = "data/processed/"
) -> Dict[str, Any]:
    """
    Pipeline complet pour la consommation électrique.
    
    Étapes :
    1. Génération données météo (parallèle)
    2. Génération données vacances/jours fériés (parallèle)
    3. Préparation des features consommation
    4. Entraînement du modèle
    5. Évaluation du modèle
    6. Monitoring (drift + performance)
    7. Staging (Model Registry)
    
    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        raw_path: Chemin vers le fichier brut PRM
        output_dir: Répertoire de sortie
    
    Returns:
        dict: Résultats complets du pipeline
    """
    # 0. Charger la config
    config = load_config(config_name="consumption")
    
    # 1. ===== GÉNÉRATION DES DONNÉES =====
    logger.info("=== ÉTAPE 1: Génération des données ===")
    
    # 1a. Générer données météo (tâche parallélisable)
    weather_path = Path(output_dir) / f"weather_{start_date}_to_{end_date}.parquet"
    weather_future = generate_weather_parquet_task(
        start_date=start_date,
        end_date=end_date,
        output_path=str(weather_path),
        latitude=43.5283,  # Aix en Provence 
        longitude=5.4497,
        location_name="Aix en Provence"
    )
    logger.info(f"📡 Génération météo démarrée: {weather_path}")
    
    # 1b. Générer données vacances/jours fériés (tâche parallélisable)
    holidays_path = Path(output_dir) / f"holidays_{start_date}_to_{end_date}.parquet"
    holidays_future = generate_holidays_parquet_task(
        start_date=start_date,
        end_date=end_date,
        output_path=str(holidays_path),
        zone="B"  # Zone A, B ou C selon les régions -> Aix en Provence est en zone B
    )
    logger.info(f"📅 Génération vacances démarrée: {holidays_path}")
    
    # 2. ===== PRÉPARATION DES FEATURES =====
    logger.info("\n=== ÉTAPE 2: Préparation des features ===")
    
    # Attendre que les données soient prêtes
    weather_path_resolved = weather_future.wait()
    holidays_path_resolved = holidays_future.wait()
    
    # Préparer les features consommation
    features_path = Path(output_dir) / f"consumption_features_{start_date}_to_{end_date}.parquet"
    features_future = prepare_consumption_features_task(
        raw_path=raw_path,
        weather_path=weather_path_resolved,
        holidays_path=holidays_path_resolved,
        output_path=str(features_path)
    )
    logger.info(f"🔧 Préparation des features: {features_path}")
    
    # 3. ===== ENTRAÎNEMENT =====
    logger.info("\n=== ÉTAPE 3: Entraînement du modèle ===")
    
    # Entraîner le modèle
    train_result_future = train_consumption_model_task(
        features_path=str(features_path),
        config_path="src/configs/consumption.yaml"
    )
    train_result = train_result_future.wait()
    logger.info(f"🤖 Modèle entraîné: {train_result['data_stats']}")
    
    # 4. ===== ÉVALUATION =====
    logger.info("\n=== ÉTAPE 4: Évaluation du modèle ===")
    
    # Charger les données pour évaluation
    features_df = pd.read_parquet(features_path)
    target_column = config.get('data', {}).get('target_column', 'Valeur')
    
    from ml.utils.data.data_preparation import split_data
    _, X_test, _, y_test = split_data(
        features_df,
        test_size=0.2,
        random_state=42,
        target_column=target_column
    )
    
    # Évaluer le modèle
    eval_result_future = evaluate_consumption_model_task(
        model=train_result["model"],
        X_test=X_test,
        y_test=y_test,
        feature_names=list(X_test.columns)
    )
    eval_result = eval_result_future.wait()
    logger.info(f"📊 Métriques: {eval_result['metrics']}")
    
    # 5. ===== MONITORING =====
    logger.info("\n=== ÉTAPE 5: Monitoring du modèle ===")
    
    # Charger les données pour monitoring
    X_train_full = features_df.drop(columns=[target_column, 'Horodate'])
    y_train_full = features_df[target_column]
    
    monitor_result_future = monitor_consumption_model_task(
        model=train_result["model"],
        X_train=X_train_full,
        X_test=X_test,
        y_train=y_train_full,
        y_test=y_test,
        feature_names=list(X_test.columns),
        problem_type="regression"
    )
    monitor_result = monitor_result_future.wait()
    logger.info(f"📈 Monitoring: {monitor_result['summary']}")
    
    # 6. ===== STAGING =====
    logger.info("\n=== ÉTAPE 6: Staging (Model Registry) ===")
    
    # Enregistrer dans Model Registry et gérer les stages
    staging_result_future = stage_and_log_consumption_model_task(
        model=train_result["model"],
        run_id=None,  # Utilise la dernière run
        config_path="src/configs/consumption.yaml",
        metric_keys=["mae", "rmse", "r2"],
        min_improvement=1.0  # 1% d'amélioration minimum
    )
    staging_result = staging_result_future.wait()
    logger.info(f"🚀 Modèle en production: {staging_result['model_uri']}")
    
    # 7. ===== RÉSULTAT FINAL =====
    logger.info("\n" + "="*60)
    logger.info("PIPELINE CONSOMMATION TERMINÉ AVEC SUCCÈS")
    logger.info("="*60)
    
    return {
        "status": "success",
        "data": {
            "weather_path": str(weather_path),
            "holidays_path": str(holidays_path),
            "features_path": str(features_path)
        },
        "training": train_result,
        "evaluation": eval_result,
        "monitoring": monitor_result,
        "staging": staging_result
    }


@flow(
    name="consumption-data-pipeline",
    description="Pipeline données seulement : météo + vacances → features"
)
def consumption_data_pipeline(
    start_date: str = "2024-01-01",
    end_date: str = "2024-01-31",
    raw_path: str = "data/templates/raw_template.csv",
    output_dir: str = "data/processed/"
) -> Dict[str, Any]:
    """
    Pipeline pour la préparation des données seulement.
    
    Utile pour générer les features sans entraîner le modèle.
    """
    # 1. Générer données météo et vacances (parallèle)
    weather_path = Path(output_dir) / f"weather_{start_date}_to_{end_date}.parquet"
    holidays_path = Path(output_dir) / f"holidays_{start_date}_to_{end_date}.parquet"
    
    weather_future = generate_weather_parquet_task(
        start_date=start_date,
        end_date=end_date,
        output_path=str(weather_path)
    )
    
    holidays_future = generate_holidays_parquet_task(
        start_date=start_date,
        end_date=end_date,
        output_path=str(holidays_path)
    )
    
    # 2. Préparer les features
    features_path = Path(output_dir) / f"consumption_features_{start_date}_to_{end_date}.parquet"
    
    prepare_consumption_features_task(
        raw_path=raw_path,
        weather_path=weather_future.wait(),
        holidays_path=holidays_future.wait(),
        output_path=str(features_path)
    )
    
    return {
        "status": "success",
        "weather_path": str(weather_path),
        "holidays_path": str(holidays_path),
        "features_path": str(features_path)
    }


@flow(
    name="consumption-training-only",
    description="Pipeline entraînement seulement : features → modèle"
)
def consumption_training_only_pipeline(
    features_path: str,
    config_path: str = "src/configs/consumption.yaml"
) -> Dict[str, Any]:
    """
    Pipeline pour l'entraînement seulement.
    
    Utile lorsque les features sont déjà générées.
    """
    # 1. Entraîner
    train_result = train_consumption_model_task(
        features_path=features_path,
        config_path=config_path
    )
    
    # 2. Évaluer
    features_df = pd.read_parquet(features_path)
    target_column = load_config(config_path).get('data', {}).get('target_column', 'Valeur')
    
    from ml.utils.data.data_preparation import split_data
    _, X_test, _, y_test = split_data(
        features_df,
        test_size=0.2,
        random_state=42,
        target_column=target_column
    )
    
    eval_result = evaluate_consumption_model_task(
        model=train_result["model"],
        X_test=X_test,
        y_test=y_test,
        feature_names=list(X_test.columns)
    )
    
    # 3. Staging
    staging_result = stage_and_log_consumption_model_task(
        model=train_result["model"],
        config_path=config_path
    )
    
    return {
        "status": "success",
        "training": train_result,
        "evaluation": eval_result,
        "staging": staging_result
    }
