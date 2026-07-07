# Pipeline d'Ingestion des Données

## Vue d'ensemble

Le pipeline d'ingestion met à jour les prédictions avec les valeurs réelles observées depuis différentes sources externes. Il comprend :

1. **Ingestion des valeurs réelles** : Met à jour les prédictions avec les valeurs observées
2. **Connecteur SFTP** : Récupère les données de consommation brutes depuis un serveur SFTP

## Flux d'Ingestion

```mermaid
graph LR
    subgraph "Sources Externes"
        S1[SFTP<br/>CSV PRM]
    end

    subgraph "Connecteurs"
        C1[SFTPConnector]
    end

    subgraph "Pipelines"
        P1[IngestionPipeline<br/>Valeurs Réelles]
    end

    subgraph "Stockage"
        ST1[PostgreSQL<br/>Table predictions]
    end

    S1 --> C1
    C1 --> P1
    P1 --> ST1

    style S1 fill:#e1f5ff
    style C1 fill:#fce4ec
    style P1 fill:#d1c4e9
    style ST1 fill:#ffccbc
```


## Pipeline d'Ingestion des Valeurs Réelles

### Vue d'ensemble

Le pipeline `IngestionPipeline` met à jour quotidiennement les prédictions avec les valeurs réelles observées. Il est exécuté via le script `pipelines/run_ingestion.py`.

### Étapes du Pipeline

1. **Configuration** (`setup`) : Initialise la connexion à la base de données PostgreSQL
2. **Récupération des prédictions** (`get_previous_day_predictions`) : Récupère les prédictions de la veille
3. **Génération des valeurs réelles** (`generate_random_actual_values`) :
   - Si SFTP activé : Tente l'ingestion SFTP
   - Sinon : Génère des valeurs aléatoires (±20% autour de la prédiction)
   - Si aucune prédiction : Insère des enregistrements complets
4. **Vérification** (`verify_updates`) : Vérifie que les valeurs ont été mises à jour

### Exécution

```bash
# Exécution avec configuration par défaut
python pipelines/run_ingestion.py

# Exécution avec URI de base de données explicite
python pipelines/run_ingestion.py --db_uri postgresql://user:password@host:port/database

# Exécution avec configuration depuis variables d'environnement
python pipelines/run_ingestion.py --use_env_config
```

### Variables d'environnement

- `PREDICTIONS_POSTGRES_URI` : URI de connexion PostgreSQL (priorité sur config)

### Configuration

Dans le fichier de configuration (`consumption.{dev,prod,test}.yaml`) :

```yaml
sftp:
  enabled: false  # Active/désactive l'ingestion SFTP
  use_env_config: false  # Utilise les variables d'environnement pour SFTP
  host: "sftp.example.com"
  username: "user"
  ssh_private_key_b64: "..."
  remote_directory: "/data/incoming"
  archive_directory: "/data/archived"
```

## Connecteur SFTP

**Fichier** : `src/ml/connectors/sftp/sftp_connector.py`

**Classe** : `SFTPConnector`

**Fonctionnalités** :
- Connexion SFTP avec authentification par clé SSH et passphrase
- Téléchargement de fichiers (individuel ou répertoire complet)
- Archivage des fichiers traités
- Support des formats RSA, ECDSA, Ed25519, DSS

**Exemple d'utilisation** :

```python
from ml.connectors.sftp.sftp_connector import SFTPConnector

connector = SFTPConnector(
    host="sftp.example.com",
    username="user",
    ssh_private_key_b64="<BASE64_ENCODED_KEY>",
    passphrase="your_passphrase"
)

# Télécharger un fichier
connector.download_file("/remote/file.csv", "/local/file.csv")

# Archiver un fichier
connector.archive_file("/remote/file.csv", "/archived/")
```

> **Note** : Les connecteurs Weather API et Holidays API sont utilisés dans le **Preparation Pipeline**, pas dans le pipeline d'ingestion.



## Stockage

### Base de données PostgreSQL

**Table** : `predictions`

**Colonnes principales** :
- `prediction_id` : Identifiant unique
- `target_timestamp` : Timestamp de la prédiction
- `prediction` : Valeur prédite
- `actual_value` : Valeur réelle (mise à jour par ingestion)
- `entity_id` : Identifiant de l'entité

### Fichiers Parquet

**Emplacement** : `data/processed/`

**Fichiers générés** :
- `weather_{location}_{start}_{end}.parquet` : Données météo
- `{start}_to_{end}_holidays.parquet` : Données vacances/jours fériés
- `{start}_to_{end}_train.parquet` : Données d'entraînement
- `{start}_to_{end}_consumption.parquet` : Données de consommation
