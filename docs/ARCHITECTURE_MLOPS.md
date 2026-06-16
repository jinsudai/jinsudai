# Documentation Architecture MLOps - Jinsudai

## Vue d'ensemble

Ce document présente l'architecture MLOps complète du projet de prédiction énergétique, illustrée avec des diagrammes Mermaid. L'architecture est conçue pour respecter le cahier des charges et répondre aux objectifs suivants :

- **Création d'algorithmes IA** adaptés aux données d'entraînement et conformes aux spécifications
- **Adaptation de l'infrastructure de données** à travers la construction d'API pour accueillir la solution en production
- **Conception de pipelines CI/CD** pour automatiser le déploiement
- **Développement de scripts de réentraînement** pour automatiser le Machine Learning
- **Pilotage de la performance** via des outils de monitoring (Evidently) pour assurer le respect des spécifications en production

---

## 1. Architecture Globale

### 1.1 Vue d'ensemble des composants

```mermaid
graph TB
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

### 1.2 Architecture détaillée des services

```mermaid
graph TB
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

---

## 2. Flux de Données

### 2.1 Pipeline de données complet

```mermaid
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
```

### 2.2 Flux de données d'entraînement

```mermaid
flowchart TD
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

### 2.3 Flux de données d'inférence

```mermaid
flowchart TD
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

---

## 3. Pipeline d'Entraînement

### 3.1 Workflow Prefect d'entraînement

```mermaid
flowchart TD
    subgraph "Consumption Flow"
        A1[setup_training_task<br/>Config MLflow + DB] --> A2[load_data_task<br/>Chargement CSV]
        A2 --> A3[validate_data_task<br/>Validation schéma]
        A3 --> A4[prepare_data_task<br/>Nettoyage + Features]
        A4 --> A5[train_model_task<br/>AutoGluon Training]
        A5 --> A6[evaluate_model_task<br/>Métriques R², MAE]
        A6 --> A7[log_to_mlflow_task<br/>Log artefacts]
        A7 --> A8[promote_to_prod_task<br/>Alias prod]
    end
    
    subgraph "Solar Production Flow"
        B1[setup_training_task] --> B2[load_data_task]
        B2 --> B3[validate_data_task]
        B3 --> B4[prepare_data_task<br/>+ Irradiance]
        B4 --> B5[train_model_task]
        B5 --> B6[evaluate_model_task<br/>R² >= 0.92]
        B6 --> B7[log_to_mlflow_task]
        B7 --> B8[promote_to_prod_task]
    end
    
    style A1 fill:#e1f5ff
    style A5 fill:#fff4e1
    style A7 fill:#d1c4e9
    style B5 fill:#fff4e1
    style B7 fill:#d1c4e9
```

### 3.2 Pipeline d'entraînement détaillé

```mermaid
graph LR
    subgraph "Phase 1: Préparation"
        P1[Chargement Config] --> P2[Connexion MLflow]
        P2 --> P3[Chargement Données]
        P3 --> P4[Validation]
        P4 --> P5[Nettoyage]
        P5 --> P6[Feature Engineering]
    end
    
    subgraph "Phase 2: Training"
        P6 --> T1[Split Train/Test]
        T1 --> T2[AutoGluon Fit]
        T2 --> T3[Hyperparameter Tuning]
        T3 --> T4[Best Model Selection]
    end
    
    subgraph "Phase 3: Évaluation"
        T4 --> E1[Calcul Métriques]
        E1 --> E2[R² >= 0.90?]
        E2 -->|Oui| E3[Validation OK]
        E2 -->|Non| E4[Retrying]
    end
    
    subgraph "Phase 4: Déploiement"
        E3 --> D1[Log MLflow]
        D1 --> D2[Save Model]
        D2 --> D3[Register Model]
        D3 --> D4[Promote to Prod]
    end
    
    style P1 fill:#e1f5ff
    style T2 fill:#fff4e1
    style E2 fill:#fce4ec
    style D4 fill:#e8f5e9
```

---

## 4. Pipeline d'Inférence

### 4.1 Workflow Prefect de prédiction

```mermaid
flowchart TD
    subgraph "Prediction Full Pipeline"
        A[setup_prediction_task<br/>Config MLflow + DB] --> B[load_model_task<br/>Modèle prod]
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

### 4.2 Variants de pipelines d'inférence

```mermaid
graph TB
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

---

## 5. Pipeline CI/CD

### 5.1 Pipeline GitHub Actions

