# Guide d'Utilisation - Evidently UI

Guide complet pour utiliser l'interface native d'EvidentlyAI pour visualiser les rapports de monitoring ML.

## 📋 Table des matières

1. [Premiers pas](#premiers-pas)
2. [Démarrage du service](#démarrage-du-service)
3. [Configuration du pipeline](#configuration-du-pipeline)
4. [Utilisation de l'interface](#utilisation-de-linterface)
5. [Fonctionnalités avancées](#fonctionnalités-avancées)
6. [Intégration avec MLflow](#intégration-avec-mlflow)
7. [Bonnes pratiques](#bonnes-pratiques)
8. [Dépannage](#dépannage)

---

## Premiers pas

### Prérequis

- Python 3.11+
- Docker (optionnel, recommandé)
- Accès au workspace Evidently (local ou distant)

### Architecture

```
┌─────────────────┐
│  Pipeline ML    │
│  (Prédictions)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Drift Detector         │
│  (drift_detector.py)   │
│  - Génération rapport   │
│  - Sauvegarde workspace│
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Evidently Workspace    │
│  - Stockage rapports    │
│  - Métadonnées          │
│  - Tags                 │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Evidently UI           │
│  - Visualisation        │
│  - Comparaison          │
│  - Dashboards           │
└─────────────────────────┘
```

---

## Démarrage du service

### Option 1 : Docker (Recommandé pour production)

```bash
# Naviguer dans le dossier du service
cd Services/EvidentlyUI

# Construire l'image Docker
docker build -t evidently-ui .

# Lancer le container avec volume pour le workspace
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/workspace:/app/workspace \
  --name evidently-ui \
  evidently-ui
```

**Variables d'environnement Docker :**

```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/workspace:/app/workspace \
  -e EVIDENTLY_WORKSPACE_PATH=/app/workspace \
  -e EVIDENTLY_HOST=0.0.0.0 \
  -e EVIDENTLY_PORT=8000 \
  --name evidently-ui \
  evidently-ui
```

### Option 2 : Python local (Pour développement)

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Créer le dossier workspace
mkdir -p workspace

# Lancer le serveur
python main.py
```

### Option 3 : Docker Compose (Pour déploiement complet)

Créer un fichier `docker-compose.yml` :

```yaml
version: '3.8'

services:
  evidently-ui:
    build: ./Services/EvidentlyUI
    ports:
      - "8000:8000"
    volumes:
      - ./Services/EvidentlyUI/workspace:/app/workspace
    environment:
      - EVIDENTLY_WORKSPACE_PATH=/app/workspace
      - EVIDENTLY_HOST=0.0.0.0
      - EVIDENTLY_PORT=8000
    restart: unless-stopped
```

Lancer avec :

```bash
docker-compose up -d
```

### Vérification du démarrage

```bash
# Vérifier que le service est accessible
curl http://localhost:8000

# Ou ouvrir dans un navigateur
# http://localhost:8000
```

---

## Configuration du pipeline

### 1. Configuration YAML

Modifier le fichier de configuration `src/configs/consumption.{env}.yaml` :

```yaml
drift_detection:
  enabled: true
  data_drift_threshold: 0.1
  concept_drift_threshold: 0.15
  feature_columns:
    - Température
    - Humidité
    - Consommation
  target_column: "Valeur"
  
  # Configuration Evidently UI
  save_to_workspace: true
  evidently_workspace_path: "/app/workspace"
  evidently_project_name: "energy_consumption"
```

### 2. Utilisation dans le code

```python
from src.ml.utils.monitoring.drift_detector import (
    load_reference_data,
    load_production_data,
    run_evidently_drift_detection
)

# Configuration
config = {
    "data_drift_threshold": 0.1,
    "concept_drift_threshold": 0.15,
    "evidently_workspace_path": "/app/workspace",
    "evidently_project_name": "energy_consumption"
}

# Charger les données
reference_data = load_reference_data(
    reference_path="data/reference_data.parquet",
    target_column="Valeur"
)

current_data = load_production_data(
    db_handler=db_handler,
    limit=1000
)

# Exécuter la détection avec sauvegarde dans le workspace
results = run_evidently_drift_detection(
    reference_data=reference_data,
    current_data=current_data,
    config=config,
    save_to_mlflow=True,  # Optionnel : aussi sauvegarder dans MLflow
    save_to_workspace=True,  # Sauvegarder dans Evidently UI
    workspace_path="/app/workspace",
    project_name="energy_consumption"
)
```

### 3. Sauvegarde manuelle d'un rapport

```python
from src.ml.utils.monitoring.drift_detector import (
    generate_evidently_report,
    save_evidently_report_to_workspace
)

# Générer le rapport
report, report_dict = generate_evidently_report(
    reference_data=reference_data,
    current_data=current_data
)

# Sauvegarder dans le workspace avec métadonnées personnalisées
save_evidently_report_to_workspace(
    report=report,
    project_name="energy_consumption",
    report_name="custom_report_2024-01-15",
    workspace_path="/app/workspace",
    metadata={
        "model_version": "v1.2.0",
        "data_source": "production",
        "batch_id": "batch_123"
    },
    tags=["manual", "production", "v1.2.0"]
)
```

---

## Utilisation de l'interface

### Accès à l'interface

Ouvrir un navigateur et naviguer vers `http://localhost:8000`

### Navigation principale

1. **Page d'accueil** : Liste des projets disponibles
2. **Page du projet** : Rapports et dashboards du projet
3. **Page du rapport** : Détails d'un rapport spécifique

### Exploration des rapports

#### 1. Sélectionner un projet

- Cliquer sur le projet (ex: `energy_consumption`)
- Voir la liste des rapports disponibles

#### 2. Visualiser un rapport

- Cliquer sur un rapport dans la liste
- L'interface affiche :
  - **Résumé** : Métriques principales
  - **Data Drift** : Détail du drift par feature
  - **Histogrammes** : Comparaison des distributions
  - **Corrélations** : Matrice de corrélation
  - **Statistiques** : Statistiques descriptives

#### 3. Utiliser les filtres

- **Par date** : Filtrer par période
- **Par tags** : Filtrer par tags (ex: `drift_detected`, `production`)
- **Par métadonnées** : Filtrer par métadonnées personnalisées

#### 4. Comparer des rapports

- Sélectionner plusieurs rapports avec les checkboxes
- Cliquer sur "Compare"
- Voir les différences entre les snapshots

### Dashboard

Le dashboard du projet inclut :

- **Compteur de rapports** : Nombre total de rapports
- **Graphique de drift** : Évolution du drift score dans le temps
- **Métriques clés** : Résumé des métriques importantes
- **Alertes** : Rapports avec drift détecté

---

## Fonctionnalités avancées

### 1. Création de dashboards personnalisés

```python
from evidently.ui.workspace import Workspace
from evidently.ui.dashboards import DashboardPanelPlot, ReportFilter

workspace = Workspace.create("/app/workspace")
project = workspace.get_project("energy_consumption")

# Ajouter un panel personnalisé
project.dashboard.add_panel(
    DashboardPanelPlot(
        title="Évolution du PSI moyen",
        filter=ReportFilter(metadata_values={}, tag_values=[]),
        metric_id="data_drift",
        metric_name="psi",
        plot_type="line"
    )
)

project.save()
```

### 2. Tags et métadonnées

Utiliser les tags pour organiser les rapports :

```python
tags = [
    "production",  # Environnement
    "drift_detected",  # Statut
    "v1.2.0",  # Version du modèle
    "batch_123"  # ID du batch
]

metadata = {
    "model_version": "v1.2.0",
    "data_source": "production",
    "batch_id": "batch_123",
    "threshold": 0.1
}
```

### 3. Snapshots automatiques

Configurer la génération automatique de rapports :

```python
# Dans le pipeline de prédiction
if config.get("drift_detection", {}).get("save_to_workspace", False):
    results = run_evidently_drift_detection(
        reference_data=reference_data,
        current_data=current_data,
        config=config,
        save_to_workspace=True
    )
```

### 4. Export des rapports

Exporter un rapport en HTML :

```python
# Le rapport peut être exporté depuis l'interface UI
# Ou programmatiquement :
report.save_html("report_export.html")
```

---

## Intégration avec MLflow

Les deux systèmes peuvent coexister :

### Sauvegarde double

```python
results = run_evidently_drift_detection(
    reference_data=reference_data,
    current_data=current_data,
    config=config,
    save_to_mlflow=True,  # Sauvegarde dans MLflow
    save_to_workspace=True  # Sauvegarde dans Evidently UI
)
```

### Avantages de chaque système

| Système | Avantages |
|---------|-----------|
| **MLflow** | Tracking des expériences, gestion des modèles, artefacts centralisés |
| **Evidently UI** | Visualisation optimisée, comparaison avancée, dashboards interactifs |

### Workflow recommandé

```
Pipeline ML → Sauvegarde MLflow (tracking) → Sauvegarde Evidently UI (visualisation)
```

---

## Bonnes pratiques

### 1. Organisation des projets

- Un projet par modèle ou par use case
- Noms de projets cohérents : `energy_consumption`, `demand_forecasting`, etc.

### 2. Convention de nommage des rapports

```python
# Format recommandé
report_name = f"{model_name}_{timestamp}_{environment}"
# Exemple: "energy_model_20240115_120000_production"
```

### 3. Tags standards

```python
# Environnement
tags.append("production")  # ou "staging", "development"

# Statut
if drift_detected:
    tags.append("drift_detected")
else:
    tags.append("no_drift")

# Version
tags.append(f"v{model_version}")
```

### 4. Métadonnées essentielles

```python
metadata = {
    "timestamp": datetime.now().isoformat(),
    "model_version": "v1.2.0",
    "data_source": "production",
    "batch_id": "batch_123",
    "threshold": 0.1,
    "reference_data_period": "2024-01-01 to 2024-01-31"
}
```

### 5. Fréquence de génération

- **Production** : Quotidien ou après chaque batch
- **Staging** : Hebdomadaire
- **Développement** : À la demande

### 6. Nettoyage des anciens rapports

```python
# Script de nettoyage (à exécuter périodiquement)
from evidently.ui.workspace import Workspace
from datetime import datetime, timedelta

workspace = Workspace.create("/app/workspace")
project = workspace.get_project("energy_consumption")

# Supprimer les rapports de plus de 90 jours
cutoff_date = datetime.now() - timedelta(days=90)
for report in project.list_reports():
    if report.timestamp < cutoff_date:
        project.delete_report(report.id)

project.save()
```

---

## Dépannage

### Problème : Le serveur ne démarre pas

**Symptôme :** Erreur au démarrage ou port déjà utilisé

**Solutions :**

```bash
# Vérifier si le port est utilisé
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Changer le port
export EVIDENTLY_PORT=8080
python main.py

# Ou tuer le processus utilisant le port
kill -9 <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows
```

### Problème : Aucun rapport n'apparaît

**Symptôme :** L'interface se charge mais aucun rapport n'est visible

**Causes possibles :**
- Le workspace est vide
- Mauvais chemin de workspace
- Rapports non sauvegardés

**Solutions :**

```bash
# Vérifier le contenu du workspace
ls -la workspace/

# Vérifier les logs du pipeline
# Chercher "Rapport Evidently sauvegardé dans le workspace"

# Vérifier la configuration
cat src/configs/consumption.dev.yaml | grep evidently
```

### Problème : Erreur de permission

**Symptôme :** Erreur "Permission denied" lors de la sauvegarde

**Solutions :**

```bash
# Donner les permissions au dossier workspace
chmod -R 755 workspace/

# Ou changer le propriétaire
chown -R $USER:$USER workspace/

# Vérifier avec Docker
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/workspace:/app/workspace \
  --user $(id -u):$(id -g) \
  evidently-ui
```

### Problème : Rapport corrompu

**Symptôme :** Erreur lors de l'ouverture d'un rapport

**Solutions :**

```python
# Supprimer le rapport corrompu
from evidently.ui.workspace import Workspace

workspace = Workspace.create("/app/workspace")
project = workspace.get_project("energy_consumption")

# Lister les rapports
reports = project.list_reports()

# Supprimer le rapport problématique
project.delete_report(report_id)
project.save()
```

### Problème : Performance lente

**Symptôme :** L'interface est lente avec beaucoup de rapports

**Solutions :**

- Nettoyer les anciens rapports (voir section Bonnes pratiques)
- Utiliser les filtres pour réduire le nombre de rapports affichés
- Augmenter les ressources du container Docker

```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/workspace:/app/workspace \
  --memory="2g" \
  --cpus="1.5" \
  evidently-ui
```

### Problème : Connexion refusée

**Symptôme :** Impossible de se connecter à l'interface

**Solutions :**

```bash
# Vérifier que le service tourne
docker ps | grep evidently-ui
# Ou
ps aux | grep python

# Vérifier les logs
docker logs evidently-ui

# Redémarrer le service
docker restart evidently-ui
```

---

## Ressources additionnelles

- [Documentation Evidently UI](https://docs.evidentlyai.com/user-guide/ui)
- [Documentation Evidently](https://docs.evidentlyai.com/)
- [GitHub Evidently](https://github.com/evidentlyai/evidently)
- [Exemples de dashboards](https://github.com/evidentlyai/evidently/tree/main/examples)

---

## Support

Pour toute question ou problème :
1. Consulter ce guide
2. Vérifier les logs du service
3. Consulter la documentation officielle Evidently
4. Créer une issue dans le repository du projet
