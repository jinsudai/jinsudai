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

__all__ = [
    # Consumption flows
    "consumption_full_pipeline",
    "consumption_data_pipeline",
    "consumption_training_only_pipeline",
    # Prediction flows
    "prediction_full_pipeline",
    "prediction_inference_only_pipeline",
    "prediction_batch_pipeline",
]
