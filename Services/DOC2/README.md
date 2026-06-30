---
title: Documentation MLOps Jinsudai
emoji: 👀
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
---

# Documentation MLOps - Jinsudai

Cette documentation présente l'architecture MLOps complète du projet de prédiction énergétique.

## 🚀 Accès à la documentation

La documentation complète est disponible dans le sous-dossier **docs/**. Utilisez le menu de navigation à gauche pour explorer les différents pipelines :

- **Architecture Globale** - Vue d'ensemble des composants
- **Pipeline d'Ingestion** - Collecte des données sources
- **Pipeline d'Entraînement** - Entraînement des modèles ML
- **Pipeline d'Inférence** - Prédictions en production
- **Pipeline CI/CD** - Automatisation du déploiement
- **Monitoring et Drift Detection** - Surveillance des modèles
- **Automatisation du Retraining** - Reconditionnement automatique

## 📋 Caractéristiques

- **Graphiques horizontaux** - Tous les diagrammes Mermaid coulent de gauche à droite
- **Dimensions 800x600** - Taille optimisée pour la lisibilité
- **Contraste élevé** - Thème sombre avec couleurs personnalisées
- **Pages dédiées** - Chaque pipeline a sa propre page de documentation

## 🛠️ Installation locale

Pour lancer la documentation localement :

```bash
cd Services/docsify
npm install -g docsify-cli docsify-mermaid
docsify serve docs --port 7860 --open
```

Ou avec Docker :

```bash
cd Services/docsify
docker build -t jinsudai-docs .
docker run -p 7860:7860 jinsudai-docs
```

Puis ouvrez http://localhost:7860 dans votre navigateur.
