# Guide de Visualisation du Monitoring EvidentlyAI

Ce guide explique comment visualiser et interpréter les rapports de monitoring générés par EvidentlyAI dans le projet Jinsudai.

## 📋 Table des matières

1. [Architecture du Monitoring](#architecture-du-monitoring)
2. [Génération des Rapports](#génération-des-rapports)
3. [Accès au Dashboard Streamlit](#accès-au-dashboard-streamlit)
4. [Visualisation dans MLflow](#visualisation-dans-mlflow)
5. [Interprétation des Résultats](#interprétation-des-résultats)
6. [Dépannage](#dépannage)

---

## Architecture du Monitoring

Le système de monitoring EvidentlyAI est composé de plusieurs composants :

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
│  - Data Drift           │
│  - Concept Drift        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Rapports Evidently     │
│  - HTML                 │
│  - Métriques JSON       │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  MLflow                 │
│  - Stockage artefacts    │
│  - Logging métriques    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Dashboard Streamlit    │
│  (main.py)              │
│  - Visualisation        │
│  - Exploration          │
└─────────────────────────┘
```

### Composants principaux

- **`src/ml/utils/monitoring/drift_detector.py`** : Module Python qui génère les rapports Evidently
- **`Services/EvidentlyAI/main.py`** : Dashboard Streamlit pour visualiser les rapports
- **MLflow** : Stockage centralisé des rapports et métriques

---

## Génération des Rapports

Les rapports Evidently sont générés automatiquement lors de l'exécution du pipeline de prédiction.

### 1. Configuration

La configuration du drift detection se trouve dans `src/configs/consumption.{env}.yaml` :

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
```

### 2. Exécution automatique

Le rapport est généré automatiquement quand :
- Le pipeline de prédiction s'exécute
- La détection de drift est activée dans la configuration
- Des données de production sont disponibles

### 3. Génération manuelle

Pour générer un rapport manuellement :

```python
from src.ml.utils.monitoring.drift_detector import (
    load_reference_data,
    load_production_data,
    generate_evidently_report,
    save_evidently_report_to_mlflow
)

# Charger les données
reference_data = load_reference_data(
    reference_path="data/reference_data.parquet",
    target_column="Valeur"
)

current_data = load_production_data(
    db_handler=db_handler,
    limit=1000
)

# Générer le rapport
report, report_dict = generate_evidently_report(
    reference_data=reference_data,
    current_data=current_data,
    output_path="reports",
    report_name="custom_drift_report"
)

# Sauvegarder dans MLflow
save_evidently_report_to_mlflow(
    report=report,
    report_dict=report_dict,
    run_id=None  # Utilise la run active
)
```

---

## Accès au Dashboard Streamlit

Le dashboard Streamlit est l'interface principale pour visualiser les rapports Evidently.

### Option 1 : Exécution locale

```bash
# Naviguer dans le dossier du service
cd Services/EvidentlyAI

# Installer les dépendances
pip install -r requirements.txt

# Lancer le dashboard
streamlit run main.py
```

Le dashboard sera accessible à `http://localhost:8501`

### Option 2 : Via Docker

```bash
# Construire l'image
cd Services/EvidentlyAI
docker build -t evidently-dashboard .

# Lancer le container
docker run -p 8501:8501 evidently-dashboard
```

### Option 3 : Déploiement HuggingFace Spaces

Le dashboard est automatiquement déployé sur HuggingFace Spaces via le workflow GitHub `.github/workflows/hf_create_spaces.yaml`.

### Configuration du Dashboard

Dans la sidebar du dashboard :

1. **MLflow Tracking URI** : URI du serveur MLflow (par défaut: `http://localhost:5000`)
2. **Experiment Name** : Nom de l'expérience MLflow (par défaut: `energy_consumption`)
3. **Jours à analyser** : Période d'analyse pour les métriques (1-30 jours)

---

## Visualisation dans MLflow

Les rapports peuvent également être visualisés directement dans l'interface MLflow.

### Accès à MLflow UI

```bash
# Lancer MLflow UI
mlflow ui

# Ou spécifier le backend store
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

L'interface MLflow sera accessible à `http://localhost:5000`

### Navigation dans MLflow

1. Sélectionner l'expérience (ex: `energy_consumption`)
2. Cliquer sur une run
3. Dans la section "Artifacts", chercher le dossier `evidently_reports`
4. Télécharger ou visualiser le fichier HTML du rapport

### Métriques dans MLflow

Les métriques suivantes sont loggées automatiquement :

- `dataset_drift` : 1 si drift détecté, 0 sinon
- `drifted_features` : Nombre de features en drift
- `total_features` : Nombre total de features analysées
- `drift_{feature_name}` : 1 si la feature est en drift, 0 sinon

---

## Interprétation des Résultats

### Data Drift

Le **Data Drift** détecte les changements dans la distribution des features entre les données d'entraînement et les données de production.

**Indicateurs clés :**
- **Dataset Drift** : Indicateur global de drift sur l'ensemble du dataset
- **Drifted Features** : Nombre de features dont la distribution a changé
- **PSI (Population Stability Index)** : Score de drift par feature
  - PSI < 0.1 : Pas de drift significatif
  - 0.1 ≤ PSI < 0.25 : Drift modéré
  - PSI ≥ 0.25 : Drift significatif

**Visualisations dans le rapport :**
- Histogrammes comparatifs (référence vs courant)
- Boxplots par feature
- Heatmap des corrélations
- Distribution des valeurs par feature

### Concept Drift

Le **Concept Drift** détecte les changements dans la relation entre les features et la cible, ou dans la performance du modèle.

**Indicateurs clés :**
- **Mean Drift** : Changement dans la moyenne des prédictions
- **Std Drift** : Changement dans l'écart-type des prédictions
- **MAE Drift** : Changement dans l'erreur absolue moyenne
- **R² Drift** : Changement dans le coefficient de détermination

**Actions recommandées :**

| Situation | Action |
|-----------|--------|
| Data drift détecté sur 1-2 features | Monitoring accru, investigation des features |
| Data drift détecté sur >50% features | Re-entraînement du modèle recommandé |
| Concept drift détecté | Re-entraînement avec données récentes |
| Performance dégradée (MAE↑, R²↓) | Investigation des données, re-entraînement |

---

## Dépannage

### Problème : Aucun rapport trouvé dans le dashboard

**Causes possibles :**
- Aucune exécution du pipeline avec drift detection
- Mauvaise configuration MLflow
- Rapports non sauvegardés dans MLflow

**Solutions :**
```bash
# Vérifier que MLflow est accessible
curl http://localhost:5000/health

# Vérifier les runs dans l'expérience
python -c "
import mlflow
mlflow.set_tracking_uri('http://localhost:5000')
experiment = mlflow.get_experiment_by_name('energy_consumption')
print(experiment)
if experiment:
    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    print(f'{len(runs)} runs trouvées')
"
```

### Problème : Erreur de connexion MLflow

**Solution :**
```bash
# Vérifier que MLflow UI est lancé
mlflow ui --port 5000

# Ou utiliser le tracking URI correct dans la sidebar du dashboard
```

### Problème : Rapport HTML ne s'affiche pas

**Solution :**
- Vérifier que le fichier HTML existe dans les artefacts MLflow
- Vérifier les permissions de téléchargement
- Essayer de télécharger le rapport directement depuis MLflow UI

### Problème : Métriques incorrectes

**Vérifier :**
- Les seuils de drift dans la configuration
- La qualité des données de référence
- Le volume de données de production (minimum recommandé: 1000 enregistrements)

---

## Bonnes Pratiques

1. **Fréquence de monitoring** : Exécuter la détection de drift quotidiennement ou après chaque batch de prédictions
2. **Données de référence** : Mettre à jour périodiquement les données de référence (mensuellement ou trimestriellement)
3. **Seuils adaptés** : Ajuster les seuils de drift selon la criticité de votre application
4. **Alertes** : Configurer des alertes automatiques quand un drift significatif est détecté
5. **Documentation** : Documenter chaque incident de drift et les actions prises

---

## Ressources Additionnelles

- [Documentation EvidentlyAI](https://docs.evidentlyai.com/)
- [Documentation MLflow](https://mlflow.org/docs/latest/index.html)
- [Documentation Streamlit](https://docs.streamlit.io/)

---

## Support

Pour toute question ou problème, consultez :
- Le README du service : `Services/EvidentlyAI/README.md`
- Le code du détecteur : `src/ml/utils/monitoring/drift_detector.py`
- Le fichier de configuration : `config.yaml`
