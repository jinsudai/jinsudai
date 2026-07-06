# Architecture Globale

## Vue d'ensemble des composants

```mermaid
graph LR
    subgraph "Sources de Données"
        A[Données BRUT<br/>CSV PRM]
        B[Données Météo<br/>API Open-Meteo]
        C[Données Vacances<br/>API]
    end

    subgraph "Orchestration"
        D[Airflow<br/>Workflows & Scheduling]
    end

    subgraph "ML & Tracking"
        F[MLflow<br/>Model Registry]
        G[AutoGluon<br/>Training]
    end

    subgraph "API & Inference"
        H[FastAPI<br/>REST API]
    end

    subgraph "Monitoring"
        J[Evidently AI<br/>Drift Detection]
        K[Grafana<br/>Dashboards]
    end

    subgraph "Stockage"
        L[PostgreSQL<br/>Prédictions]
        M[S3<br/>Artefacts MLflow]
    end

    A --> D
    B --> D
    C --> D
    D --> F
    D --> G
    F --> H
    H --> L
    D --> J
    J --> K
    F --> M
    L --> J

    style D fill:#e1f5ff
    style F fill:#fff4e1
    style H fill:#e8f5e9
    style J fill:#fce4ec
```

## Architecture détaillée des services

```mermaid
graph LR
    subgraph "Services Dockerisés"
        subgraph "MLflow"
            ML1[MLflow Server<br/>Port 7860]
            ML2[PostgreSQL Backend]
            ML3[S3 Artefacts]
        end
        
        subgraph "FastAPI"
            FA1[FastAPI Service<br/>Port 8000]
            FA2[Health Check]
            FA3[Prediction Endpoint]
        end
        
        subgraph "Evidently"
            EV1[Evidently AI<br/>Port 8501]
            EV2[Workspace]
            EV3[Reports HTML]
        end
        
        subgraph "Airflow"
            AF1[Airflow Webserver<br/>Port 8080]
            AF2[Airflow Scheduler]
            AF3[Airflow Worker]
        end
    end
    
    ML1 -.-> ML2
    ML1 -.-> ML3
    FA1 --> ML1
    AF1 --> FA1
    AF1 --> ML1
    AF1 --> EV1
    
    style ML1 fill:#ff6b6b
    style FA1 fill:#4ecdc4
    style EV1 fill:#45b7d1
    style AF1 fill:#9b59b6
```

## Flux de données complet (A finaliser)

```mermaid
sequenceDiagram
    participant Source as Sources Externes
    participant Ingest as Ingestion
    participant Process as Preparation
    participant MLflow as MLflow
    participant API as Inference
    participant DB as PostgreSQL
    participant Monitor as Evidently
    participant Train as Training
    
    Source->>Ingest: Données brutes (CSV)
    Ingest->>Process: Validation & Nettoyage
    Process->>Process: Feature Engineering
    Process->>Monitor: Données préparées
    
    Note over API,DB: Phase d'Inférence
    
    API->>MLflow: Chargement modèle prod
    MLflow-->>API: Modèle chargé
    API->>API: Prédictions
    API->>DB: Stockage prédictions
    
    Note over DB,Monitor: Phase de Monitoring
    
    DB->>Monitor: Données production
    Monitor->>Monitor: Comparaison référence
    Monitor->>Monitor: Détection drift
    Monitor-->>Train: Trigger retraining
    Train->>Train: Entraînement AutoGluon
    Train->>MLflow: Log métriques & modèle
    MLflow-->>Train: Model URI
    Train->>MLflow: Promotion en production
```



## Flux de données d'entraînement (à finaliser)

```mermaid
graph LR
    A[Données brutes CSV<br/>data/raw/] --> B[Data Validation<br/>Schéma & Valeurs]
    B --> C[Data Preparation<br/>Nettoyage & Normalisation]
    C --> D[Feature Engineering<br/>Météo + Calendrier]
    D --> E[Split Train/Test<br/>80/20]
    E --> F[Training AutoGluon<br/>Regression]
    F --> G[Évaluation Modèle<br/>R², MAE, RMSE]
    G --> H{Performance OK?}
    H -->|Oui| I[Log MLflow<br/>Métriques + Artefacts]
    H -->|Non| J[Hyperparameter Tuning]
    J --> F
    I --> K[Promotion Production<br/>Alias 'prod']
    K --> L[Modèle en production]

    style B fill:#e1f5ff
    style F fill:#fff4e1
    style G fill:#e8f5e9
    style H fill:#fce4ec
    style I fill:#d1c4e9
```

## Flux de données d'inférence (à finaliser)

```mermaid
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

## Conformité au Cahier des Charges

### Mapping Objectifs → Implémentation

```mermaid
graph LR
    subgraph "Objectifs Cahier des Charges"
        O1[Créer algorithme IA<br/>adapté aux données]
        O2[Adapter infrastructure<br/>API production]
        O3[Concevoir pipelines CI/CD<br/>automatiser déploiement]
        O4[Développer scripts<br/>réentraînement auto]
        O5[Piloter performance<br/>monitoring production]
    end

    subgraph "Implémentation"
        I1[AutoGluon Training<br/>Multi-domaines]
        I2[FastAPI REST API]
        I3[GitHub Actions<br/>+ Docker Compose]
        I4[Airflow DAGs<br/>+ Drift Detection]
        I5[Evidently AI<br/>+ Grafana Dashboards]
    end

    O1 --> I1
    O2 --> I2
    O3 --> I3
    O4 --> I4
    O5 --> I5

    style O1 fill:#e1f5ff
    style O2 fill:#fff4e1
    style O3 fill:#e8f5e9
    style O4 fill:#fce4ec
    style O5 fill:#d1c4e9
```
