"""
Package des workflows Prefect pour l'analytics.

Contient les flows d'orchestration pour les différents domaines
(consumption, solar_production, prediction, etc.).

NOTE: Les workflows Prefect ont été désactivés et déplacés vers le répertoire disabled/.
Pour utiliser les workflows, utiliser les scripts simples dans pipelines/ et scripts/.
"""

# Les workflows Prefect sont désactivés - voir le répertoire disabled/
# from ml.workflows.consumption_flow import (
#     consumption_full_pipeline,
#     consumption_data_pipeline,
#     consumption_training_only_pipeline
# )

# from ml.workflows.prediction_flow import (
#     prediction_full_pipeline,
#     prediction_inference_only_pipeline,
#     prediction_batch_pipeline
# )

# from ml.workflows.sftp_ingestion_flow import (
#     sftp_ingestion_pipeline
# )

__all__ = []
