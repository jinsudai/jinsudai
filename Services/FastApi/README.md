---
title: FastAPI - Consumption Prediction Service
emoji: ⚡
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# FastAPI Consumption Prediction Service

FastAPI service for predicting energy consumption using MLflow models.

## Endpoints

### `/predict`
Predict energy consumption for a single data point.

**Request:**
```json
{
  "Horodate": "2024-01-01T00:00:00",
  "temperature_2m_mean": 15.5,
  "relative_humidity_mean": 70.0,
  "precipitation_sum": 0.0,
  "is_vacances": 0,
  "jour_de_la_semaine": "Lundi",
  "jour_ferie": 0
}
```

**Response:**
```json
{
  "prediction": 125.5,
  "timestamp": "2024-01-01T00:00:00",
  "model_version": "1"
}
```

### `/predict/batch`
Batch prediction for multiple data points.

**Request:**
```json
[
  {
    "Horodate": "2024-01-01T00:00:00",
    "temperature_2m_mean": 15.5,
    "relative_humidity_mean": 70.0,
    "precipitation_sum": 0.0,
    "is_vacances": 0,
    "jour_de_la_semaine": "Lundi",
    "jour_ferie": 0
  }
]
```

**Response:**
```json
[
  {
    "prediction": 125.5,
    "timestamp": "2024-01-01T00:00:00",
    "model_version": "1"
  }
]
```

### `/health`
Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "model_loaded": true,
  "model_version": "1",
  "mlflow_tracking_uri": "https://jinsudai-mlflow.hf.space/"
}
```

## Environment Variables

- `ENV`: Environment (dev, test, prod) - default: `dev`
- `MLFLOW_TRACKING_URI`: MLflow tracking URI - default: `https://jinsudai-mlflow.hf.space/`
- `MODEL_NAME`: MLflow model name - default: `consumption_model`
- `MODEL_STAGE`: MLflow model stage - default: `prod`

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn main:app --reload --port 8000
```

## Docker

```bash
# Build
docker build -t fastapi-consumption .

# Run
docker run -p 7860:7860 fastapi-consumption
```

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:7860/docs`
- ReDoc: `http://localhost:7860/redoc`
