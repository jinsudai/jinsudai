# Architecture Globale

## Vue d'ensemble des composants

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
graph LR
    subgraph "Sources de Données"
        A[Données BRUT<br/>CSV PRM]
        B[Données Météo<br/>API Open-Meteo]
        C[Données Vacances<br/>API]
    end
    
    subgraph "Orchestration"
        D[Prefect Server<br/>Workflows]
        E[Airflow<br/>Scheduling]
    end
    
    subgraph "ML & Tracking"
        F[MLflow<br/>Model Registry]
        G[AutoGluon<br/>Training]
    end
    
    subgraph "API & Inference"
        H[FastAPI<br/>REST API]
        I[Streamlit<br/>UI Prédictions]
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
    F --> I
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
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
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
        
        subgraph "Grafana"
            GR1[Grafana<br/>Port 3000]
            GR2[Dashboards]
            GR3[Datasources]
        end
        
        subgraph "Prefect"
            PF1[Prefect Server<br/>Port 4200]
            PF2[Prefect Worker]
            PF3[Work Pool]
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
    PF1 --> FA1
    PF1 --> ML1
    PF1 --> EV1
    EV1 --> GR1
    AF1 --> PF1
    
    style ML1 fill:#ff6b6b
    style FA1 fill:#4ecdc4
    style EV1 fill:#45b7d1
    style GR1 fill:#f39c12
    style PF1 fill:#9b59b6
    style AF1 fill:#e74c3c
```

## Flux de données complet

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
sequenceDiagram
    participant Source as Sources Externes
    participant Ingest as Ingestion Prefect
    participant Process as Traitement
    participant Train as Training
    participant MLflow as MLflow
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Monitor as Evidently
    
    Source->>Ingest: Données brutes (CSV)
    Ingest->>Process: Validation & Nettoyage
    Process->>Process: Feature Engineering
    Process->>Train: Données préparées
    Train->>Train: Entraînement AutoGluon
    Train->>MLflow: Log métriques & modèle
    MLflow-->>Train: Model URI
    Train->>MLflow: Promotion en production
    
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
    
    style Source fill:#e1f5ff
    style Train fill:#fff4e1
    style MLflow fill:#d1c4e9
    style Monitor fill:#fce4ec
```

## Structure du code

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
graph LR
    subgraph "src/"
        subgraph "ml/"
            M1[config.py<br/>Gestion config]
            M2[consumption/<br/>Domaine consommation]
            M3[solar_production/<br/>Domaine solaire]
            M4[data/<br/>Loading, Validation]
            M5[models/<br/>Training, Inference]
            M6[monitoring/<br/>Drift Detection]
            M7[pipelines/<br/>Orchestration]
            M8[utils/<br/>Utilitaires]
            M9[workflows/<br/>Flows Prefect]
        end
        
        subgraph "connectors/"
            C1[resend_client/<br/>Email]
            C2[database/<br/>PostgreSQL]
            C3[mlflow/<br/>Tracking]
        end
        
        subgraph "configs/"
            CFG1[consumption.dev.yaml]
            CFG2[consumption.prod.yaml]
            CFG3[consumption.test.yaml]
        end
    end
    
    subgraph "scripts/"
        S1[deploy_prediction_flows.py]
        S2[deploy_prediction_schedule.py]
        S3[create_test_data.py]
        S4[send_notification.py]
    end
    
    subgraph "Services/"
        SVC1[MLflow/]
        SVC2[FastApi/]
        SVC3[EvidentlyAI/]
        SVC4[Grafana/]
        SVC5[Airflow/]
        SVC6[Prefect/]
    end
    
    style M1 fill:#e1f5ff
    style M9 fill:#fff4e1
    style S1 fill:#e8f5e9
    style SVC1 fill:#fce4ec
```

## Différenciation par configuration

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
graph LR
    subgraph "Config Consommation"
        C1[src/ml/consumption/<br/>configs/config.yaml]
        C2[Problem: Regression]
        C3[Features: Temp, Humidité, Précip]
        C4[Métrique: R² >= 0.90]
        C5[Alert: R² < 0.85]
        C6[Experiment: energy_consumption]
    end
    
    subgraph "Config Production Solaire"
        S1[src/ml/solar_production/<br/>configs/config.yaml]
        S2[Problem: Regression]
        S3[Features: Temp, Humidité, Irradiance, Cloud]
        S4[Métrique: R² >= 0.92]
        S5[Alert: R² < 0.88]
        S6[Experiment: solar_production]
    end
    
    subgraph "Code Partagé"
        SH1[src/ml/data/]
        SH2[src/ml/models/]
        SH3[src/ml/monitoring/]
        SH4[src/ml/pipelines/]
    end
    
    C1 --> SH1
    S1 --> SH1
    C1 --> SH2
    S1 --> SH2
    C1 --> SH3
    S1 --> SH3
    C1 --> SH4
    S1 --> SH4
    
    style C1 fill:#e1f5ff
    style S1 fill:#fff4e1
    style SH1 fill:#e8f5e9
```
