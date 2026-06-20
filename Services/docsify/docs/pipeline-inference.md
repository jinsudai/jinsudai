# Pipeline d'Inférence

## Vue d'ensemble

Le pipeline d'inférence charge les modèles en production, génère des prédictions, et stocke les résultats dans PostgreSQL avec monitoring de drift.

## Workflow Prefect de prédiction

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
graph LR
    subgraph "Prediction Full Pipeline"
        A[setup_prediction_task] --> B[load_model_task<br/>Modèle prod]
        B --> C[generate_inference_data_task<br/>Génération features]
        C --> D[prepare_features_task<br/>Préparation]
        D --> E[run_predictions_task<br/>Inférence]
        E --> F[store_predictions_task<br/>PostgreSQL]
        F --> G[detect_drift_task<br/>Evidently]
        G --> H{Drift détecté?}
        H -->|Oui| I[retrain_model_task<br/>Retraining auto]
        H -->|Non| J[verify_results_task<br/>Vérification]
        I --> J
    end
    
    style A fill:#e1f5ff
    style E fill:#fff4e1
    style G fill:#fce4ec
    style I fill:#ffcccb
    style J fill:#e8f5e9
```

## Flux de données d'inférence

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
graph LR
    A[Requête API<br/>Features météo + calendrier] --> B[Validation Input<br/>Schéma & Ranges]
    B --> C{Valid?}
    C -->|Non| D[Rejet 400 Bad Request]
    C -->|Oui| E[Chargement Modèle<br/>MLflow Registry]
    E --> F[Prédictions<br/>AutoGluon Inference]
    F --> G[Formatage Output<br/>kWh + Timestamp]
    G --> H[Stockage PostgreSQL<br/>Table predictions]
    H --> I[Logging MLflow<br/>Run ID + Métriques]
    I --> J[Response 200 OK<br/>Prédiction retournée]
    
    style B fill:#e1f5ff
    style C fill:#fce4ec
    style F fill:#fff4e1
    style H fill:#e8f5e9
    style J fill:#d1c4e9
```

## Variants de pipelines d'inférence

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
graph LR
    subgraph "prediction_full_pipeline"
        F1[Config] --> F2[Modèle]
        F2 --> F3[Données]
        F3 --> F4[Prédictions]
        F4 --> F5[Stockage BD]
        F5 --> F6[Drift Detection]
        F6 --> F7[Retraining]
        F7 --> F8[Vérification]
    end
    
    subgraph "prediction_inference_only_pipeline"
        I1[Config] --> I2[Modèle]
        I2 --> I3[Données existantes]
        I3 --> I4[Prédictions]
        I4 --> I5[Output direct]
    end
    
    subgraph "prediction_batch_pipeline"
        B1[Config] --> B2[Modèle]
        B2 --> B3[Batch 1]
        B3 --> B4[Batch 2]
        B4 --> B5[Batch N]
        B5 --> B6[Stockage BD]
    end
    
    style F1 fill:#e1f5ff
    style I1 fill:#fff4e1
    style B1 fill:#e8f5e9
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
