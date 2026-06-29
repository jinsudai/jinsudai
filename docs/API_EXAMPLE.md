# API Examples - JinsudAPI

## Prédiction de consommation

### Endpoint
`POST /predict`

### Exemple de requête curl

```bash
curl -X 'POST' \
  'https://jetestai-jinsudapi.hf.space/predict' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "Horodate": "2024-01-15T14:30:00",
  "temperature_2m_mean": 12.5,
  "relative_humidity_mean": 65.0,
  "precipitation_sum": 0.0,
  "is_vacances": 0,
  "jour_de_la_semaine": "Lundi",
  "jour_ferie": 0
}'
```

### Description des champs

| Champ | Type | Description | Exemple |
|-------|------|-------------|---------|
| `Horodate` | string | Timestamp au format ISO 8601 | `"2024-01-15T14:30:00"` |
| `temperature_2m_mean` | float | Température moyenne en °C | `12.5` |
| `relative_humidity_mean` | float | Humidité relative moyenne en % | `65.0` |
| `precipitation_sum` | float | Précipitations totales en mm | `0.0` |
| `is_vacances` | int | 1 si période de vacances, 0 sinon | `0` |
| `jour_de_la_semaine` | string | Jour de la semaine en français | `"Lundi"` |
| `jour_ferie` | int | 1 si jour férié, 0 sinon | `0` |

### Réponse attendue

```json
{
  "prediction": 1234.56,
  "timestamp": "2024-01-15T14:30:00.123456",
  "model_version": "35"
}
```

## Prédiction par lot (Batch)

### Endpoint
`POST /predict/batch`

### Exemple de requête curl

```bash
curl -X 'POST' \
  'https://jetestai-jinsudapi.hf.space/predict/batch' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '[
  {
    "Horodate": "2024-01-15T08:00:00",
    "temperature_2m_mean": 10.0,
    "relative_humidity_mean": 70.0,
    "precipitation_sum": 0.0,
    "is_vacances": 0,
    "jour_de_la_semaine": "Lundi",
    "jour_ferie": 0
  },
  {
    "Horodate": "2024-01-15T12:00:00",
    "temperature_2m_mean": 14.5,
    "relative_humidity_mean": 60.0,
    "precipitation_sum": 0.5,
    "is_vacances": 0,
    "jour_de_la_semaine": "Lundi",
    "jour_ferie": 0
  }
]'
```

### Réponse attendue

```json
[
  {
    "prediction": 1100.0,
    "timestamp": "2024-01-15T12:00:00.123456",
    "model_version": "35"
  },
  {
    "prediction": 1350.0,
    "timestamp": "2024-01-15T12:00:00.123456",
    "model_version": "35"
  }
]
```

## Health Check

### Endpoint
`GET /health`

### Exemple de requête curl

```bash
curl -X 'GET' \
  'https://jetestai-jinsudapi.hf.space/health' \
  -H 'accept: application/json'
```

### Réponse attendue

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T14:30:00.123456",
  "model_loaded": true,
  "model_version": "35",
  "mlflow_tracking_uri": "https://jinsudai-mlflow.hf.space/"
}
```
