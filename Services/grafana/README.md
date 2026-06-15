# Dashboard Grafana - MLOps Energy Prediction

Ce dossier contient la configuration du dashboard Grafana pour le monitoring du projet de prédiction énergétique.

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Panels du Dashboard](#panels-du-dashboard)
3. [Configuration des Data Sources](#configuration-des-data-sources)
4. [Installation](#installation)
5. [Utilisation](#utilisation)
6. [Alertes et Seuils](#alertes-et-seuils)

---

## Vue d'ensemble

Le dashboard Grafana fournit une vue centralisée des métriques clés du projet MLOps :
- **Performance des modèles** : R², MAE, RMSE, MAPE
- **Monitoring du drift** : Data drift, concept drift via EvidentlyAI
- **SLA** : Temps d'inférence (< 100ms)
- **Volume d'activité** : Entraînements et prédictions
- **Alertes** : Basées sur les seuils définis dans les spécifications

---

## Panels du Dashboard

### 1. Vue d'ensemble (Row 1)

- **R² Score (Consommation)** : Score R² actuel pour le modèle de consommation
  - Vert : ≥ 0.90
  - Jaune : 0.85 - 0.90
  - Rouge : < 0.85

- **R² Score (Solaire)** : Score R² actuel pour le modèle de production solaire
  - Vert : ≥ 0.92
  - Jaune : 0.88 - 0.92
  - Rouge : < 0.88

- **Temps d'Inférence** : Temps moyen d'inférence en millisecondes
  - Vert : < 80ms
  - Jaune : 80 - 100ms
  - Rouge : ≥ 100ms

- **Data Drift Status** : Statut du drift de données
  - Vert : OK (pas de drift)
  - Rouge : DRIFT détecté

### 2. Évolution du R² (Row 2)

Graphique temporel montrant l'évolution des scores R² pour les deux modèles :
- R² Consommation
- R² Solaire

### 3. MAE & RMSE (Row 2)

Graphique temporel des erreurs :
- MAE Consommation
- MAE Solaire
- RMSE Consommation
- RMSE Solaire

### 4. Data Drift - Features (Row 3)

Graphique temporel du drift de données :
- Nombre de features en drift
- Nombre total de features analysées
- Seuils : Vert (< 0.1), Jaune (0.1 - 0.25), Rouge (≥ 0.25)

### 5. Temps d'Inférence (Row 3)

Graphique temporel du temps d'inférence avec seuil SLA (< 100ms)

### 6. MAPE (Row 4)

Graphique temporel du Mean Absolute Percentage Error pour la consommation

### 7. Volume d'Activité (Row 4)

Graphique en barres montrant :
- Nombre d'entraînements
- Nombre de prédictions

### 8. Alertes - Seuils R² (Row 5)

Bar gauge montrant l'état des alertes basées sur les seuils R²

---

## Configuration des Data Sources

Le dashboard nécessite les data sources suivantes :

### 1. MLflow

**Type** : Prometheus ou HTTP API

**Configuration** :
- URL : `http://localhost:5000` (ou votre URI MLflow)
- Access : Server (default)
- Auth : Basic (si nécessaire)

**Métriques disponibles** :
- `metrics_r2` : Score R² consommation
- `metrics_r2_solar` : Score R² solaire
- `metrics_mae` : Mean Absolute Error consommation
- `metrics_mae_solar` : Mean Absolute Error solaire
- `metrics_rmse` : Root Mean Square Error consommation
- `metrics_rmse_solar` : Root Mean Square Error solaire
- `metrics_mape` : Mean Absolute Percentage Error consommation
- `inference_time_ms` : Temps d'inférence en ms
- `training_count` : Nombre d'entraînements
- `prediction_count` : Nombre de prédictions

### 2. EvidentlyAI

**Type** : Prometheus ou HTTP API

**Configuration** :
- URL : `http://localhost:8501` (ou votre URI EvidentlyAI)
- Access : Server (default)

**Métriques disponibles** :
- `dataset_drift` : 1 si drift détecté, 0 sinon
- `drifted_features` : Nombre de features en drift
- `total_features` : Nombre total de features

---

## Installation

### Option 1 : Import manuel dans Grafana

1. Ouvrir Grafana (`http://localhost:3000`)
2. Aller dans **Dashboards** → **Import**
3. Choisir **Upload JSON file**
4. Sélectionner `dashboard.json`
5. Sélectionner les data sources (MLflow, EvidentlyAI)
6. Cliquer sur **Import**

### Option 2 : Via API Grafana

```bash
# Installer la CLI Grafana
pip install grafana-api

# Importer le dashboard
python -c "
from grafana_api.grafana_face import GrafanaFace
import json

grafana = GrafanaFace(
    auth=('admin', 'admin'),
    host='localhost',
    port=3000
)

with open('dashboard.json', 'r') as f:
    dashboard = json.load(f)

grafana.dashboard.update_dashboard(dashboard)
"
```

### Option 3 : Via Docker Compose

Ajouter à votre `docker-compose.yml` :

```yaml
version: '3.8'

services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/data:/var/lib/grafana
      - ./Services/grafana/dashboard.json:/etc/grafana/provisioning/dashboards/dashboard.json
    depends_on:
      - mlflow
      - evidently
```

---

## Utilisation

### Variables du Dashboard

Le dashboard inclut des variables pour filtrer les données :

- **Experiment** : Nom de l'expérience MLflow (défaut: `energy_consumption`)
- **Time Range** : Période temporelle (défaut: `7d`)

### Rafraîchissement

Le dashboard se rafraîchit automatiquement toutes les 30 secondes. Vous pouvez modifier cette fréquence dans les paramètres du dashboard.

### Personnalisation

Pour personnaliser le dashboard :

1. Cliquer sur le **menu** (haut droite) → **Settings**
2. Modifier les panels, les seuils, ou les requêtes
3. Sauvegarder les modifications

---

## Alertes et Seuils

### Consommation Électrique

| Métrique | Warning | Critical | Action |
|----------|---------|----------|--------|
| R² | < 0.88 | < 0.85 | Réentraînement immédiat si critical |
| Temps d'inférence | ≥ 80ms | ≥ 100ms | Optimiser le modèle |
| Data drift | PSI ≥ 0.1 | PSI ≥ 0.25 | Investigation des features |

### Production Solaire

| Métrique | Warning | Critical | Action |
|----------|---------|----------|--------|
| R² | < 0.90 | < 0.88 | Réentraînement immédiat si critical |
| Temps d'inférence | ≥ 80ms | ≥ 100ms | Optimiser le modèle |
| Data drift | PSI ≥ 0.1 | PSI ≥ 0.25 | Investigation des features |

### Configuration des Alertes Grafana

Pour configurer des alertes dans Grafana :

1. Aller dans **Alerting** → **New Alert Rule**
2. Sélectionner le dashboard et le panel
3. Définir les conditions (ex: `R² < 0.85`)
4. Configurer les notifications (email, Slack, etc.)
5. Sauvegarder l'alerte

---

## Intégration avec le Projet

### Logging des Métriques

Les métriques sont automatiquement loggées dans MLflow lors des entraînements et des prédictions. Exemple :

```python
import mlflow

# Logging des métriques d'entraînement
mlflow.log_metric("metrics_r2", 0.92)
mlflow.log_metric("metrics_mae", 45.3)
mlflow.log_metric("metrics_rmse", 67.8)
mlflow.log_metric("metrics_mape", 0.08)

# Logging du temps d'inférence
mlflow.log_metric("inference_time_ms", 85)
```

### Intégration EvidentlyAI

Les rapports EvidentlyAI sont générés automatiquement et les métriques de drift sont loggées dans MLflow :

```python
from src.ml.utils.monitoring.drift_detector import generate_evidently_report

# Générer le rapport et logger les métriques
report, report_dict = generate_evidently_report(
    reference_data=reference_data,
    current_data=current_data
)

mlflow.log_metric("dataset_drift", report_dict.get('dataset_drift', 0))
mlflow.log_metric("drifted_features", report_dict.get('drifted_features', 0))
mlflow.log_metric("total_features", report_dict.get('total_features', 0))
```

---

## Dépannage

### Problème : Aucune donnée affichée

**Causes possibles** :
- Data sources non configurées
- MLflow ou EvidentlyAI non accessibles
- Métriques non loggées

**Solutions** :
```bash
# Vérifier que MLflow est accessible
curl http://localhost:5000/health

# Vérifier que EvidentlyAI est accessible
curl http://localhost:8501

# Vérifier les métriques dans MLflow
python -c "
import mlflow
mlflow.set_tracking_uri('http://localhost:5000')
runs = mlflow.search_runs()
print(runs.head())
"
```

### Problème : Data source non connectée

**Solution** :
1. Aller dans **Configuration** → **Data Sources**
2. Sélectionner la data source (MLflow ou EvidentlyAI)
3. Cliquer sur **Save & Test**
4. Vérifier que le statut est "OK"

### Problème : Alertes non déclenchées

**Solution** :
1. Vérifier que les canaux de notification sont configurés
2. Vérifier que les conditions d'alerte sont correctes
3. Consulter les logs de Grafana : `/var/log/grafana/grafana.log`

---

## Bonnes Pratiques

1. **Fréquence de monitoring** : Configurer le rafraîchissement selon vos besoins (30s recommandé)
2. **Seuils adaptés** : Ajuster les seuils selon la criticité de votre application
3. **Alertes multiples** : Configurer des alertes sur plusieurs canaux (email, Slack, PagerDuty)
4. **Documentation** : Documenter chaque incident et les actions prises
5. **Maintenance** : Mettre à jour régulièrement le dashboard avec de nouvelles métriques

---

## Ressources

- [Documentation Grafana](https://grafana.com/docs/)
- [Documentation MLflow](https://mlflow.org/docs/latest/index.html)
- [Documentation EvidentlyAI](https://docs.evidentlyai.com/)
- [Spécifications du Projet](../../SPECIFICATIONS.md)

---

## Support

Pour toute question ou problème :
- Consulter le README principal du projet : `../../README.md`
- Consulter les spécifications : `../../SPECIFICATIONS.md`
- Ouvrir une issue sur le repository GitHub
