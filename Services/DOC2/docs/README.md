# Documentation MLOps - Jinsudai

Bienvenue dans la documentation complète de l'architecture MLOps du projet de prédiction énergétique.

## Vue d'ensemble

Ce projet implémente une architecture MLOps complète pour la prédiction de consommation énergétique et de production solaire, respectant les objectifs suivants :

- **Création d'algorithmes IA** adaptés aux données d'entraînement et conformes aux spécifications
- **Adaptation de l'infrastructure de données** à travers la construction d'API pour accueillir la solution en production
- **Conception de pipelines CI/CD** pour automatiser le déploiement
- **Développement de scripts de réentraînement** pour automatiser le Machine Learning
- **Pilotage de la performance** via des outils de monitoring (Evidently) pour assurer le respect des spécifications en production

## Navigation

Utilisez le menu de gauche pour naviguer entre les différents pipelines et composants de l'architecture.

## Architecture Globale

Cette section présente une vue d'ensemble de l'architecture MLOps avec les sources de données, l'orchestration, le ML & Tracking, l'API & Inference, le Monitoring et le Stockage.

---

## Diagramme

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
