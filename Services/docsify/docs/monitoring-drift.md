# Monitoring et Drift Detection

## Vue d'ensemble

Le monitoring utilise Evidently AI pour détecter le drift des données et des prédictions, avec alertes automatiques et triggering de retraining.

## Architecture de monitoring

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
graph LR
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

## Pipeline de détection de drift

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
graph LR
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
    K --> L[Trigger Retraining<br/>Airflow DAG]
    L --> M[Nouveau Modèle]
    M --> N[Promotion Production]
    N --> H
    
    style C fill:#e1f5ff
    style F fill:#fce4ec
    style G fill:#fff4e1
    style K fill:#ffcccb
    style M fill:#e8f5e9
```

## Métriques monitoring et seuils

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
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

## Types de Drift

### Data Drift
- **Définition**: Changement dans la distribution des features d'entrée
- **Détection**: Test Kolmogorov-Smirnov, PSI
- **Action**: Rejet des prédictions si drift sévère

### Concept Drift
- **Définition**: Changement dans la relation features/target
- **Détection**: Comparaison des distributions de prédictions
- **Action**: Trigger retraining automatique

### Prediction Drift
- **Définition**: Changement dans la distribution des prédictions
- **Détection**: Analyse des résidus
- **Action**: Monitoring accru, alertes
