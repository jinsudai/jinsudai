"""
Script pour déployer les flows de prédiction sur le serveur Prefect.

Exécutez ce script pour enregistrer les flows dans le serveur Prefect
et les rendre disponibles dans l'UI.

Usage:
    python scripts/deploy_prediction_flows.py
"""

from prefect import get_client
from ml.workflows.prediction_flow import (
    prediction_full_pipeline,
    prediction_inference_only_pipeline,
    prediction_batch_pipeline
)

async def create_work_pool_if_not_exists(pool_name: str):
    """Create work pool if it doesn't exist."""
    import subprocess
    async with get_client() as client:
        try:
            await client.read_work_pool(pool_name)
            print(f"Work pool '{pool_name}' already exists")
        except Exception:
            print(f"Creating work pool '{pool_name}'...")
            try:
                subprocess.run(
                    ["prefect", "work-pool", "create", pool_name, "--type", "process"],
                    check=True,
                    capture_output=True
                )
                print(f"✅ Work pool '{pool_name}' created")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Failed to create work pool via CLI: {e}")
                print("Continuing with deployment...")

if __name__ == "__main__":
    import asyncio
    
    print("=== Déploiement des flows de prédiction ===\n")
    
    # Create work pool if it doesn't exist
    asyncio.run(create_work_pool_if_not_exists("default-pool"))
    print()
    
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
