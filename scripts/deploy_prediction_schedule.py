"""
Script de déploiement du scheduling Prefect pour le flow prediction.

Ce script configure l'exécution automatique quotidienne du flow prediction_full_pipeline.
"""
from prefect import serve
from prefect.deployments import Deployment
from prefect.schedules import CronSchedule
from pathlib import Path
import sys

# Ajouter le répertoire src au path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ml.workflows.prediction_flow import prediction_full_pipeline

def deploy_prediction_schedule():
    """
    Déploie le flow prediction avec un scheduling quotidien.
    
    Le flow sera exécuté tous les jours à 2h du matin (heure serveur),
    après la mise à jour des données météo.
    """
    
    # Créer le déploiement avec scheduling quotidien
    deployment = Deployment(
        name="prediction-daily-pipeline",
        flow=prediction_full_pipeline,
        schedule=CronSchedule(cron="0 2 * * *"),  # Tous les jours à 2h du matin
        tags=["prediction", "daily", "drift-detection", "retraining"],
        description="Pipeline de prédiction quotidien avec détection de drift et retraining automatique",
        parameters={
            "model_name": "consumption_model",
            "n_days": 3
        }
    )
    
    # Déployer
    deployment.build()
    
    print("✅ Déploiement prediction-daily-pipeline créé avec succès")
    print("   Schedule: Tous les jours à 2h du matin")
    print("   Flow: prediction_full_pipeline")
    print("   Inclut: Détection de drift + Retraining automatique")
    
    return deployment

if __name__ == "__main__":
    deploy_prediction_schedule()
