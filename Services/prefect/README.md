---
title: Prefect
emoji: 📊
colorFrom: pink
colorTo: indigo
sdk: docker
pinned: false
---



# Prefect - Documentation de démarrage local

Ce service contient la configuration et la documentation pour lancer Prefect en local.

## 🚀 Démarrage rapide

### Prérequis

- Python 3.11+
- Docker (optionnel, pour le mode container)
- Les dépendances du projet installées via Poetry

### 1. Installation des dépendances

```bash
# Depuis la racine du projet
poetry install
```

### 2. Démarrage du serveur Prefect

#### Option A: Mode local (recommandé pour le développement)

```bash
# Activer l'environnement virtuel
poetry shell

# Démarrer le serveur Prefect
prefect server start
```

Le serveur sera accessible sur: http://localhost:4200

#### Option B: Mode Docker

```bash
# Construire et démarrer le container
docker build -t prefect-server Services/prefect/
docker run -p 4200:4200 prefect-server
```

### 3. Configuration de l'API Prefect

```bash
# Configurer le client pour pointer vers le serveur local
prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api
```

### 4. Déploiement des flows

Les flows sont définis dans `src/ml/workflows/`. Pour les déployer:

```bash
# Déployer tous les flows de prédiction
python scripts/deploy_prediction_flows.py

# Déployer les flows avec scheduling
python scripts/deploy_prediction_schedule.py

# Déployer les flows weather
python scripts/deploy_weather_schedule.py
```

### 5. Démarrage d'un worker Prefect

Le worker exécute les flows déployés:

```bash
# Démarrer un worker avec le pool par défaut
prefect worker start --pool default-pool
```

## 📋 Flows disponibles

Le projet contient les flows suivants:

| Flow | Fichier | Description |
|------|---------|-------------|
| `consumption_full_pipeline` | `src/ml/workflows/consumption_flow.py` | Pipeline complet d'entraînement consommation |
| `prediction_full_pipeline` | `src/ml/workflows/prediction_flow.py` | Pipeline de prédiction complet |
| `prediction_inference_only_pipeline` | `src/ml/workflows/prediction_flow.py` | Pipeline d'inférence uniquement |
| `prediction_batch_pipeline` | `src/ml/workflows/prediction_flow.py` | Pipeline de prédiction par batch |
| `sftp_ingestion_pipeline` | `src/ml/workflows/sftp_ingestion_flow.py` | Pipeline d'ingestion SFTP |
| `holidays_annual_pipeline` | `src/ml/workflows/holidays_flow.py` | Pipeline annuel des vacances |
| `actual_values_full_pipeline` | `src/ml/workflows/actual_values_flow.py` | Pipeline des valeurs réelles |
| `weather_flow` | `src/ml/workflows/weather_flow.py` | Pipeline des données météo |

## 🔧 Configuration

### Configuration des schedules

Les schedules sont définis dans `src/configs/flows.yaml`:

```yaml
flows:
  training:
    enabled: true
    schedule:
      cron: "0 2 * * 0"  # Tous les dimanches à 2h
      timezone: "Europe/Paris"
```

### Variables d'environnement

Créez un fichier `.env` à la racine du projet (voir `.env.example`):

```bash
# Configuration Prefect
PREFECT_API_URL=http://127.0.0.1:4200/api
PREFECT_UI_API_URL=/api

# Configuration MLflow
MLFLOW_TRACKING_URI=http://localhost:5000
```

## 📊 Utilisation de l'UI Prefect

Une fois le serveur démarré, accédez à:
- **UI Prefect**: http://localhost:4200
- **API**: http://localhost:4200/api

Depuis l'UI, vous pouvez:
- Voir l'état des flows
- Lancer des flows manuellement
- Voir les logs et l'historique
- Configurer les schedules

## 🛠️ Commandes utiles

```bash
# Voir les flows déployés
prefect deployment ls

# Lancer un flow manuellement
prefect deployment run <deployment-name>

# Voir l'état des workers
prefect worker ls

# Voir les logs d'un run
prefect work-queue logs

# Arrêter le serveur (Ctrl+C)
```

## 🐛 Dépannage

### Le serveur ne démarre pas

```bash
# Vérifier que le port 4200 est libre
netstat -ano | findstr :4200

# Changer le port si nécessaire
prefect server start --port 4300
```

### Les flows ne s'exécutent pas

```bash
# Vérifier que le worker est actif
prefect worker ls

# Redémarrer le worker
prefect worker start --pool default-pool
```

### Erreur de connexion à l'API

```bash
# Reconfigurer l'URL de l'API
prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api
```

## 📚 Ressources

- [Documentation Prefect](https://docs.prefect.io/)
- [Flows du projet](../src/ml/workflows/)
- [Configuration des flows](../src/configs/flows.yaml)
