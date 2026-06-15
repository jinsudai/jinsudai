---
title: EvidentlyAI
emoji: 📊
colorFrom: pink
colorTo: indigo
sdk: docker
pinned: false
---



# Evidently AI Dashboard

Dashboard Streamlit pour visualiser les rapports de drift detection générés par Evidently AI.

## Fonctionnalités

- Visualisation des rapports de drift detection
- Affichage des métriques de drift (data drift, concept drift)
- Intégration avec MLflow pour récupérer les rapports
- Interface interactive pour explorer les résultats

## Déploiement

Ce service est déployé sur HuggingFace Spaces via le workflow `.github/workflows/hf_create_spaces.yaml`.

## Configuration

Le dashboard se configure via :
- Variables d'environnement (MLFLOW_TRACKING_URI, etc.)
- Fichier `config.yaml` à la racine du projet

## Utilisation

1. Le dashboard se connecte automatiquement à MLflow
2. Il récupère les rapports Evidently stockés comme artefacts
3. Les rapports sont affichés dans une interface interactive

## Dépendances

- evidently
- streamlit
- mlflow
- pandas
- plotly
