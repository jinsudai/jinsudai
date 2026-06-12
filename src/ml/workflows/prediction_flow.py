"""
Flow Prefect complet pour le pipeline de prédiction.

Ce flow orchestre toutes les étapes :
1. Configuration du pipeline (MLflow + Base de données)
2. Chargement du modèle en production
3. Génération des données d'inférence
4. Préparation des features
5. Exécution des prédictions
6. Stockage des prédictions en base de données
7. Vérification des résultats

Exemple d'utilisation :
    from ml.workflows.prediction_flow import prediction_full_pipeline
    
    # Exécuter le pipeline complet
    result = prediction_full_pipeline(
        model_name="consumption_model",
        n_days=3
    )
"""

from prefect import flow
from typing import Dict, Any, Optional
import logging

# Importer les tâches de prédiction
from ml.workflows.prediction_tasks import (
    setup_prediction_task,
    load_model_task,
    generate_inference_data_task,
    set_inference_data_task,
    prepare_features_task,
    run_predictions_task,
    store_predictions_task,
    verify_results_task
)

# Importer les utilitaires
from ml.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@flow(
    name="prediction-full-pipeline",
    description="Pipeline complet de prédiction : configuration → modèle → données → prédictions → stockage",
    retries=1,
    retry_delay_seconds=60
)
def prediction_full_pipeline(
    model_name: str,
    mlflow_uri: Optional[str] = None,
    experiment_name: Optional[str] = None,
    db_uri: Optional[str] = None,
    n_days: int = 3,
    n_samples_per_day: int = 48,
    feature_columns: Optional[list] = None,
    alias_prod: str = "prod",
    use_existing_data: bool = False,
    df_inference_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Pipeline complet pour la prédiction.
    
    Étapes :
    1. Configuration du pipeline (MLflow + Base de données)
    2. Chargement du modèle en production
    3. Génération ou chargement des données d'inférence
    4. Préparation des features
    5. Exécution des prédictions
    6. Stockage des prédictions en base de données
    7. Vérification des résultats
    
    Args:
        model_name: Nom du modèle dans MLflow
        mlflow_uri: URI du serveur MLflow (optionnel, utilise la config par défaut)
        experiment_name: Nom de l'expérience MLflow (optionnel, utilise la config par défaut)
        db_uri: URI de connexion PostgreSQL (optionnel, utilise la config par défaut)
        n_days: Nombre de jours de prédictions (défaut: 3)
        n_samples_per_day: Nombre d'échantillons par jour (défaut: 48 pour 30min)
        feature_columns: Liste des colonnes features (optionnel)
        alias_prod: Alias pour la production (défaut: "prod")
        use_existing_data: Si True, charge des données existantes au lieu de générer
        df_inference_path: Chemin vers les données existantes (si use_existing_data=True)
    
    Returns:
        dict: Résultats complets du pipeline
    """
    # 0. Charger la config pour les valeurs par défaut
    config = load_config(config_name="consumption")
    
    if mlflow_uri is None:
        mlflow_uri = config.get('mlflow', {}).get('tracking_uri', 'http://localhost:5000')
    
    if experiment_name is None:
        experiment_name = config.get('mlflow', {}).get('experiment_name', 'consumption_experiment')
    
    if db_uri is None:
        db_uri = config.get('database', {}).get('uri')
    
    logger.info("####################################################")
    logger.info("### PIPELINE COMPLET DE PRÉDICTION ###")
    logger.info(f"### Modèle: {model_name} ###")
    logger.info(f"### Alias: {alias_prod} ###")
    logger.info("####################################################\n")
    
    # 1. ===== CONFIGURATION =====
    logger.info("=== ÉTAPE 1: Configuration du pipeline ===")
    
    pipeline = setup_prediction_task(
        mlflow_uri=mlflow_uri,
        experiment_name=experiment_name,
        db_uri=db_uri
    )
    
    # 2. ===== CHARGEMENT DU MODÈLE =====
    logger.info("\n=== ÉTAPE 2: Chargement du modèle ===")
    
    model_info = load_model_task(
        pipeline=pipeline,
        model_name=model_name,
        alias_prod=alias_prod
    )
    
    # 3. ===== DONNÉES D'INFÉRENCE =====
    logger.info("\n=== ÉTAPE 3: Données d'inférence ===")
    
    if use_existing_data and df_inference_path:
        logger.info(f"Chargement des données existantes: {df_inference_path}")
        data_info = set_inference_data_task(
            pipeline=pipeline,
            df_inference_path=df_inference_path
        )
    else:
        logger.info(f"Génération des données: {n_days} jours, {n_samples_per_day} échantillons/jour")
        data_info = generate_inference_data_task(
            pipeline=pipeline,
            n_days=n_days,
            n_samples_per_day=n_samples_per_day,
            feature_columns=feature_columns
        )
    
    # 4. ===== PRÉPARATION DES FEATURES =====
    logger.info("\n=== ÉTAPE 4: Préparation des features ===")
    
    features_info = prepare_features_task(pipeline=pipeline)
    
    # 5. ===== PRÉDICTIONS =====
    logger.info("\n=== ÉTAPE 5: Exécution des prédictions ===")
    
    predictions_info = run_predictions_task(
        pipeline=pipeline,
        feature_columns=feature_columns
    )
    
    # 6. ===== STOCKAGE =====
    logger.info("\n=== ÉTAPE 6: Stockage des prédictions ===")
    
    if db_uri:
        storage_info = store_predictions_task(pipeline=pipeline)
    else:
        logger.warning("Aucune URI de base de données fournie, stockage ignoré")
        storage_info = {"status": "skipped", "reason": "no_db_uri"}
    
    # 7. ===== VÉRIFICATION =====
    logger.info("\n=== ÉTAPE 7: Vérification des résultats ===")
    
    if db_uri:
        verification_info = verify_results_task(pipeline=pipeline)
    else:
        logger.warning("Vérification ignorée (pas de base de données)")
        verification_info = {"status": "skipped", "reason": "no_db_uri"}
    
    # 8. ===== RÉSULTAT FINAL =====
    logger.info("\n" + "="*60)
    logger.info("PIPELINE DE PRÉDICTION TERMINÉ AVEC SUCCÈS")
    logger.info("="*60)
    
    return {
        "status": "success",
        "model": model_info,
        "data": data_info,
        "features": features_info,
        "predictions": predictions_info,
        "storage": storage_info,
        "verification": verification_info
    }


@flow(
    name="prediction-inference-only",
    description="Pipeline d'inférence seulement : modèle + données → prédictions"
)
def prediction_inference_only_pipeline(
    model_name: str,
    df_inference_path: str,
    mlflow_uri: Optional[str] = None,
    experiment_name: Optional[str] = None,
    feature_columns: Optional[list] = None,
    alias_prod: str = "prod"
) -> Dict[str, Any]:
    """
    Pipeline pour l'inférence seulement (sans stockage en base de données).
    
    Utile pour des tests rapides ou des prédictions ponctuelles.
    
    Args:
        model_name: Nom du modèle dans MLflow
        df_inference_path: Chemin vers le fichier de données (CSV ou Parquet)
        mlflow_uri: URI du serveur MLflow (optionnel)
        experiment_name: Nom de l'expérience MLflow (optionnel)
        feature_columns: Liste des colonnes features (optionnel)
        alias_prod: Alias pour la production (défaut: "prod")
    
    Returns:
        dict: Résultats de l'inférence
    """
    # Charger la config pour les valeurs par défaut
    config = load_config(config_name="consumption")
    
    if mlflow_uri is None:
        mlflow_uri = config.get('mlflow', {}).get('tracking_uri', 'http://localhost:5000')
    
    if experiment_name is None:
        experiment_name = config.get('mlflow', {}).get('experiment_name', 'consumption_experiment')
    
    logger.info("=== Pipeline d'inférence seulement ===")
    
    # Configuration (sans base de données)
    pipeline = setup_prediction_task(
        mlflow_uri=mlflow_uri,
        experiment_name=experiment_name,
        db_uri=None
    )
    
    # Chargement du modèle
    model_info = load_model_task(
        pipeline=pipeline,
        model_name=model_name,
        alias_prod=alias_prod
    )
    
    # Chargement des données
    data_info = set_inference_data_task(
        pipeline=pipeline,
        df_inference_path=df_inference_path
    )
    
    # Préparation des features
    features_info = prepare_features_task(pipeline=pipeline)
    
    # Prédictions
    predictions_info = run_predictions_task(
        pipeline=pipeline,
        feature_columns=feature_columns
    )
    
    # Récupérer le DataFrame des prédictions
    df_predictions = pipeline.get_predictions_df()
    
    logger.info("=== Inférence terminée ===")
    
    return {
        "status": "success",
        "model": model_info,
        "data": data_info,
        "features": features_info,
        "predictions": predictions_info,
        "predictions_df": df_predictions
    }


@flow(
    name="prediction-batch",
    description="Pipeline de prédiction par batch pour plusieurs périodes"
)
def prediction_batch_pipeline(
    model_name: str,
    start_date: str,
    end_date: str,
    mlflow_uri: Optional[str] = None,
    experiment_name: Optional[str] = None,
    db_uri: Optional[str] = None,
    feature_columns: Optional[list] = None,
    alias_prod: str = "prod",
    batch_size_days: int = 7
) -> Dict[str, Any]:
    """
    Pipeline de prédiction par batch pour plusieurs périodes.
    
    Utile pour générer des prédictions sur une longue période
    en découpant en batches plus petits.
    
    Args:
        model_name: Nom du modèle dans MLflow
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        mlflow_uri: URI du serveur MLflow (optionnel)
        experiment_name: Nom de l'expérience MLflow (optionnel)
        db_uri: URI de connexion PostgreSQL (optionnel)
        feature_columns: Liste des colonnes features (optionnel)
        alias_prod: Alias pour la production (défaut: "prod")
        batch_size_days: Nombre de jours par batch (défaut: 7)
    
    Returns:
        dict: Résultats de tous les batches
    """
    from datetime import datetime, timedelta
    
    # Charger la config pour les valeurs par défaut
    config = load_config(config_name="consumption")
    
    if mlflow_uri is None:
        mlflow_uri = config.get('mlflow', {}).get('tracking_uri', 'http://localhost:5000')
    
    if experiment_name is None:
        experiment_name = config.get('mlflow', {}).get('experiment_name', 'consumption_experiment')
    
    if db_uri is None:
        db_uri = config.get('database', {}).get('uri')
    
    logger.info(f"=== Pipeline batch du {start_date} au {end_date} ===")
    
    # Calculer le nombre de batches
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = (end_dt - start_dt).days + 1
    n_batches = (total_days + batch_size_days - 1) // batch_size_days
    
    logger.info(f"Total jours: {total_days}, Batches: {n_batches}")
    
    # Configuration unique pour tous les batches
    pipeline = setup_prediction_task(
        mlflow_uri=mlflow_uri,
        experiment_name=experiment_name,
        db_uri=db_uri
    )
    
    # Chargement du modèle unique
    model_info = load_model_task(
        pipeline=pipeline,
        model_name=model_name,
        alias_prod=alias_prod
    )
    
    # Exécuter chaque batch
    batch_results = []
    current_start = start_dt
    
    for i in range(n_batches):
        current_end = min(current_start + timedelta(days=batch_size_days - 1), end_dt)
        batch_days = (current_end - current_start).days + 1
        
        logger.info(f"\n--- Batch {i+1}/{n_batches}: {current_start.date()} au {current_end.date()} ({batch_days} jours) ---")
        
        # Générer les données pour ce batch
        generate_inference_data_task(
            pipeline=pipeline,
            n_days=batch_days,
            n_samples_per_day=48,
            feature_columns=feature_columns
        )
        
        # Préparer les features
        prepare_features_task(pipeline=pipeline)
        
        # Exécuter les prédictions
        run_predictions_task(
            pipeline=pipeline,
            feature_columns=feature_columns
        )
        
        # Stocker si base de données disponible
        if db_uri:
            store_predictions_task(pipeline=pipeline)
        
        batch_results.append({
            "batch_number": i + 1,
            "start_date": current_start.strftime("%Y-%m-%d"),
            "end_date": current_end.strftime("%Y-%m-%d"),
            "n_days": batch_days
        })
        
        # Passer au batch suivant
        current_start = current_end + timedelta(days=1)
    
    # Vérification finale
    if db_uri:
        verification_info = verify_results_task(pipeline=pipeline)
    else:
        verification_info = {"status": "skipped"}
    
    logger.info(f"\n=== Pipeline batch terminé: {len(batch_results)} batches exécutés ===")
    
    return {
        "status": "success",
        "model": model_info,
        "n_batches": n_batches,
        "batch_results": batch_results,
        "verification": verification_info
    }
