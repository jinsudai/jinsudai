# Pour Devin

## Tâches de fond:
Eviter les sauts de ligne inutiles


# A faire

## question
github_action_trigger.py est utilisé?
EmailResend.py est utilisé?

Expliquer  """Génère un jeu de données d'inférence pour n jours."""
    np.random.seed(seed)  ?

## documentation
- actualiser la documentation

## prepare Consumption prepare -> En cours
- Date non prise en compte -> Check Head
- vérifier si pas code en double pour récupéré les  valeurs réelle depuis la base de donnée

## Monitoring
- datadrift récupérer le fichier depuis S3 dans trained -> A tester
- generation du rapport... -> failed demander GitHub Copilot -> Later
- visualisation dans Evidently AI
- grafana avec donnée actuelles

# cleaning
**Ajouter** un `__init__.py` dans chaque répertoire pour des imports propres


# A tester

## Evidently
- J'ai un server EvidentlyAi deployé je pense qu'il faut juste uploader les rapports dans le bucket s3 evidently-reports
- Faire marcher la detection de drift avec S3
- Est-ce que l'on compare bien les bons datasets?
- Data Drift (Drift Detection Action) -> Tester la documentation

## Data 
- Verifier les fichiers sources
- Vérifier les fichier généré dans S3
- Vérifier la creation des parquet dans S3

## slidev
- Verifier la Documentation pour bloc 4

## Db
- Quels informations sont stockée en base de données? Quels pipelines utilise la base de données predictions?
- Il y a t'il un documentation pour documenter les interraction avec la table prediction?  


# Fait? -> A Challenger avec le prof
- Orchestration airflow qui déclenche GitHub Actions
- Prediction (inférence) inclue dans le pipeline pour être executé une seule fois dans un environnement temporaire
- deployement (ou streamlit) fait via le lancement des pipeline Retraining et Prediction provoqué par les Workflows?



# Nice to have

# A Nettoyer
- Faire marcher les scripts restants
- get_production_data_for_retraining peut être renommé en get_production_data
- Clean vacances etc...
- Renommer les fichiers initiaux pour suivre le format date_xxx.parquet

# A faire
- Gérer correctement la preparation du premier training
-- Identifier que c'est le premier training

# Plus tard
- email notifier
- config.yaml pour les différents environnements
- Réparer base de donnée neon airflai (via un import de celle de jinsudai? Essayer plutot airflow db reset --yes)
- Faire en sorte que chaque pipeline soit un service ?
- Loki pour collecter les logs ?
- Fast API qui contient tout le ML pour une orchestration peu gourmande avec l'orchestrateur qui appelle les endpoints








CI & CD issues

deployement docker avec:
Streamlit / EvidentlyAI ou UI / Airflow
Base de donnée externes / Mlflow Externe

EvidentlyUI -> Erreur dockerfile
Traceback (most recent call last):
  File "/app/main.py", line 10, in <module>
    from evidently.ui.dashboards import DashboardPanelPlot, DashboardPanelCounter, ReportFilter
ModuleNotFoundError: No module named 'evidently.ui.dashboards'
Traceback (most recent call last):
  File "/app/main.py", line 10, in <module>
    from evidently.ui.dashboards import DashboardPanelPlot, DashboardPanelCounter, ReportFilter
ModuleNotFoundError: No module named 'evidently.ui.dashboards'



QU'est ce qu'il manque dans le projet pour respecter le besoin suivant:
Description: Faire en sorte de respecter le cahier des charges
Créer un algorithme d'Intelligence Artificielle adapté aux données d'entraînement et conforme aux spécifications du cahier des charges, en veillant à répondre aux besoins spécifiques, notamment en termes d'accessibilité.
Adapter l'infrastructure de données de l'organisation à travers la construction d'API pour accueillir la solution d'IA en production.
Concevoir des pipelines d'intégration et déploiement continu pour automatiser le processus de déploiement d'une solution d'IA.
Développer des scripts de réentrainement des modèles pour automatiser le processus de Machine Learning.
Piloter la performance de la solution d'IA dans l'infrastructure à travers la mise en place d'outils de monitoring (comme Aporia ou Evidently) pour s'assurer qu'elle respecte les spécifications du cahier des charges dans un environnement de production.



Basé sur mon analyse du projet, voici ce qui manque pour respecter le cahier des charges:

1. API pour accueillir la solution d'IA en production ❌ CRITIQUE
État actuel: FastAPI est dans Services/_disabled/FastApi/ - non activé

Manque:

Aucune API REST active pour les prédictions en temps réel
Pas d'endpoint /predict pour consommation
Pas d'endpoint /predict pour production solaire
Pas d'endpoint /health pour monitoring
Pas d'endpoint /model-info pour informations modèle -> plus tard
Action requise: Activer et compléter le service FastAPI avec endpoints pour:

Prédictions consommation
Prédictions production solaire
Monitoring santé du service
Version des modèles
2. Pipelines CI/CD ❌ CRITIQUE
État actuel: Seulement des workflows GitHub pour HuggingFace Spaces

Manque:

Pas de workflow GitHub Actions pour:
Tests automatiques (pytest)
Build Docker images
Déploiement automatique des modèles
Validation du code (linting, formatting)
Pas de pipeline de déploiement continu
Pas de tests d'intégration automatisés
Action requise: Créer des workflows GitHub Actions pour:

.github/workflows/ci.yml - tests et validation
.github/workflows/cd.yml - build et déploiement
.github/workflows/model-deploy.yml - déploiement modèles MLflow
3. Modèle de Production Solaire ⚠️ PARTIEL
État actuel: src/ml/solar_production/ ne contient qu'un __init__.py vide

Manque:

Pas de solar_production_preparer.py (équivalent de consumption_preparer.py)
Pas de DAG Airflow pour production solaire
Pas de tests spécifiques pour production solaire
Action requise: Implémenter le module solar_production/ avec:

Tâches d'entraînement
Tâches de préparation features
DAG Airflow complet
Tests unitaires
4. Monitoring avec Evidently/Aporia ⚠️ PARTIEL
État actuel: Code existe mais notebooks Evidently dans _disabled

Manque:

Pas de dashboard de monitoring en production
Pas d'alertes automatiques configurées
Pas de rapports HTML générés automatiquement
Pas d'intégration avec Aporia (seulement Evidently partiel)
Notebooks Evidently désactivés
Action requise:

Activer et intégrer Evidently en production
Créer dashboard de monitoring (Streamlit ou autre)
Configurer des alertes automatiques par email
Générer des rapports réguliers
5. Scripts de réentrainement ✅ PRÉSENT
État actuel: Implémenté dans prediction_tasks.py et drift_detector.py

Présent:

Tâche retrain_model_task dans prediction_tasks.py
Détection de drift avec drift_detector.py
Pipeline de retraining conditionnel
Tests dans test_retraining_pipeline.py
Statut: ✅ Cette exigence est respectée

6. Accessibilité ❌ NON TRAITÉ
État actuel: Aucune mention dans le code ou la documentation

Manque:

Pas de considérations d'accessibilité dans l'API
Pas de documentation accessible
Pas d'interface utilisateur accessible
Action requise: Ajouter des considérations d'accessibilité selon les normes WCAG

Résumé des priorités
CRITIQUE (bloquant pour production):
Activer et implémenter FastAPI
Créer pipelines CI/CD
IMPORTANT:
Implémenter le module solar_production complet
Activer le monitoring Evidently en production
MOYEN:
Ajouter l'accessibilité
Créer dashboard de monitoring