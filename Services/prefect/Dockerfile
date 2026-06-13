FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances du projet
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Installer Prefect
RUN pip install --no-cache-dir prefect==3.7.0

# Copier le code source
COPY src/ /app/src/
COPY config.yaml /app/
COPY src/configs/ /app/src/configs/

ENV PREFECT_UI_API_URL=/api

EXPOSE 7860

# Déployer les flows puis démarrer le serveur
RUN prefect deploy src/ml/workflows/consumption_flow.py:consumption_full_pipeline --pool default || true
RUN prefect deploy src/ml/workflows/prediction_flow.py:prediction_full_pipeline --pool default || true
RUN prefect deploy src/ml/workflows/sftp_ingestion_flow.py:sftp_ingestion_pipeline --pool default || true
RUN prefect deploy src/ml/workflows/holidays_flow.py:holidays_annual_pipeline --pool default || true
RUN prefect deploy src/ml/workflows/actual_values_flow.py:actual_values_full_pipeline --pool default || true

CMD ["prefect", "server", "start", "--host", "0.0.0.0", "--port", "7860"]