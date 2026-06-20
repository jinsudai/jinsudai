# Pipeline d'Ingestion des Données

## Vue d'ensemble

Le pipeline d'ingestion collecte les données depuis différentes sources externes et les prépare pour le traitement.

## Sources de Données

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
graph LR
    A[Données BRUT<br/>CSV PRM] --> D[Prefect Server]
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
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#e1f5ff', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#0ea5e9', 'lineColor': '#64748b', 'secondaryColor': '#fff4e1', 'tertiaryColor': '#fce4ec', 'background': '#1e293b', 'mainBkg': '#e1f5ff', 'nodeBorder': '#0ea5e9', 'clusterBkg': '#334155', 'clusterBorder': '#475569', 'titleColor': '#f8fafc', 'edgeLabelBackground': '#1e293b'}}}%%
graph LR
    subgraph "Sources Externes"
        S1[CSV PRM]
        S2[API Météo]
        S3[API Vacances]
    end
    
    subgraph "Orchestration Prefect"
        O1[weather_flow]
        O2[holidays_flow]
        O3[sftp_ingestion_flow]
    end
    
    subgraph "Validation"
        V1[Schéma]
        V2[Valeurs]
    end
    
    subgraph "Stockage"
        ST1[data/raw/]
        ST2[data/processed/]
    end
    
    S1 --> O3
    S2 --> O1
    S3 --> O2
    O1 --> V1
    O2 --> V1
    O3 --> V1
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

## Workflows Prefect

### weather_flow
- **Source**: API Open-Meteo
- **Fréquence**: Quotidienne
- **Output**: Données météorologiques (température, humidité, précipitations)

### holidays_flow
- **Source**: API vacances
- **Fréquence**: Mensuelle
- **Output**: Calendrier des jours fériés

### sftp_ingestion_flow
- **Source**: SFTP (CSV PRM)
- **Fréquence**: Quotidienne
- **Output**: Données de consommation brutes
