"""
Package des workflows Prefect pour l'analytics.

Contient les flows d'orchestration pour les différents domaines
(consumption, solar_production, prediction, etc.).
"""

# Export des flows de consommation
from ml.workflows.consumption_flow import (
    consumption_full_pipeline,
    consumption_data_pipeline,
    consumption_training_only_pipeline
)

# Export des flows de prédiction
from ml.workflows.prediction_flow import (
    prediction_full_pipeline,
    prediction_inference_only_pipeline,
    prediction_batch_pipeline
)

# Export des flows d'ingestion SFTP
from ml.workflows.sftp_ingestion_flow import (
    sftp_ingestion_pipeline
)

__all__ = [
    # Consumption flows
    "consumption_full_pipeline",
    "consumption_data_pipeline",
    "consumption_training_only_pipeline",
    # Prediction flows
    "prediction_full_pipeline",
    "prediction_inference_only_pipeline",
    "prediction_batch_pipeline",
    # SFTP ingestion flows
    "sftp_ingestion_pipeline",
]
