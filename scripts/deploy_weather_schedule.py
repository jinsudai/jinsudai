"""
Script de déploiement du scheduling Prefect pour le flow weather.

Ce script configure l'exécution automatique quotidienne du flow update_weather_daily_flow.
"""
from prefect import serve
from prefect.deployments import Deployment
from prefect.schedules import CronSchedule
from pathlib import Path
import sys

# Ajouter le répertoire src au path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ml.workflows.weather_flow import update_weather_daily_flow

def deploy_weather_schedule():
    """
    Déploie le flow weather avec un scheduling quotidien.
    
    Le flow sera exécuté tous les jours à 1h du matin (heure serveur).
    """
    
    # Créer le déploiement avec scheduling quotidien
    deployment = Deployment(
        name="weather-daily-update",
        flow=update_weather_daily_flow,
        schedule=CronSchedule(cron="0 1 * * *"),  # Tous les jours à 1h du matin
        tags=["weather", "daily", "data-update"],
        description="Mise à jour quotidienne des données météo pour Aix en Provence",
        parameters={
            "config_path": "src/configs/consumption.yaml",
            "days_ahead": 7
        }
    )
    
    # Déployer
    deployment.build()
    
    print("✅ Déploiement weather-daily-update créé avec succès")
    print("   Schedule: Tous les jours à 1h du matin")
    print("   Flow: update_weather_daily_flow")
    
    return deployment

if __name__ == "__main__":
    deploy_weather_schedule()