```mermaid
flowchart TD
    A[Push sur main] --> B[GitHub Actions Trigger]
    B --> C[Linting & Tests]
    C --> D{Tests OK?}
    D -->|Non| E[Échec CI]
    D -->|Oui| F[Build Docker Images]
    F --> G[Push Registry]
    G --> H[Deploy MLflow]
    H --> I[Deploy FastAPI]
    I --> J[Deploy Evidently]
    J --> K[Deploy Grafana]
    K --> L[Deploy Prefect]
    L --> M[Integration Tests]
    M --> N{Integration OK?}
    N -->|Non| E
    N -->|Oui| O[Deploy Production]
    O --> P[Health Checks]
    P --> Q[Notification Success]
    
    style C fill:#e1f5ff
    style F fill:#fff4e1
    style M fill:#fce4ec
    style O fill:#e8f5e9
```

### 5.2 Workflow de déploiement

```mermaid
sequenceDiagram
    participant Dev as Développeur
    participant GH as GitHub
    participant HF as Hugging Face
    participant MLflow as MLflow Service
    participant API as FastAPI
    participant Mon as Monitoring
    
    Dev->>GH: Push code + tag
    GH->>GH: CI/CD Pipeline
    GH->>HF: Deploy MLflow Space
    HF-->>GH: URL MLflow
    GH->>HF: Deploy FastAPI Space
    HF-->>GH: URL API
    GH->>HF: Deploy Evidently Space
    HF-->>GH: URL Evidently
    GH->>MLflow: Health Check
    MLflow-->>GH: 200 OK
    GH->>API: Health Check
    API-->>GH: 200 OK
    GH->>Mon: Configure Dashboards
    Mon-->>GH: Ready
    GH-->>Dev: Deployment Success
```

---

## 6. Monitoring et Drift Detection

### 6.1 Architecture de monitoring

```mermaid
graph TB
    subgraph "Production"
        A[FastAPI<br/>Prédictions]
        B[PostgreSQL<br/>Historique]
    end
    
    subgraph "Monitoring"
        C[Evidently AI<br/>Drift Detection]
        D[Grafana<br/>Dashboards]
        E[MLflow<br/>Métriques]
    end
    
    subgraph "Alerting"
        F[Email Resend<br/>Notifications]
        G[Slack/Webhook<br/>Alertes]
    end
    
    A --> B
    B --> C
    C --> D
    C --> E
    C --> F
    D --> G
    
    style C fill:#fce4ec
    style D fill:#fff4e1
    style E fill:#e1f5ff
    style F fill:#ffcccb
```

### 6.2 Pipeline de détection de drift

```mermaid
flowchart TD
    A[Données Production<br/>PostgreSQL] --> B[Chargement Référence<br/>Training Data]
    B --> C[Comparaison Distributions<br/>Data Drift]
    C --> D[Comparaison Prédictions<br/>Concept Drift]
    D --> E[Calcul PSI<br/>Population Stability Index]
    E --> F{Drift > Seuil?}
    F -->|Oui| G[Génération Rapport<br/>Evidently]
    F -->|Non| H[Monitoring Continu]
    G --> I[Sauvegarde MLflow<br/>Artefact]
    I --> J[Sauvegarde Workspace<br/>Evidently UI]
    J --> K[Alerte Email<br/>Resend]
    K --> L[Trigger Retraining<br/>Prefect Flow]
    L --> M[Nouveau Modèle]
    M --> N[Promotion Production]
    N --> H
    
    style C fill:#e1f5ff
    style F fill:#fce4ec
    style G fill:#fff4e1
    style K fill:#ffcccb
    style M fill:#e8f5e9
```

### 6.3 Métriques monitoring et seuils

```mermaid
graph LR
    subgraph "Consommation Électrique"
        C1[R² >= 0.90] --> C2[MAE Monitoring]
        C2 --> C3[RMSE Monitoring]
        C3 --> C4[Inference < 100ms]
        C4 --> C5{R² < 0.88?}
        C5 -->|Oui| C6[⚠️ Warning]
        C5 -->|Non| C7[OK]
        C6 --> C8{R² < 0.85?}
        C8 -->|Oui| C9[🔴 Critical<br/>Retraining Immédiat]
    end
    
    subgraph "Production Solaire"
        S1[R² >= 0.92] --> S2[MAE Monitoring]
        S2 --> S3[RMSE Monitoring]
        S3 --> S4[Inference < 100ms]
        S4 --> S5{R² < 0.90?}
        S5 -->|Oui| S6[⚠️ Warning]
        S5 -->|Non| S7[OK]
        S6 --> S8{R² < 0.88?}
        S8 -->|Oui| S9[🔴 Critical<br/>Retraining Immédiat]
    end
    
    style C1 fill:#e8f5e9
    style C5 fill:#fff4e1
    style C9 fill:#ffcccb
    style S1 fill:#e8f5e9
    style S5 fill:#fff4e1
    style S9 fill:#ffcccb
```

---

## 7. Automatisation du Retraining

### 7.1 Triggers de retraining

