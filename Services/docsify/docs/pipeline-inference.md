# Pipeline d'Inférence

## Vue d'ensemble

Le pipeline d'inférence charge les modèles en production, génère des prédictions, et stocke les résultats dans PostgreSQL avec monitoring de drift.

## Pipeline d'Inférence

```mermaid
graph LR
    subgraph "inference_pipeline"
        A[setup<br/>MLflow + PostgreSQL] --> B[load_model<br/>Modèle prod via Alias]
        B --> C[generate_data<br/>Génération données d'inférence]
        C --> D[prepare_features<br/>Nettoyage & préparation]
        D --> E[run_predictions<br/>Inférence AutoGluon]
        E --> F[store_predictions<br/>PostgreSQL]
        F --> G[verify_results<br/>Vérification statistiques]
    end

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style D fill:#fce4ec
    style E fill:#ffcccb
    style F fill:#e8f5e9
    style G fill:#d1c4e9
```


## Endpoints FastAPI

### POST /predict
- **Description**: Prédiction individuelle
- **Input**: Features météo + calendrier
- **Output**: Prédiction kWh + timestamp
- **Temps de réponse**: < 100ms

### POST /predict/batch
- **Description**: Prédictions par lot
- **Input**: Array de features
- **Output**: Array de prédictions
- **Temps de réponse**: < 500ms (100 items)