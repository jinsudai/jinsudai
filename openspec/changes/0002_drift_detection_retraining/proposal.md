# Change Proposal
Titre: Pipeline de détection de drift et retraining automatique

Description: Créer un pipeline complet pour détecter le drift de données et de modèle, avec un mécanisme de retraining automatique des modèles de consommation énergétique.

## Contexte
Les modèles de ML en production peuvent se dégrader avec le temps dû aux changements dans les patterns de consommation (concept drift) ou dans la distribution des données (data drift). Un système de monitoring et de retraining automatique est essentiel pour maintenir la performance des modèles.

## Objectifs
- Implémenter la détection de data drift et concept drift
- Créer un pipeline de retraining automatique déclenché par la détection de drift
- Intégrer des outils de monitoring (Evidently ou Aporia)
- Mettre en place des alertes et notifications
- Assurer la traçabilité des versions de modèles

## Non-goals
- Création de nouveaux modèles de ML (focus sur l'infrastructure de monitoring/retraining)
- Modification des pipelines de prédiction existants
- Interface utilisateur complexe (focus sur l'automatisation)
