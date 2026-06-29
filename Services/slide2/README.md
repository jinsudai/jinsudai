---
title: Slidev Presentation - Architecture MLOps
emoji: 📊
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
---

# Présentation Slidev - Architecture MLOps Jinsudai

Cette présentation Slidev présente l'architecture MLOps complète du projet de prédiction énergétique Jinsudai.

## 🚀 Contenu de la présentation

La présentation couvre les aspects suivants de l'architecture MLOps :

- **Objectifs** - Création d'algorithmes IA, infrastructure API, pipelines CI/CD
- **Architecture Globale** - Vue d'ensemble des composants et services
- **Pipeline d'Ingestion** - Collecte des données depuis différentes sources
- **Pipeline d'Entraînement** - Entraînement des modèles avec AutoGluon
- **Pipeline d'Inférence** - Prédictions en production
- **Base de Données** - Structure PostgreSQL et gestion des prédictions
- **Pipeline CI/CD** - Automatisation du déploiement
- **Monitoring et Drift Detection** - Surveillance des modèles avec Evidently AI
- **Automatisation du Retraining** - Triggers automatiques et manuels
- **Spécifications Techniques** - Conformité au cahier des charges

## 🛠️ Installation locale

Pour lancer la présentation localement avec Slidev :

```bash
cd Services/slide2
npm install
npm run dev
```

La présentation sera accessible sur http://localhost:3030

## 📦 Construction

Pour construire la présentation en fichiers statiques :

```bash
npm run build
```

Les fichiers construits seront dans le répertoire `dist/`.

## 🐳 Docker

Pour construire et exécuter avec Docker :

```bash
cd Services/slide2
docker build -t jinsudai-slides .
docker run -p 7860:7860 jinsudai-slides
```

La présentation sera accessible sur http://localhost:7860

## 🎨 Personnalisation

Le fichier `slides.md` utilise le thème par défaut de Slidev avec :

- **Thème** : Default
- **Background** : Image Unsplash
- **Transitions** : slide-left
- **Highlighter** : shiki
- **Mermaid** : Diagrammes intégrés pour l'architecture

## 📝 Mises à jour de la documentation

Cette présentation a été adaptée pour refléter les changements actuels du code :

- **Intégration S3** : Téléchargement des données depuis S3 pour le training et le monitoring
- **Gestion des stages MLflow** : Promotion automatique Staging → Production avec validation des métriques
- **Archivage automatique** : Archivage des anciens fichiers sur S3 après upload
- **Workspace Evidently UI** : Sauvegarde des rapports dans le workspace local
- **Sauvegarde S3 des rapports** : Stockage des rapports Evidently sur S3

## 🔗 Liens utiles

- [Documentation Slidev](https://slidevjs.com/)
- [Thème Slidev Default](https://github.com/slidevjs/themes/tree/main/packages/theme-default)
- [Documentation MLOps Jinsudai](../docsify/)
