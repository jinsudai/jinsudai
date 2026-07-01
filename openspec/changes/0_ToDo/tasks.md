# Pour Devin

## Tâches de fond:
Eviter les sauts de ligne inutiles

# A faire
Améliorer les Logs du Monitoring Pipeline -> A tester
Ordonnées les Workflow GitHubActions? -> CD à tester
Générer les test Unitaires -> A la toute fin -> consomme des tokens
Générer des test d'intégration -> A la toute fin -> consomme des tokens

## question

## documentation
- actualiser la documentation en verifiant ce qui est pertinent à documenter
-- Orchestration airflow qui déclenche GitHub Actions
-- Prediction (inférence) inclue dans le pipeline pour être executé une seule fois dans un environnement temporaire
-- Db?


# Nice to have

Ordonencement GitHubAction

## Documentation
- simplification doc EvidentlyUI / Guide d'utilisation détaillé fait doublon?
- Readme MLflow / AirFlow
- ReadMe src perfectible

## prepare Consumption prepare -> En cours
- vérifier si pas code en double pour récupéré les  valeurs réelle depuis la base de donnée -> Doublon consumption_preparer.py et preparation.py? get_predictions...
- Simplifier l'ingestion: get_predictions_by_date(start_date, end_date) non necessaire

# A Nettoyer
- Faire marcher les scripts restants
- Clean vacances etc... Revoir holidays_api
- Renommer les fichiers initiaux pour suivre le format date_xxx.parquet

# A faire
- Gérer correctement la preparation du premier training
-- Identifier que c'est le premier training

# Plus tard
- Reusable workflow pour la CI/CD des services et plus tard pour chaque entité
- Email sender dans une variable d'environnent
- fichier de config différent pour les services. (evite de le trigger)
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

3. Pipelines CI/CD
- Tests d'intégration automatisés -> test d'intégration en testant les pipelines individuellement (GitHub Actions)
- Déploiement production non configuré (placeholder dans cd.yml) -> Deployement HuggingFace possibilité de lancer les script Hugging Face depuis le GitHub Action CD

4. Scripts de réentrainement ⚠️ PARTIELLEMENT PRÉSENT
- Pas de trigger automatique reliant détection de drift → retraining → promotion -> Voir si on peut le faire avec Airflow
- Le monitoring détecte le drift mais ne lance pas automatiquement le retraining -> Idem

5. Monitoring ⚠️ PARTIELLEMENT PRÉSENT
Pas de dashboards Grafana configurés -> Cloud -> Documenter en donnant le lien https://jenedai.grafana.net/public-dashboards/c609cf4eab1a495883ce1c5bc25b51f1?from=now-7d&to=now&timezone=browser
Pas de monitoring du système de monitoring lui-même -> via airflow on peut voir si il y a des erreurs -> Possibilité d'ajouter l'envois d'un email

6. Accessibilité ❌ MANQUANT
Pas d'UI accessible (Streamlit mentionnée mais non implémentée) -> Ne pas le mentioné 
Pas de documentation sur l'accessibilité / Pas de tests d'accessibilité -> Pas d'UI, juste Dashboard Grafana et API
