# Architecture Globale

## Vue d'ensemble des composants

Cette section présente une vue d'ensemble des composants de l'architecture MLOps, incluant les sources de données, l'orchestration, le ML & Tracking, l'API & Inference, le Monitoring et le Stockage.

## Architecture détaillée des services

Cette section détaille l'architecture des services dockerisés, incluant MLflow, FastAPI, Evidently, Grafana et Airflow avec leurs composants respectifs.

## Flux de données complet

Cette section présente le flux de données complet depuis les sources externes jusqu'au monitoring, en passant par l'ingestion, le traitement, l'entraînement et l'inférence.

## Structure du code

Cette section décrit la structure du code source, incluant les modules ml, connectors, configs, scripts et Services.

## Différenciation par configuration

Cette section explique comment la configuration différencie les domaines consommation et production solaire, avec du code partagé.

## Flux de données d'entraînement

Cette section détaille le flux de données d'entraînement, depuis les données brutes jusqu'à la promotion en production.

## Flux de données d'inférence

Cette section présente le flux de données d'inférence, depuis la requête API jusqu'à la réponse avec stockage et logging.

## Conformité au Cahier des Charges

### Mapping Objectifs → Implémentation

Cette section mappe les objectifs du cahier des charges vers leur implémentation technique.

### Spécifications techniques respectées

| Spécification | Implémentation | Statut |
|---------------|----------------|--------|
| **Algorithmes IA** | AutoGluon (regression) pour consommation et production solaire | ✅ |
| **Métriques** | R² >= 0.90 (consommation), R² >= 0.92 (solaire) | ✅ |
| **Temps inférence** | < 100ms par requête (FastAPI) | ✅ |
| **API Production** | FastAPI avec endpoints /predict et /predict/batch | ✅ |
| **CI/CD** | GitHub Actions avec Docker + Hugging Face Spaces | ✅ |
| **Réentraînement auto** | Airflow DAGs avec triggers drift + cycle hebdo | ✅ |
| **Monitoring** | Evidently AI + Grafana dashboards | ✅ |
| **Alertes** | Email via Resend + Slack webhooks | ✅ |
| **Stockage modèles** | MLflow Model Registry avec promotion prod | ✅ |
| **Données** | PostgreSQL pour prédictions, S3 pour artefacts | ✅ |

## Résumé des Flows Principaux

Cette section résume les principaux flows Airflow pour les prédictions, l'entraînement, l'ingestion de données et le monitoring.

## Services déployés

Cette section présente les services déployés, incluant le core MLOps, l'inférence, le monitoring, le stockage et les notifications.

---

## Diagrammes

### Vue d'ensemble des composants

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
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

### Architecture détaillée des services

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
    EV1 --> GR1
    
    style ML1 fill:#ff6b6b
    style FA1 fill:#4ecdc4
    style EV1 fill:#45b7d1
    style GR1 fill:#f39c12
    style AF1 fill:#9b59b6
```

### Flux de données complet

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
sequenceDiagram
    participant Source as Sources Externes
    participant Ingest as Ingestion Airflow
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

### Structure du code

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
            M9[dags/<br/>DAGs Airflow]
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
    end
    
    style M1 fill:#e1f5ff
    style M9 fill:#fff4e1
    style S1 fill:#e8f5e9
    style SVC1 fill:#fce4ec
```

### Différenciation par configuration

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

### Flux de données d'entraînement

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
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

### Flux de données d'inférence

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

### Mapping Objectifs → Implémentation

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
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
        I2[FastAPI REST API<br/>+ Streamlit UI]
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

### Résumé des Flows Principaux

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
mindmap
  root((DAGs Airflow))
    prediction
      prediction_full_pipeline
      prediction_inference_only_pipeline
      prediction_batch_pipeline
    training
      consumption_flow
      solar_production_flow
    data_ingestion
      weather_flow
      holidays_flow
      sftp_ingestion_flow
    monitoring
      actual_values_flow
      drift_detection_flow
```

### Services déployés

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
mindmap
  root((Services))
    MLOps_Core
      MLflow
      Airflow
    Inference
      FastAPI
      Streamlit
    Monitoring
      Evidently_AI
      Grafana
    Storage
      PostgreSQL
      S3
    Notification
      Resend_Email
```