```mermaid
flowchart TD
    subgraph "Triggers Automatiques"
        A1[Drift Détecté<br/>R² < Seuil] --> D[Trigger Retraining]
        A2[Cycle Hebdo<br/>7 jours] --> D
        A3[Données Nouvelles<br/>>= 1000 exemples] --> D
    end
    
    subgraph "Triggers Manuels"
        B1[API Trigger] --> D
        B2[CLI Command] --> D
        B3[Airflow DAG] --> D
    end
    
    subgraph "Conditions Préalables"
        C1[Données suffisantes] --> E{Conditions OK?}
        C2[Performance baseline] --> E
        C3[R² nouveaux >= R² courant] --> E
    end
    
    D --> E
    E -->|Oui| F[Lancement Training]
    E -->|Non| G[Annulation]
    
    F --> H[Évaluation Nouveau Modèle]
    H --> I{Amélioration?}
    I -->|Oui| J[Promotion Production]
    I -->|Non| K[Conserve Ancien]
    
    style A1 fill:#ffcccb
    style A2 fill:#fff4e1
    style A3 fill:#fff4e1
    style E fill:#fce4ec
    style J fill:#e8f5e9
```

### 7.2 Workflow de retraining automatisé

```mermaid
sequenceDiagram
    participant Monitor as Evidently
    participant Trigger as Prefect Trigger
    participant Train as Training Flow
    participant MLflow as MLflow
    participant Eval as Evaluation
    participant Prod as Production
    
    Monitor->>Monitor: Détection Drift
    Monitor->>Trigger: Signal Retraining
    Trigger->>Train: Lancement Flow
    Train->>Train: Chargement Données
    Train->>Train: Training AutoGluon
    Train->>MLflow: Log Nouveau Modèle
    MLflow-->>Train: Model URI
    Train->>Eval: Évaluation
    Eval->>Eval: Comparaison Baseline
    Eval-->>Train: Résultats
    Train->>Train: Décision Promotion
    Train->>MLflow: Promotion Prod
    MLflow-->>Prod: Nouveau Modèle
    Prod->>Prod: Déploiement
    Prod-->>Monitor: Monitoring Continu
    
    style Monitor fill:#fce4ec
    style Train fill:#fff4e1
    style MLflow fill:#e1f5ff
    style Prod fill:#e8f5e9
```

---

## 8. Structure du Code

### 8.1 Organisation des modules

```mermaid
graph TB
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

### 8.2 Différenciation par configuration

```mermaid
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

---

## 9. Conformité au Cahier des Charges

### 9.1 Mapping Objectifs → Implémentation

```mermaid
graph TB
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
        I4[Prefect Flows<br/>+ Drift Detection]
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

### 9.2 Spécifications techniques respectées

| Spécification | Implémentation | Statut |
|---------------|----------------|--------|
| **Algorithmes IA** | AutoGluon (regression) pour consommation et production solaire | ✅ |
| **Métriques** | R² >= 0.90 (consommation), R² >= 0.92 (solaire) | ✅ |
| **Temps inférence** | < 100ms par requête (FastAPI) | ✅ |
| **API Production** | FastAPI avec endpoints /predict et /predict/batch | ✅ |
| **CI/CD** | GitHub Actions avec Docker + Hugging Face Spaces | ✅ |
| **Réentraînement auto** | Prefect flows avec triggers drift + cycle hebdo | ✅ |
| **Monitoring** | Evidently AI + Grafana dashboards | ✅ |
| **Alertes** | Email via Resend + Slack webhooks | ✅ |
| **Stockage modèles** | MLflow Model Registry avec promotion prod | ✅ |
| **Données** | PostgreSQL pour prédictions, S3 pour artefacts | ✅ |

---

## 10. Résumé des Flows Principaux

### 10.1 Flows Prefect disponibles

```mermaid
mindmap
  root((Flows Prefect))
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

### 10.2 Services déployés

```mermaid
mindmap
  root((Services))
    MLOps_Core
      MLflow
      Prefect
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

---

## Conclusion

Cette architecture MLOps complète respecte l'intégralité du cahier des charges en :

1. **Créant des algorithmes IA adaptés** : AutoGluon avec configurations spécifiques par domaine (consommation, production solaire)
2. **Adaptant l'infrastructure** : API FastAPI pour production, avec UI Streamlit pour accessibilité
3. **Concevant des pipelines CI/CD** : GitHub Actions automatisant le déploiement sur Hugging Face Spaces
4. **Développant des scripts de réentraînement** : Flows Prefect avec triggers automatiques (drift, cycle hebdo)
5. **Pilotant la performance** : Evidently AI pour drift detection + Grafana pour monitoring continu

L'architecture est modulaire, scalable et conforme aux meilleures pratiques MLOps, avec une séparation claire des responsabilités entre les différents services.
