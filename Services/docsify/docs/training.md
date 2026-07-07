# Pipeline d'Entraînement

## Vue d'ensemble

Le pipeline d'entraînement prépare les données, entraîne les modèles avec AutoGluon, et déploie les meilleurs modèles en production via MLflow.

## Flux de données

```mermaid
graph LR
    A[Prepared<br/>train.parquet<br/>S3] --> C[Training]
    C --> E{Évaluation & Logging<br/>Promotion Production?}
    E -->|Oui| F[Alias 'prod']
    F --> H[Trained<br/>train.parquet<br/>S3]

    style A fill:#e1f5ff
    style B fill:#f8bbd9
    style C fill:#fff9c4
    style D fill:#fff9c4
    style E fill:#c8e6c9
```

### Cycle Préparation → Training → Archivage

1. **Preparation Pipeline** génère des features et upload vers `consumption/prepared/`
2. **Training Pipeline** télécharge depuis `consumption/prepared/` et entraîne le modèle
3. **Training Pipeline** upload vers `consumption/trained/` après entraînement
4. Les anciens fichiers sont archivés dans `consumption/archived/prepared/` et `consumption/archived/trained/`

## Flux de données d'entraînement détaillé

```mermaid
graph TD
    subgraph "Étape 1: Chargement"
        A[Données train.parquet<br/>local ou S3] --> B[Data Loading<br/>step_1_load_data]
        B -->|Fichier absent| C[Download S3<br/>consumption/prepared/]
        C --> B
    end

    B --> D[Data Validation<br/>step_2_validate_data]
    D --> E[Rapport Evidently<br/>Qualité des données]

    E --> F[Data Transformation<br/>step_3_transform_data<br/>Nettoyage colonnes]

    F --> G[Data Preparation<br/>step_3_prepare_data]
    G --> G1[Split Train/Test<br/>80/20]
    G1 --> G2[Prétraitement<br/>Imputation/Scaling/Encoding]

    G2 --> H[Model Training<br/>step_4_train_model<br/>AutoGluon/RandomForest]

    H --> I[Model Evaluation<br/>step_5_evaluate_model<br/>R², MAE, RMSE]

    I --> J[Performance Monitoring<br/>step_6_monitor_performance<br/>Drift Detection]

    J --> K[MLflow Logging<br/>step_7_log_with_mlflow<br/>Métriques + Artefacts]

    K --> L[Model Stage Management<br/>step_9_manage_model_stages]
    L --> L1[Enregistrement Staging]
    L1 --> L2{Promotion Production?}
    L2 -->|Oui| L3[Alias 'prod'<br/>Meilleures métriques]
    L2 -->|Non| L4[Reste en Staging]

    L3 --> M[Upload Data S3<br/>step_8_upload_trained_data_to_s3<br/>consumption/trained/]
    M --> M1[Archivage anciens fichiers<br/>consumption/archived/trained/]

    L4 --> M

    M1 --> N[Cleanup Model<br/>step_8_cleanup_model<br/>Suppression locale]

    style B fill:#e1f5ff
    style D fill:#fff9c4
    style F fill:#ffe0b2
    style G fill:#c8e6c9
    style H fill:#f8bbd9
    style I fill:#e1bee7
    style J fill:#b2dfdb
    style K fill:#d1c4e9
    style L fill:#ffccbc
    style M fill:#c5cae9
```


