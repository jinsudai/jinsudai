---
title: Présentation MLOps Jinsudai
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# Présentation MLOps - Jinsudai

Présentation interactive de l'architecture MLOps pour le projet de prédiction énergétique, générée avec Marp.

## 🚀 Caractéristiques

- **Diagrammes Mermaid** - Graphiques horizontaux optimisés
- **Thème sombre** - Contraste élevé pour meilleure lisibilité
- **Dimensions 800x600** - Taille optimisée pour présentation
- **Export PDF** - Téléchargeable pour partage

## 📋 Contenu

- Architecture globale des composants
- Pipeline d'ingestion des données
- Pipeline d'entraînement des modèles
- Pipeline d'inférence en production
- Pipeline CI/CD automatisé
- Monitoring et détection de drift
- Automatisation du retraining

## 🛠️ Installation locale

Pour lancer la présentation localement :

```bash
cd Services/marp
npm install -g @marp-team/marp-cli
marp slides.md --html --server
```

Ou avec Docker :

```bash
cd Services/marp
docker build -t jinsudai-marp .
docker run -p 7860:7860 jinsudai-marp
```

Puis ouvrez http://localhost:7860 dans votre navigateur.
