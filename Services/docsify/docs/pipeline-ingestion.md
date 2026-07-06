# Pipeline d'Ingestion des Données

## Vue d'ensemble

Le pipeline d'ingestion collecte les données depuis différentes sources externes et les prépare pour le traitement.

## Sources de Données

```mermaid
graph LR
    A[Données BRUT<br/>CSV PRM] --> D[Airflow]
    B[Données Météo<br/>API Open-Meteo] --> D
    C[Données Vacances<br/>API] --> D
    D --> E[Validation]
    E --> F[Stockage<br/>PostgreSQL]

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#e8f5e9
    style D fill:#fce4ec
    style F fill:#d1c4e9
```

## Flux d'Ingestion

```mermaid
graph LR
    subgraph "Sources Externes"
        S1[CSV PRM]
        S2[API Météo]
        S3[API Vacances]
    end

    subgraph "Orchestration Airflow"
        O1[sftp_ingestion_pipeline]
        O2[weather_pipeline]
        O3[holidays_pipeline]
        O4[actuals_ingestion_pipeline]
    end

    subgraph "Validation"
        V1[Schéma]
        V2[Valeurs]
    end

    subgraph "Stockage"
        ST1[data/raw/]
        ST2[data/processed/]
    end

    S1 --> O1
    S2 --> O2
    S3 --> O3
    O1 --> V1
    O4 --> V1
    V1 --> V2
    V2 --> ST1
    ST1 --> ST2

    style S1 fill:#e1f5ff
    style S2 fill:#fff4e1
    style S3 fill:#e8f5e9
    style O1 fill:#fce4ec
    style V1 fill:#d1c4e9
    style ST2 fill:#ffcccb
```

## DAGs Airflow

### sftp_ingestion_pipeline
- **Source**: SFTP (CSV PRM)
- **Fréquence**: Quotidienne
- **Output**: Données de consommation brutes

### weather_pipeline
- **Source**: API Open-Meteo
- **Fréquence**: Quotidienne
- **Output**: Données météorologiques

### holidays_pipeline
- **Source**: API vacances
- **Fréquence**: Mensuelle
- **Output**: Calendrier des vacances

### actuals_ingestion_pipeline
- **Source**: API valeurs réelles
- **Fréquence**: Quotidienne
- **Output**: Données de valeurs réelles pour monitoring
