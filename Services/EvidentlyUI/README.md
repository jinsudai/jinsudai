---
title: Evidently UI
emoji: 👀
colorFrom: indigo
colorTo: indigo
sdk: docker
pinned: false
---



# Evidently UI Service

Service Evidently UI natif pour visualiser les rapports de monitoring ML générés par EvidentlyAI.

## 🎯 Objectif

Ce service fournit l'interface utilisateur native d'EvidentlyAI pour visualiser et explorer les rapports de drift detection.

## ✨ Fonctionnalités

- **Interface native Evidently** : Visualisation optimisée des rapports Evidently
- **Workspaces et projets** : Organisation structurée des rapports par projet
- **Dashboards interactifs** : Graphiques et métriques en temps réel
- **Comparaison multi-rapports** : Comparaison facile entre plusieurs snapshots
- **Performance** : Gestion efficace des grands volumes de rapports
- **API REST** : Accès programmatique aux rapports

## 🏗️ Architecture

```
Pipeline ML → Drift Detector → Workspace Evidently → Evidently UI
```

## 🚀 Démarrage rapide

### Option 1 : Docker (Recommandé)

```bash
# Construire l'image
cd Services/EvidentlyUI
docker build -t evidently-ui .

# Lancer le container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/workspace:/app/workspace \
  --name evidently-ui \
  evidently-ui
```

L'interface sera accessible à `http://localhost:8000`

### Option 2 : Python local

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Créer le dossier workspace
mkdir -p workspace

# Lancer le serveur
python main.py
```

## ⚙️ Configuration

Variables d'environnement :

- `EVIDENTLY_WORKSPACE_PATH` : Chemin du workspace (défaut: `/app/workspace`)
- `EVIDENTLY_HOST` : Hôte du serveur (défaut: `0.0.0.0`)
- `EVIDENTLY_PORT` : Port du serveur (défaut: `8000`)

Exemple :

```bash
export EVIDENTLY_WORKSPACE_PATH=/path/to/workspace
export EVIDENTLY_PORT=8080
python main.py
```

## 📊 Utilisation

### 1. Génération des rapports

Les rapports sont générés par le module `drift_detector.py` et sauvegardés dans le workspace Evidently :

```python
from src.ml.utils.monitoring.drift_detector import save_evidently_report_to_workspace

# Sauvegarder le rapport dans le workspace Evidently
save_evidently_report_to_workspace(
    report=report,
    project_name="energy_consumption",
    report_name="drift_report_2024-01-15"
)
```

### 2. Visualisation dans l'UI

1. Ouvrir `http://localhost:8000` dans un navigateur
2. Sélectionner le projet (ex: `energy_consumption`)
3. Explorer les rapports disponibles
4. Utiliser les filtres pour comparer les snapshots

### 3. Dashboard

Le dashboard inclut :
- **Compteur de rapports** : Nombre total de rapports dans le projet
- **Drift Score** : Évolution du score de drift dans le temps
- **Métriques par feature** : Détail du drift par feature

## 🔧 Intégration avec le pipeline

Pour intégrer ce service dans le pipeline ML, modifier la configuration :

```yaml
# src/configs/consumption.dev.yaml
drift_detection:
  enabled: true
  save_to_evidently_ui: true  # Nouvelle option
  evidently_workspace_path: "/app/workspace"
  evidently_project_name: "energy_consumption"
```

## 📦 Dépendances

- evidently >= 0.4.0
- uvicorn[standard] >= 0.24.0
- pydantic >= 2.0.0
- pandas >= 2.0.0
- numpy >= 1.24.0


## 📚 Documentation additionnelle

- [Guide d'utilisation complet](./GUIDE_UTILISATION.md)
- [Documentation Evidently UI](https://docs.evidentlyai.com/user-guide/ui)
- [Documentation Evidently](https://docs.evidentlyai.com/)

## 🆘 Dépannage

### Problème : Le serveur ne démarre pas

```bash
# Vérifier que le port n'est pas déjà utilisé
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Changer le port
export EVIDENTLY_PORT=8080
python main.py
```

### Problème : Aucun rapport n'apparaît

- Vérifier que le pipeline a généré des rapports
- Vérifier le chemin du workspace
- Vérifier les permissions d'écriture

### Problème : Erreur de connexion

```bash
# Vérifier que le serveur tourne
curl http://localhost:8000

# Vérifier les logs
docker logs evidently-ui
```
