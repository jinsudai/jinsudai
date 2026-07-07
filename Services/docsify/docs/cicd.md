# Pipeline CI/CD

## Vue d'ensemble

Le pipeline CI/CD automatise le build, le test, et le déploiement des services sur Hugging Face Spaces via GitHub Actions.

## Pipeline GitHub Actions

```mermaid
graph LR
    A[Push to main/develop] --> B[CI Workflow Trigger]
    B --> C[Test Job]
    B --> D[Validate Configs Job]
    C --> E{Tests OK?}
    D --> E
    E -->|No| F[CI Failure]
    E -->|Yes| G[CD Workflow Trigger]
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
    participant Dev as Developer
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

## Services déployés

### MLflow
- **Backend**: PostgreSQL
- **Storage**: S3 pour artefacts
- **Health Check**: `/health`
- **URL**: https://jinsudai-mlflow.hf.space/

### FastAPI (JinsudAPI)
- **Endpoints**: `/predict`, `/predict/batch`, `/health`
- **Health Check**: `/health`
- **URL**: https://jetestai-jinsudapi.hf.space/

### EvidentlyUI
- **Workspace**: Rapports drift
- **Health Check**: `/health`
- **URL**: https://evidentlai-evidentlyui.hf.space/

### Airflow
- **Components**: Webserver, Scheduler, Worker
- **Health Check**: `/health`
- **URL**: https://airflai-airflow.hf.space/
