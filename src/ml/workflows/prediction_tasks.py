"""
Tâches Prefect pour le pipeline de prédiction.

Ce module contient les tâches Prefect qui encapsulent les étapes
du pipeline de prédiction : chargement modèle, génération données,
inférence, stockage.

Exemple d'utilisation :
    from ml.workflows.prediction_tasks import setup_prediction_task, load_model_task
    
    # Dans un flow Prefect
    pipeline = setup_prediction_task(mlflow_uri, experiment_name, db_uri)
    load_model_task(pipeline, model_name, alias_prod)
"""

from prefect import task
from typing import Dict, Any, Optional
import logging

from ml.utils.pipelines.Prediction_pipeline import PredictionPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@task(
    name="setup_prediction",
    description="Configure le pipeline de prédiction (MLflow + Base de données)",
    retries=2,
    retry_delay_seconds=30
)
def setup_prediction_task(
    mlflow_uri: str,
    experiment_name: str,
    db_uri: Optional[str] = None
) -> PredictionPipeline:
    """
    Tâche Prefect : Initialise et configure le pipeline de prédiction.
    
    Cette tâche :
    1. Crée une instance de PredictionPipeline
    2. Configure MLflow
    3. Configure la base de données si l'URI est fournie
    4. Vérifie les connexions
    
    Args:
        mlflow_uri: URI du serveur MLflow
        experiment_name: Nom de l'expérience MLflow
        db_uri: URI de connexion PostgreSQL (optionnel)
    
    Returns:
        PredictionPipeline: Instance du pipeline configuré
        
    Raises:
        Exception: Si la configuration échoue
    """
    pipeline = PredictionPipeline(mlflow_uri, experiment_name, db_uri)
    
    if not pipeline.setup():
        raise Exception("Échec de la configuration du pipeline de prédiction")
    
    logger.info("✅ Pipeline de prédiction configuré avec succès")
    return pipeline


@task(
    name="load_model",
    description="Charge le modèle en production depuis MLflow via alias",
    retries=2,
    retry_delay_seconds=30
)
def load_model_task(
    pipeline: PredictionPipeline,
    model_name: str,
    alias_prod: str = "prod"
) -> Dict[str, Any]:
    """
    Tâche Prefect : Charge le modèle de production depuis MLflow.
    
    Cette tâche :
    1. Charge le modèle via l'alias spécifié (défaut: "prod")
    2. Récupère les informations du modèle
    
    Args:
        pipeline: Instance de PredictionPipeline configurée
        model_name: Nom du modèle dans MLflow
        alias_prod: Alias pour la production (défaut: "prod")
    
    Returns:
        dict: Informations du modèle chargé
        
    Raises:
        Exception: Si le chargement échoue
    """
    if not pipeline.load_model(model_name, alias_prod=alias_prod):
        raise Exception(f"Échec du chargement du modèle {model_name}")
    
    model_info = pipeline.get_model_info()
    logger.info(f"✅ Modèle chargé: {model_info}")
    
    return model_info


@task(
    name="generate_inference_data",
    description="Génère les données d'inférence pour la prédiction",
    retries=2,
    retry_delay_seconds=30
)
def generate_inference_data_task(
    pipeline: PredictionPipeline,
    n_days: int = 3,
    n_samples_per_day: int = 48,
    feature_columns: Optional[list] = None
) -> Dict[str, Any]:
    """
    Tâche Prefect : Génère les données d'inférence.
    
    Cette tâche :
    1. Génère les données d'inférence avec les paramètres spécifiés
    2. Stocke les données dans le pipeline
    
    Args:
        pipeline: Instance de PredictionPipeline configurée
        n_days: Nombre de jours de prédictions
        n_samples_per_day: Nombre d'échantillons par jour (défaut: 48 pour 30min)
        feature_columns: Liste des colonnes features (optionnel)
    
    Returns:
        dict: Informations sur les données générées
        
    Raises:
        Exception: Si la génération échoue
    """
    if not pipeline.generate_data(
        n_days=n_days,
        n_samples_per_day=n_samples_per_day,
        feature_columns=feature_columns
    ):
        raise Exception("Échec de la génération des données d'inférence")
    
    logger.info(f"✅ Données d'inférence générées: {n_days} jours, {n_samples_per_day} échantillons/jour")
    
    return {
        "n_days": n_days,
        "n_samples_per_day": n_samples_per_day,
        "total_samples": n_days * n_samples_per_day
    }


