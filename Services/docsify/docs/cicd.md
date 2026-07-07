# Pipeline CI/CD

## Vue d'ensemble

Le pipeline CI/CD automatise le build, le test, et le déploiement des services sur Hugging Face Spaces via GitHub Actions.

## Pipeline GitHub Actions

```mermaid
graph LR
    A[Push sur main/develop] --> B[CI Workflow Trigger]
    B --> C[Test Job]
    B --> D[Validate Configs Job]
    C --> E{Tests OK?}
    D --> E
    E -->|Non| F[Échec CI]
    E -->|Oui| G[CD Workflow Trigger]
    G --> H[Filter Job]
    H --> I{Path Changes?}
    I -->|createSpaces| J[HF Create Spaces]
    I -->|pushServices| K[HF Push Services]
    I -->|updateSecrets| L[HF Update Secrets]
    I -->|buildFastApi| M[Build FastAPI Docker]
    M --> N[Push to GHCR]
    N --> O[Deploy FastAPI]
    J --> P[Notification Success]
    K --> P
    L --> P
    O --> P

    style C fill:#e1f5ff
    style D fill:#e1f5ff
    style H fill:#fff4e1
    style M fill:#fff4e1
    style P fill:#e8f5e9
```

## Workflow de déploiement

```mermaid
sequenceDiagram
    participant Dev as Développeur
    participant CI as CI Workflow
    participant CD as CD Workflow
    participant Filter as Filter Job
    participant HF as Hugging Face
    participant GHCR as GitHub Container Registry
    participant API as FastAPI Service
    
    Dev->>CI: Push code (main/develop)
    CI->>CI: Run Tests & Validate Configs
    CI->>CD: Trigger on success
    CD->>Filter: Check path changes
    Filter->>Filter: Determine jobs to run
    
    alt createSpaces changed
        Filter->>HF: Create Spaces
        HF-->>Filter: Spaces created
    end
    
    alt pushServices changed
        Filter->>HF: Push Services
        HF-->>Filter: Services pushed
    end
    
    alt updateSecrets changed
        Filter->>HF: Update Secrets
        HF-->>Filter: Secrets updated
    end
    
    alt buildFastApi changed
        Filter->>GHCR: Build Docker Image
        GHCR-->>Filter: Image pushed
        Filter->>API: Deploy FastAPI
        API-->>Filter: Deployment ready
    end
    
    CD-->>Dev: Deployment Success
```

## Services déployés (A déplacer?)

### MLflow
- **Port**: 7860
- **Backend**: PostgreSQL
- **Storage**: S3 pour artefacts
- **Health Check**: `/health`

### FastAPI
- **Port**: 8000
- **Endpoints**: `/predict`, `/predict/batch`, `/health`
- **Health Check**: `/health`

### Evidently AI
- **Port**: 8501
- **Workspace**: Rapports drift
- **Health Check**: `/health`

### Grafana
- **Port**: 3000
- **Dashboards**: Monitoring ML
- **Health Check**: `/api/health`

### Airflow
- **Port**: 8080
- **Components**: Webserver, Scheduler, Worker
- **Health Check**: `/health`
