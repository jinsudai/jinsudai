# Contexte du projet

**Contexte**

- La consommation énergétique est de plus en plus variable en raison des conditions météorologiques, des usages et des contraintes opérationnelles.
- L'augmentation des coûts de l'énergie et les objectifs de réduction des émissions de CO₂ rendent indispensable une meilleure maîtrise des consommations.
- Les gestionnaires ont besoin d'anticiper la demande afin d'optimiser les ressources et de limiter les pertes.

**Problématique**

- Difficulté à prévoir précisément les besoins énergétiques.
- Risque de surconsommation ou de sous-dimensionnement des capacités.
- Décisions souvent prises sur la base de données historiques sans capacité de prévision fiable.

**Objectif du projet**  
Développer un modèle de prédiction de la consommation énergétique permettant de :

- prévoir la demande à court et moyen terme ;
- optimiser la planification des ressources ;
- réduire les coûts énergétiques ;
- améliorer la performance opérationnelle et environnementale.

**Bénéfices attendus**

- 📈 Prévisions plus précises
- 💰 Réduction des coûts
- ⚡ Optimisation de la consommation
- 🌱 Diminution de l'empreinte carbone
- 📊 Aide à la prise de décision grâce aux données


---

# Notes

- Documentation complète en Français
- Code simple et lisible (priorité)
- Pas de dépendances externes lourdes
- Approche multi-domaines avec code partagé (`src/ml/`)
- Configurations spécifiques par domaine (yaml)


---

## Variables d'environnement

Voir le fichier: .env.secrets.example


---

## Structure du code

### Architecture multi-domaines

```
src/
├── ml/                        # Cœur MLOps (réutilisable)
│   ├── consumption/
│   │   ├── configs/
│   │   │   └── config.yaml    # Config spécifique consommation
│   │   └── __init__.py
│   │
│   ├── solar_production/
│   │   ├── configs/
│   │   │   └── config.yaml    # Config spécifique production PV
│   │   └── __init__.py
│   │
│   ├── config.py              # Gestion config (générique)
│   ├── data/                  # Data loading, validation, preparation
│   ├── models/                # Training, inference, tracking
│   ├── monitoring/            # Performance monitoring, drift detection
│   ├── pipelines/             # Orchestration train/predict
│   └── utils/                 # Utilitaires ML
│
├── utils/
│   └── resend_client/         # Client email (notifications)
│
├── configs/
│   └── config_global.yaml     # Config globale (MLflow, env vars)
│
├── pipelines/                 # Entry points orchestration
└── scripts/                   # (Optionnel) CLI helpers
```

### Différenciation par config

| Paramètre | Consommation | Production Solaire |
|-----------|-------------|-------------------|
| **Config** | `src/ml/consumption/configs/config.yaml` | `src/ml/solar_production/configs/config.yaml` |
| **Problem type** | Regression (kWh continu) | Regression (kWh continu) |
| **Features** | Température, humidité, précip, vacances | Température, humidité, irradiance, cloud cover |
| **Métrique** | R² >= 0.90 | R² >= 0.92 |
| **Alert threshold** | < 0.85 | < 0.88 |
| **Experiment name** | energy_consumption | solar_production |

### Utilisation en Python

```python
# Consommation
from src.ml.config import load_config
from src.ml.pipelines.training import TrainingPipeline

config = load_config("src/ml/consumption/configs/config.yaml")
pipeline = TrainingPipeline(config_path="src/ml/consumption/configs/config.yaml")
```

```python
# Production solaire
config = load_config("src/ml/solar_production/configs/config.yaml")
pipeline = TrainingPipeline(config_path="src/ml/solar_production/configs/config.yaml")
```