@task(
    name="set_inference_data",
    description="Charge un DataFrame d'inférence existant dans le pipeline",
    retries=1
)
def set_inference_data_task(
    pipeline: PredictionPipeline,
    df_inference_path: str
) -> Dict[str, Any]:
    """
    Tâche Prefect : Charge un DataFrame d'inférence depuis un fichier.
    
    Alternative à generate_inference_data_task lorsque les données
    sont déjà disponibles dans un fichier.
    
    Args:
        pipeline: Instance de PredictionPipeline configurée
        df_inference_path: Chemin vers le fichier de données (CSV ou Parquet)
    
    Returns:
        dict: Informations sur les données chargées
        
    Raises:
        Exception: Si le chargement échoue
    """
    import pandas as pd
    
    # Charger le fichier selon l'extension
    if df_inference_path.endswith('.parquet'):
        df = pd.read_parquet(df_inference_path)
    elif df_inference_path.endswith('.csv'):
        df = pd.read_csv(df_inference_path)
    else:
        raise ValueError("Format de fichier non supporté (utilisez .csv ou .parquet)")
    
    if not pipeline.set_inference_data(df):
        raise Exception("Échec du chargement des données d'inférence")
    
    logger.info(f"✅ Données d'inférence chargées: {df.shape}")
    
    return {
        "shape": df.shape,
        "columns": list(df.columns)
    }


@task(
    name="prepare_features",
    description="Prépare les features à partir des données d'inférence",
    retries=1
)
def prepare_features_task(
    pipeline: PredictionPipeline
) -> Dict[str, Any]:
    """
    Tâche Prefect : Prépare les features pour le modèle.
    
    Cette tâche :
    1. Nettoie et transforme les données d'inférence
    2. Prépare les features pour le modèle
    
    Args:
        pipeline: Instance de PredictionPipeline avec données d'inférence chargées
    
    Returns:
        dict: Informations sur les features préparées
        
    Raises:
        Exception: Si la préparation échoue
    """
    df_features = pipeline.prepare_features()
    
    if df_features is None:
        raise Exception("Échec de la préparation des features")
    
    logger.info(f"✅ Features préparées: {df_features.shape}")
    
    return {
        "shape": df_features.shape,
        "columns": list(df_features.columns)
    }


@task(
    name="run_predictions",
    description="Exécute les prédictions avec le modèle chargé",
    retries=2,
    retry_delay_seconds=30
)
def run_predictions_task(
    pipeline: PredictionPipeline,
    feature_columns: Optional[list] = None
) -> Dict[str, Any]:
    """
    Tâche Prefect : Exécute les prédictions.
    
    Cette tâche :
    1. Utilise le modèle chargé pour générer des prédictions
    2. Calcule les scores de confiance
    3. Ajoute les prédictions aux données
    
    Args:
        pipeline: Instance de PredictionPipeline avec modèle et données chargés
        feature_columns: Liste des colonnes features (optionnel)
    
    Returns:
        dict: Informations sur les prédictions générées
        
    Raises:
        Exception: Si les prédictions échouent
    """
    if not pipeline.run_predictions(feature_columns=feature_columns):
        raise Exception("Échec de l'exécution des prédictions")
    
    df_predictions = pipeline.get_predictions_df()
    logger.info(f"✅ Prédictions générées: {len(df_predictions)} échantillons")
    
    return {
        "n_predictions": len(df_predictions),
        "has_confidence": 'confidence' in df_predictions.columns
    }


@task(
    name="store_predictions",
    description="Stocke les prédictions en base de données",
    retries=2,
    retry_delay_seconds=30
)
def store_predictions_task(
    pipeline: PredictionPipeline
) -> Dict[str, Any]:
    """
    Tâche Prefect : Stocke les prédictions en base de données.
    
    Cette tâche :
    1. Prépare les timestamps et métadonnées
    2. Insère les prédictions dans PostgreSQL
    3. Valide le stockage
    
    Args:
        pipeline: Instance de PredictionPipeline avec prédictions générées
    
    Returns:
        dict: Informations sur le stockage
        
    Raises:
        Exception: Si le stockage échoue
    """
    if not pipeline.store_predictions():
        raise Exception("Échec du stockage des prédictions")
    
    logger.info("✅ Prédictions stockées avec succès")
    
    return {
        "status": "stored",
        "timestamp": pipeline.df_predictions['prediction_timestamp'].iloc[0] if pipeline.df_predictions is not None else None
    }


@task(
    name="verify_results",
    description="Vérifie les résultats du pipeline de prédiction",
    retries=1
)
def verify_results_task(
    pipeline: PredictionPipeline
) -> Dict[str, Any]:
    """
    Tâche Prefect : Vérifie les résultats du pipeline.
    
    Cette tâche :
    1. Récupère les statistiques de la base de données
    2. Récupère les prédictions récentes
    3. Retourne les résultats pour validation
    
    Args:
        pipeline: Instance de PredictionPipeline avec prédictions stockées
    
    Returns:
        dict: Statistiques et prédictions récentes
    """
    stats = pipeline.db_handler.get_prediction_stats()
    recent_predictions = pipeline.verify_results()
    
    logger.info(f"✅ Vérification terminée: {stats}")
    
    return {
        "stats": stats,
        "recent_predictions_count": len(recent_predictions) if recent_predictions is not None else 0
    }
