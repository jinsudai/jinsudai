"""
Script pour déployer les flows avec des schedules automatiques.

- Training pipeline : toutes les semaines (dimanche à 2h du matin)
- Prediction pipeline : tous les jours à 1h du matin
- Actual values pipeline : tous les jours à 2h du matin (pour mettre à jour les valeurs de la veille)

Usage:
    python scripts/deploy_scheduled_flows.py
"""

from prefect.schedules import CronSchedule
from ml.workflows.consumption_flow import consumption_full_pipeline
from ml.workflows.prediction_flow import prediction_full_pipeline
from ml.workflows.actual_values_flow import actual_values_full_pipeline

if __name__ == "__main__":
    print("=== Déploiement des flows avec schedules ===\n")
    
    # 1. Déploiement du pipeline d'entraînement (hebdomadaire)
    print("1. Déploiement de consumption_full_pipeline (hebdomadaire)...")
    
    # Schedule : tous les dimanches à 2h00 du matin
    weekly_schedule = CronSchedule(cron="0 2 * * 0", timezone="Europe/Paris")
    
    consumption_full_pipeline.deploy(
        name="consumption-training-weekly",
        work_pool_name="default-pool",
        schedule=weekly_schedule,
        tags=["training", "consumption", "weekly", "production"],
        description="Pipeline d'entraînement hebdomadaire (dimanche 2h)",
        parameters={
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "raw_path": "data/templates/raw_template.csv",
            "output_dir": "data/processed/"
        }
    )
    print("✅ consumption_full_pipeline déployé (hebdomadaire)\n")
    
    # 2. Déploiement du pipeline de prédiction (quotidien)
    print("2. Déploiement de prediction_full_pipeline (quotidien)...")
    
    # Schedule : tous les jours à 1h00 du matin
    daily_schedule = CronSchedule(cron="0 1 * * *", timezone="Europe/Paris")
    
    prediction_full_pipeline.deploy(
        name="prediction-daily",
        work_pool_name="default-pool",
        schedule=daily_schedule,
        tags=["prediction", "consumption", "daily", "production"],
        description="Pipeline de prédiction quotidien (1h du matin)",
        parameters={
            "model_name": "consumption_model",
            "n_days": 1,
            "n_samples_per_day": 48,
            "alias_prod": "prod"
        }
    )
    print("✅ prediction_full_pipeline déployé (quotidien)\n")
    
    # 3. Déploiement du pipeline de valeurs réelles (quotidien)
    print("3. Déploiement de actual_values_full_pipeline (quotidien)...")
    
    # Schedule : tous les jours à 2h00 du matin (après le pipeline de prédiction)
    daily_schedule_2am = CronSchedule(cron="0 2 * * *", timezone="Europe/Paris")
    
    actual_values_full_pipeline.deploy(
        name="actual-values-daily",
        work_pool_name="default-pool",
        schedule=daily_schedule_2am,
        tags=["actual-values", "daily", "production"],
        description="Pipeline de mise à jour des valeurs réelles quotidien (2h du matin)",
        parameters={}
    )
    print("✅ actual_values_full_pipeline déployé (quotidien)\n")
    
    print("=== Tous les flows déployés avec succès ===")
    print("Schedule entraînement : Tous les dimanches à 2h (Europe/Paris)")
    print("Schedule prédiction : Tous les jours à 1h (Europe/Paris)")
    print("Schedule valeurs réelles : Tous les jours à 2h (Europe/Paris)")
    print("Accédez à l'UI Prefect: http://localhost:4200")
