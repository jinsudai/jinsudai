# Structure du répertoire `src/ml/`

Ce répertoire contient toute la logique Machine Learning du projet, organisée selon une **architecture modulaire par domaine** avec séparation claire entre code partagé, logique métier et orchestration.

## 📁 Arborescence

```
src/
├── configs/                       # 📋 Configurations centralisées
│   ├── consumption.yaml          # Configuration domaine consommation
│   ├── solar_production.yaml     # Configuration domaine production solaire
│   └── [autres configs...]
│
└── ml/
    ├── config.py                 # ✅ Chargeur central de configs
    ├── pipelines/                # 🔄 Pipelines ML (orchestration complète)
    │   ├── training_pipeline.py  # Classe MLPipeline (entraînement)
    │   ├── inference_pipeline.py # Pipeline d'inférence
    │   ├── ingestion_pipeline.py  # Pipeline d'ingestion des données
    │   └── monitoring_pipeline.py # Pipeline de monitoring et drift detection
    │
    ├── utils/                     # 🔧 Code utilitaire partagé (réutilisable)
    │   ├── data/
    │   │   ├── data_loader.py      # Chargement CSV depuis data/raw/
    │   │   ├── data_preparation.py # Prétraitement: imputation, scaling, encoding
    │   │   ├── data_transformer.py # Feature engineering (dates, colonnes)
    │   │   └── data_validator.py    # Validation qualité données
    │   
    │   ├── models/
    │   │   ├── model.py             # Entraînement (RandomForest, AutoGluon)
    │   │   ├── inference_model.py   # Classe InferenceModel (chargement MLflow)
    │   │   └── mlflow_tracker.py    # Logging métriques/artefacts dans MLflow
    │   
    │   └── api/                   # Intégrations externes
    │       ├── weather_api.py      # Récupération données météo
    │       └── ...
    │
    ├── consumption/              # ⚡ Logique spécifique CONSOMMATION ÉLECTRIQUE
    │   ├── __init__.py
    │   └── [futures classes]      # Ex: ConsumptionModel(InferenceModel)
    │
    ├── solar_production/          # ☀️ Logique spécifique PRODUCTION SOLAIRE
    │   ├── __init__.py
    │   └── [futures classes]
    │
```

---

## 🏗️ Principes d'architecture

### 1. **Séparation des concerns**
| Répertoire | Responsabilité | Exemples |
|------------|----------------|----------|
| `utils/` | Code générique réutilisable | Chargement CSV, prétraitement, tracking MLflow |
| `consumption/` / `solar_production/` | Logique métier spécifique | Validation domaine, métriques custom |
| `pipelines/` | Orchestration des pipelines ML | Training, inference, ingestion, monitoring |

### 2. **Flux de données**
```
pipelines/          → Orchestre les pipelines ML
    │
    ├──→ utils/data/          → Charge et valide données
    │       │
    │       └──→ consumption/ → Applique logique métier consommation
    │               │
    │               └──→ utils/models/ → Entraîne et sauvegarde modèle
    │                       │
    │                       └──→ utils/mlflow_tracker.py → Log dans MLflow
    │
    └──→ solar_production/    → Idem pour production solaire
```

### 3. **Règles de dépendance**
- ⬆️ **`utils/`** ne dépend **jamais** de `consumption/` ou `solar_production/`
- ⬇️ **`consumption/` et `solar_production/`** peuvent importer depuis `utils/`
- ⬇️ **`pipelines/`** importe depuis `utils/` ET les répertoires domaine

---

## 📌 Bonnes pratiques

### Ajouter un nouveau domaine (ex: `battery_storage/`)
1. Créer `src/configs/battery_storage.yaml`
2. Implémenter la logique métier dans `src/ml/battery_storage/`
3. Ajouter un pipeline dans `src/ml/pipelines/battery_storage_pipeline.py`
4. **Ne pas** modifier `utils/` sauf si le code est réutilisable par tous

### Étendre une fonctionnalité partagée
- Ajouter/modifier dans `utils/` (ex: nouveau type de prétraitement)
- **Tester** l'impact sur tous les domaines avant merge

### Créer un pipeline ML
- **Toujours** dans `pipelines/`
- Importer la logique depuis les répertoires domaine
- Exemple minimal :
  ```python
  from ml.consumption.training import train_model
  from ml.utils.data.data_loader import load_data
  
  def consumption_training():
      data = load_data("data/raw/consumption.csv")
      train_model(data)
  ```

---

## 🔗 Exemples concrets

### Cas 1: Entraînement d'un modèle de consommation
```python
# src/ml/pipelines/training_pipeline.py
from ml.config import load_config  # Chargeur central
from ml.utils.data.data_loader import load_data
from ml.pipelines.training_pipeline import MLPipeline

def consumption_full_pipeline():
    config = load_config("consumption.yaml")  # Charge depuis src/configs/
    pipeline = MLPipeline(config_path=config)
    pipeline.run()
```

### Cas 2: Inférence en production
```python
# src/ml/pipelines/inference_pipeline.py (partagé)
from ml.config import load_config
from ml.utils.models.inference_model import InferenceModel
from ml.consumption.models import ConsumptionInferenceModel  # Spécialisation

def predict_consumption():
    config = load_config("consumption.yaml")
    model = ConsumptionInferenceModel(config=config)  # Héritage de InferenceModel
    return model.predict(new_data)
```
