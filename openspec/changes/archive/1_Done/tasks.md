# A Nettoyer
- Enlever les exemples donnés pour les connecteurs si non pertinent -> les mettre dans Script
- get_production_data_for_retraining peut être renommé en get_production_data

## Monitoring
- datadrift récupérer le fichier depuis S3 dans prepared (et non le reference)) -> Fait
- autre drifts -> Fait
- email notification -> Fait

## Pipelines
# 1_actuals_ingestion_pipeline (Daily)
- Peux tu me confirmer que si le ftp n'est pas activé, les donnnées sont générée aléatoirement? -> A tester
- Peux tu me confirmer que la base de donnée est bien actualisée avec les données réelles? -> A tester

# 2_preparation_pipeline (Daily)
- Est-ce qu'il determine la date du dernier entrainement automatiquement? oui  -> A tester
- Est-ce que les nouvelles données de meteo sont bien sauvegarder dans un {date}_weather.parquet? oui  -> A tester
- Est-ce qu'il récupère bien les valeurs depuis la base de donnée et génère bien le fichier {date}_train.parquet du jour  enregistré sur s3 sous le prefix /consumption/train/ oui -> A tester

# 3_training-pipeline (3 jours)
- Est-ce qu'une fois l'entrainement terminé (model chargé sur mlflow), le fichier {date}_train.parquet est bien transférer sur s3 dans le prefix "/consumption/trained/"

# 6_retraining (Daily)
- Est-ce que le fichier source est bien le fichier /consumption/trained/{date}_train.parquet" le plus recent

# Config -> A tester
- J'ai ajouté la notion de satelite dans le config.yaml. il faudrait pouvoir gérer les espaces et les secrets avec un HF_Token différent en cherchant le secret SATELITENAME_HF_TOKEN en l'occurence AIRFLOW_HF_TOKEN -> A tester
- Il y a confusion entre les deux fichier config.yaml. Je pense qu'il est mieux d'avoir seulement celui à la racine du projet. -> A tester
- Chercher d'abord la variable d'environnement ENVIRONMENT avant de chercher à utiliser le .env -> A tester
- Renseigner ServicesNames dans le fichier de config et ne plus y faire reference dans le .env. Adapter le code dans .github. -> A tester

## S3 -> A demander
- Pas besoin de différencier le chemin selon l'environnement -> A tester
- utiliser {date}_train.parquet -> A tester
- prendre toujours le fichier avec la date la plus récente -> A tester
- Le prefix weather doit servir pour stocker le fichier parquet de la meteo {date}_weather.parquet -> A tester