Pour Devin

Config -> A tester
- Chercher d'abord la variable d'environnement ENVIRONMENT avant de chercher à utiliser le .env
- Renseigner ServicesNames dans le fichier de config et ne plus y faire reference dans le .env. Adapter le code dans .github.
- J'ai ajouté la notion de satelite dans le config.yaml. il faudrait pouvoir gérer les espaces et les secrets avec un HF_Token différent en cherchant le secret SATELITENAME_HF_TOKEN en l'occurence AIRFLOW_HF_TOKEN

S3 -> A tester
- Est-ce que parfois on a  plusieurs periodes de fichiers {start_date}_to_{end_date}_.parquet et on les combines pour former un train.parquet?
- Pas besoin de différencier le chemin selon l'environnement -> A tester
- utiliser {date}_train.parquet à la place de consumption_features_{date}.parquet -> A tester
- Pas besoin de la copy train_consumption.parquet -> prendre toujours le fichier avec la date la plus récente -> A tester
- Le prefix weather doit servir pour stocker le fichier parquet de la meteo {date}_weather.parquet -> A tester


Prediction pipeline refinment: Problème de config
- Le même code a été dupliqué plusieurs fois. Il faut utiliser la class config (je crois) à la place -> A tester

Data Drift (Drift Detection Action) -> En cours
- Proposer une manière d'executer le réentrainement -> Executé
- Je n'ai pas conserver le Dag Airflow l'idée est d'avoir un GitHub Action

A faire
- Marp
- Connexion à S3
- Ordonnancement dans GitHub ou via Airflow?
- Utilisation de FastAPI par Streamlit -> A tester

- grafana

A tester
- Tester le passage des secrets airflow
- Faire marcher la detection de drift avec S3
Evidently 
Streamlit
deployement

A vérifier
- prepare consumption pipelines

A faire (later)
- J'ai ajouté la notion de satelite externe...
- Réparer base de donnée neon jinsudai
- airflow peut orchestrer Github via des pushs git
- Faire fonctionner prefect en local
- Faire en sorte que chaque pipeline soit un service -> Sauvegarder le projet
- Evidently -> Il faut stocker aussi les données météo pour le data drift -> Idealement oui
- Loki pour collecter les logs ?
- pb de URI Database non poussé avec Airflow?


Idées
- Renomage de FastAPI en inference-service
- Fast API qui contient tout le ML pour une orchestration peu gourmande
  L'orchestrateur qui appelle les endpoints








CI & CD issues

deployement docker avec:
Streamlit / EvidentlyAI ou UI / Prefect interne
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




CI/CD erreur comment faire dans le cas d'une library?
build-and-push (Airflow)
buildx failed with: ERROR: failed to build: failed to solve: failed to compute cache key: failed to calculate checksum of ref kiw59aulbykum0484mn3adpwg::1iikn05edexob1twkcj67a028: "/src": not found

poetry env activate
C:\Users\SustCoop\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\Local\pypoetry\Cache\virtualenvs\ml-6PV5fMfH-py3.11\Scripts\activate.ps1
streamlit run .\services\EvidentlyAI\main.py
-> Erreur lors du chargement des rapports: 'str' object has no attribute 'info'

FastApi
Peux tu ecrire un guide pour utiliser FastApi
-> Comment le tester


Pas de 30minutes???? Doublon dans la base de données...



Documentation
-> Docsify?

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

Pas de solar_production_tasks.py (équivalent de consumption_tasks.py)
Pas de solar_production_preparer.py (équivalent de consumption_preparer.py)
Pas de flow Prefect pour production solaire
Pas de tests spécifiques pour production solaire
Action requise: Implémenter le module solar_production/ avec:

Tâches d'entraînement
Tâches de préparation features
Flow Prefect complet
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