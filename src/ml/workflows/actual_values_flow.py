"""
Flow Prefect pour le pipeline de mise à jour des valeurs réelles.

Ce flow orchestre toutes les étapes :
1. Configuration du pipeline (Base de données)
2. Récupération des prédictions de la veille
3. Génération de valeurs aléatoires (pour l'instant)
4. Mise à jour des enregistrements dans la base de données
5. Vérification des mises à jour

Exemple d'utilisation :
    from ml.workflows.actual_values_flow import actual_values_full_pipeline
    
    # Exécuter le pipeline complet
    result = actual_values_full_pipeline()
"""

from prefect import flow, task
from typing import Dict, Any, Optional
import logging

from ml.utils.pipelines.Actual_values_pipeline import ActualValuesPipeline
from ml.config import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@task
def setup_actual_values_task(db_uri: str) -> ActualValuesPipeline:
    """
    Tâche de configuration du pipeline de valeurs réelles.
    
    Args:
        db_uri: URI de connexion PostgreSQL
        
    Returns:
        ActualValuesPipeline: Pipeline configuré
    """
    pipeline = ActualValuesPipeline(db_uri)
    if not pipeline.setup():
        raise ValueError("Impossible de configurer le pipeline de valeurs réelles")
    return pipeline


@task
def get_previous_day_task(pipeline: ActualValuesPipeline) -> Dict[str, Any]:
    """
    Tâche de récupération des prédictions de la veille.
    
    Args:
        pipeline: Pipeline de valeurs réelles
        
    Returns:
        dict: Informations sur les prédictions récupérées
    """
    success = pipeline.get_previous_day_predictions()
    if not success:
        return {"status": "no_predictions", "count": 0}
    
    return {
        "status": "success",
        "count": len(pipeline.previous_day_predictions) if pipeline.previous_day_predictions else 0
    }


@task
def generate_random_values_task(pipeline: ActualValuesPipeline) -> Dict[str, Any]:
    """
    Tâche de génération de valeurs aléatoires.
    
    Args:
        pipeline: Pipeline de valeurs réelles
        
    Returns:
        dict: Informations sur les valeurs générées
    """
    success = pipeline.generate_random_actual_values()
    if not success:
        return {"status": "failed", "count": 0}
    
    return {
        "status": "success",
        "count": pipeline.updated_count
    }


@task
def verify_updates_task(pipeline: ActualValuesPipeline) -> Dict[str, Any]:
    """
    Tâche de vérification des mises à jour.
    
    Args:
        pipeline: Pipeline de valeurs réelles
        
    Returns:
        dict: Informations sur les mises à jour vérifiées
    """
    updated_predictions = pipeline.verify_updates()
    
    if updated_predictions is None:
        return {"status": "failed", "verified_count": 0}
    
    with_actual_values = updated_predictions[updated_predictions['actual_value'].notna()]
    
    return {
        "status": "success",
        "verified_count": len(with_actual_values),
        "total_count": len(updated_predictions)
    }


@flow(
    name="actual-values-full-pipeline",
    description="Pipeline complet de mise à jour des valeurs réelles : configuration → récupération veille → génération aléatoire → mise à jour BD",
    retries=1,
    retry_delay_seconds=60
)
def actual_values_full_pipeline(
    db_uri: Optional[str] = None
) -> Dict[str, Any]:
    """
    Pipeline complet pour la mise à jour des valeurs réelles.
    
    Étapes :
    1. Configuration du pipeline (Base de données)
    2. Récupération des prédictions de la veille
    3. Génération de valeurs aléatoires
    4. Mise à jour des enregistrements dans la base de données
    5. Vérification des mises à jour
    
    Args:
        db_uri: URI de connexion PostgreSQL (optionnel, utilise la config par défaut)
    
    Returns:
        dict: Résultats complets du pipeline
    """
    # Charger la config pour les valeurs par défaut
    config = load_config(config_name="consumption")
    
    if db_uri is None:
        db_uri = config.get('database', {}).get('uri')
    
    logger.info("####################################################")
    logger.info("### PIPELINE DE MISE À JOUR DES VALEURS RÉELLES ###")
    logger.info("####################################################\n")
    
    # 1. ===== CONFIGURATION =====
    logger.info("=== ÉTAPE 1: Configuration du pipeline ===")
    
    pipeline = setup_actual_values_task(db_uri=db_uri)
    
    # 2. ===== RÉCUPÉRATION DES PRÉDICTIONS DE LA VEILLE =====
    logger.info("\n=== ÉTAPE 2: Récupération des prédictions de la veille ===")
    
    retrieval_info = get_previous_day_task(pipeline=pipeline)
    
    if retrieval_info["status"] == "no_predictions":
        logger.warning("Aucune prédiction trouvée pour la veille, pipeline terminé")
        return {
            "status": "no_predictions",
            "retrieval": retrieval_info,
            "generation": {"status": "skipped"},
            "verification": {"status": "skipped"}
        }
    
    # 3. ===== GÉNÉRATION DE VALEURS ALÉATOIRES =====
    logger.info("\n=== ÉTAPE 3: Génération de valeurs aléatoires ===")
    
    generation_info = generate_random_values_task(pipeline=pipeline)
    
    # 4. ===== VÉRIFICATION =====
    logger.info("\n=== ÉTAPE 4: Vérification des mises à jour ===")
    
    verification_info = verify_updates_task(pipeline=pipeline)
    
    # 5. ===== RÉSULTAT FINAL =====
    logger.info("\n" + "="*60)
    logger.info("PIPELINE DE VALEURS RÉELLES TERMINÉ AVEC SUCCÈS")
    logger.info("="*60)
    
    return {
        "status": "success",
        "retrieval": retrieval_info,
        "generation": generation_info,
        "verification": verification_info
    }
