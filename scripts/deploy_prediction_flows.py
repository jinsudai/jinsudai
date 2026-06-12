"""
Script pour déployer les flows de prédiction sur le serveur Prefect.

Exécutez ce script pour enregistrer les flows dans le serveur Prefect
et les rendre disponibles dans l'UI.

Usage:
    python scripts/deploy_prediction_flows.py
"""

from ml.workflows.prediction_flow import (
    prediction_full_pipeline,
    prediction_inference_only_pipeline,
    prediction_batch_pipeline
)

if __name__ == "__main__":
    print("=== Déploiement des flows de prédiction ===\n")
    
    # Déployer le pipeline complet
    print("1. Déploiement de prediction_full_pipeline...")
    prediction_full_pipeline.deploy(
        name="prediction-full-pipeline",
        work_pool_name="default-pool",
        tags=["prediction", "consumption", "production"],
        description="Pipeline complet de prédiction avec stockage BD"
    )
    print("✅ prediction_full_pipeline déployé\n")
    
    # Déployer le pipeline d'inférence seulement
    print("2. Déploiement de prediction_inference_only_pipeline...")
    prediction_inference_only_pipeline.deploy(
        name="prediction-inference-only",
        work_pool_name="default-pool",
        tags=["prediction", "inference", "test"],
        description="Pipeline d'inférence sans stockage BD"
    )
    print("✅ prediction_inference_only_pipeline déployé\n")
    
    # Déployer le pipeline batch
    print("3. Déploiement de prediction_batch_pipeline...")
    prediction_batch_pipeline.deploy(
        name="prediction-batch",
        work_pool_name="default-pool",
        tags=["prediction", "batch", "long-period"],
        description="Pipeline de prédiction par batch pour longues périodes"
    )
    print("✅ prediction_batch_pipeline déployé\n")
    
    print("=== Tous les flows déployés avec succès ===")
    print("Accédez à l'UI Prefect: http://localhost:4200")
