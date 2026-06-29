# Pour Devin

## Tâches de fond:
Eviter les sauts de ligne inutiles

# A faire

## question

## documentation
- slidev -> utiliser EvidentlAI
- actualiser la documentation en verifiant ce qui est pertinent à documenter
-- Orchestration airflow qui déclenche GitHub Actions
-- Prediction (inférence) inclue dans le pipeline pour être executé une seule fois dans un environnement temporaire
-- Db?


# Nice to have

## Monitoring
- datadrift récupérer le fichier depuis S3 dans prepared (et non le reference))
- autre drifts?
- email notification

## prepare Consumption prepare -> En cours
- vérifier si pas code en double pour récupéré les  valeurs réelle depuis la base de donnée -> Doublon consumption_preparer.py et preparation.py? get_predictions...
- Enlever les exemples donnés pour les connecteurs si non pertinent -> les mettre dans Script?
- Simplifier l'ingestion: get_predictions_by_date(start_date, end_date) non necessaire

# A Nettoyer
- Faire marcher les scripts restants
- get_production_data_for_retraining peut être renommé en get_production_data
- Clean vacances etc...
- Renommer les fichiers initiaux pour suivre le format date_xxx.parquet

# A faire
- Gérer correctement la preparation du premier training
-- Identifier que c'est le premier training

# Plus tard
- fichier de config différent pour les services. (evite de le trigger)
- email notifier
- config.yaml pour les différents environnements
- Réparer base de donnée neon airflai (via un import de celle de jinsudai? Essayer plutot airflow db reset --yes)
- Faire en sorte que chaque pipeline soit un service ?
- Loki pour collecter les logs ?
- Fast API qui contient tout le ML pour une orchestration peu gourmande avec l'orchestrateur qui appelle les endpoints
- Optimisation du dockerfile JinsudAPI








CI & CD issues

deployement docker avec:
EvidentlyUI / Airflow
Base de donnée externes / Mlflow Externe


QU'est ce qu'il manque dans le projet pour respecter le besoin suivant:
Description: Faire en sorte de respecter le cahier des charges
Créer un algorithme d'Intelligence Artificielle adapté aux données d'entraînement et conforme aux spécifications du cahier des charges, en veillant à répondre aux besoins spécifiques, notamment en termes d'accessibilité.
Adapter l'infrastructure de données de l'organisation à travers la construction d'API pour accueillir la solution d'IA en production.
Concevoir des pipelines d'intégration et déploiement continu pour automatiser le processus de déploiement d'une solution d'IA.
Développer des scripts de réentrainement des modèles pour automatiser le processus de Machine Learning.
Piloter la performance de la solution d'IA dans l'infrastructure à travers la mise en place d'outils de monitoring (comme Aporia ou Evidently) pour s'assurer qu'elle respecte les spécifications du cahier des charges dans un environnement de production.
