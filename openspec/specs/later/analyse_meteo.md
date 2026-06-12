# Spec: Stockage des données météo

## Contexte
Nous stockons les valeurs de consommation énergétique, mais pas les données météo brutes.

## Question
Est-il nécessaire de stocker les données météo réelles ?

## Première analyse
- Les données météo peuvent être recalculées via API externe
- Risque : dépendance externe et incohérences historiques
- Avantage de stockage : reproductibilité des modèles

## Hypothèses
- Stockage uniquement des features dérivées pourrait suffire
- Les données brutes ne sont peut-être pas nécessaires

## Décision
À trancher lors de l’architecture data globale




Nous stockonsles valeurs réélle de consommation dans la base de donnée mais pas les données réelles de météo. Est ce problématique?

Thought for 2s

Je vais analyser votre système pour comprendre comment les données météo sont utilisées et si leur stockage est nécessaire.

Explored2 files and searched 2 queries

Thought for 2s

Read`consumption_preparer.py` and 3 other files

Thought for 7s

Read`Actual_values_pipeline.py` and `SPECIFICATIONS.md`

Thought for 5s

Basé sur l'analyse de votre codebase, voici mon évaluation :

## Situation actuelle

**Stocké dans la BD** (

database_handler.py) :

- Prédictions de consommation
    
- **Valeurs réelles de consommation** (`actual_value`)
    

**Non stocké dans la BD** :

- Données météo réelles
    

Les données météo sont stockées dans des fichiers Parquet (

weather.parquet) et utilisées comme features pour l'entraînement/prédiction.

## Est-ce problématique ?

### **NON problématique pour :**

- **Calcul des métriques de performance** : Vous comparez déjà `prediction` vs `actual_value` pour calculer R², MAE, RMSE
    
- **Réentraînement du modèle** : Les données météo historiques sont disponibles dans les fichiers Parquet
    
- **Monitoring basique** : Les spécifications mentionnent le suivi de R², MAE, RMSE qui ne nécessitent pas les météo réelles
    

### **PROBLÉMATIQUE pour :**

- **Analyse des erreurs** : Impossible de déterminer si une erreur vient d'une mauvaise prédiction météo ou du modèle lui-même
    
- **Drift detection des features météo** : Impossible de détecter si la distribution météo a changé (ex: températures anormalement hautes)
    
- **Audit complet** : Pour retracer exactement quelles conditions météo ont conduit à quelle prédiction/erreur
    
- **Amélioration du modèle** : Difficile d'identifier les patterns d'erreur liés à des conditions météo spécifiques
    

## Recommandation

**Pour l'instant : Ce n'est pas critique** car votre pipeline actuel fonctionne pour les besoins de base (monitoring R², réentraînement).

**À terme : Je recommande d'ajouter le stockage des météo réelles** si vous voulez :

- Faire de l'analyse d'errors avancée
    
- Détecter le drift des features météo
    
- Avoir une traçabilité complète