# Monitoring et Drift Detection

## Vue d'ensemble

Le monitoring utilise Evidently AI pour détecter le drift des données et des prédictions, avec alertes automatiques et triggering de retraining.

## Architecture de monitoring

```mermaid
graph LR
    subgraph "Data Store - S3"
        A[Reference<br/>Dataset]
        B[Prepared<br/>Dataset]
    end
    subgraph "Artifacts - S3"
        Ev[Evidently<br/>Reports]
        ML[MLflow<br/>Metrics]
    end

    subgraph "AirFlow"
        C[Monitoring<br/>Pipeline]
        
    end
    
    subgraph "Monitoring"
        D[MLFlow<br/>Server]
        EU[EvidentlyUI<br/>Server]
        F[Email<br/>Resend]
        R[Retraining<br/>Trigger]
    end
    
    A --> C
    B --> C
    C --> Ev
    C --> ML
    C --> |Drift Detected| R
    C --> |Drift Detected| F

    Ev --> EU

    ML --> D
    
    style C fill:#fce4ec
    style F fill:#ffcccb
    style R fill:#ffcccb
```


## Drifts détectés

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
