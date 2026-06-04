FROM ghcr.io/mlflow/mlflow:v3.10.1

USER root

# dossier artefacts
RUN mkdir -p /mlflow/artifacts

# créer un utilisateur mlflow avec UID 1000
RUN useradd -m -u 1000 mlflow

# Switch back to airflow user
USER mlflow

RUN pip install --upgrade pip
RUN pip install --no-cache-dir psycopg2-binary boto3

EXPOSE 7860

ARG AWS_DEFAULT_REGION
ARG AWS_REGION
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG MLFLOW_S3_ENDPOINT_URL

# A supprimer si cela continue de fonctionner sans
#ARG MLFLOW_REGISTRY_URI
#ARG MLFLOW_TRACKING_URI
#ARG MLFLOW_POSTGRES_URI
#ARG MLFLOW_ENABLE_TRACING=true

# Possibilité d'améliorer la sécurité en cherchant à limiter   --allowed-hosts "*" \   --cors-allowed-origins "*" à des domaines spécifiques
# Pas sur que cela soit possible dans le contexte de Hugging Face Spaces, à vérifier
CMD mlflow server --host 0.0.0.0 \
  --port 7860 \
  --backend-store-uri $MLFLOW_POSTGRES_URI \
  --default-artifact-root "s3://mlflow-artifacts/" \
  --allowed-hosts "*" \
  --cors-allowed-origins "*"