
## Vue d'ensemble

Projet MLOps multi-domaines pour prédiction d'énergie :
- **Consommation électrique** : Prédire la consommation basée sur météo, vacances, jour
- **Production solaire** : Prédire la production PV basée sur météo, irradiance, cloud cover

Orchestration centralisée, réentraînement automatique, monitoring continu.

---

## 1. Modèles

### 1.1 Consommation Électrique

- **Tâche** : Régression (prédiction consommation continue en kWh)
- **Métrique primaire** : R² >= 0.90
- **Métriques secondaires** : MAE, RMSE, MAPE
- **Algorithme** : AutoGluon (regression)
- **Données** : Features météo + calendrier

### 1.2 Production Solaire

- **Tâche** : Régression (prédiction production PV continue en kWh)
- **Métrique primaire** : R² >= 0.92 (solaire plus prévisible)
- **Métriques secondaires** : MAE, RMSE
- **Algorithme** : AutoGluon (regression)
- **Données** : Features météo + irradiance + calendrier

### Performance requise

- **Temps d'inférence** : < 100ms par requête
- **Temps d'entraînement** : < 1h par modèle
- **Taille du modèle** : < 500MB
- **Stockage** : MLflow avec expériments séparées

---

## 2. Données

### 2.1 Consommation Électrique

**Format d'entrée**
- **Type** : CSV (PRM - Point de Mesure)
- **Encoding** : UTF-8
- **Localisation** : `data/raw/`
- **Colonnes** : 
  - `Identifiant PRM` : ID client
  - `Horodate` : Timestamp
  - `Valeur` : Consommation (target)
  - Features météo (temp, humidité, précip)
  - Features calendrier (vacances, jour semaine, jour férié)

### 2.2 Production Solaire

**Format d'entrée**
- **Type** : CSV (PRM - Point de Mesure)
- **Encoding** : UTF-8
- **Localisation** : `data/raw/`
- **Colonnes** :
  - `Identifiant PRM` : ID site
  - `Horodate` : Timestamp
  - `Valeur` : Production (target)
  - Features météo (temp, humidité, irradiance, cloud cover)
  - Features calendrier (vacances, jour semaine, jour férié)

### Qualité attendue
- **Valeurs manquantes** : Max 5% par feature
- **Duplicates** : Vérifiés et supprimés
- **Outliers** : Détectés et gérés selon specs
- **Cohérence temporelle** : Vérifiée (pas de gaps anormaux)

### Validation
- Vérification des schémas (colonnes attendues)
- Vérification des ranges (min/max par feature)
- Vérification du ratio train/test

---

## 3. Pipeline d'entraînement

### Étapes
1. **Data Loading** : Charge depuis `data/raw/`
2. **Data Validation** : Vérification schéma, valeurs manquantes
3. **Data Preparation** : Nettoyage, normalisation
4. **Data Transformation** : Feature engineering
5. **Training** : Entraînement du modèle
6. **Tracking** : Log dans MLflow (métriques, modèle)
7. **Versioning** : Sauvegarde du modèle

### SLA
- **Input** : Données CSV brutes
- **Output** : Modèle versionné dans MLflow + métriques
- **Durée** : < 1h

---

## 4. Pipeline d'inférence

### Endpoint
- **Type** : Batch ou real-time
- **Input** : DataFrame ou CSV avec features PRM, météo et calendrier (voir sections 2.1/2.2)
- **Output** : Prédiction continue en kWh (consommation ou production PV)
- **SLA** : < 100ms par requête

### Validation
- Vérification schéma d'entrée
- Vérification ranges des features
- Rejet si données invalides

---

## 5. Réentraînement

### Triggers - Consommation
- **Déclenché** si R² < 0.88 (drift détecté)
- **Déclenché** tous les 7 jours (cycle normal)
- **Manuel** : via trigger externe

### Triggers - Production Solaire
- **Déclenché** si R² < 0.90 (drift détecté)
- **Déclenché** tous les 7 jours (cycle normal)
- **Manuel** : via trigger externe

### Conditions
- Données nouvelles : >= 1000 exemples
- Performance baseline : comparaison avec modèle courant
- Acceptation : R² nouveaux modèle >= R² courant

---

## 6. Monitoring

### Métriques à tracker - Consommation
- **R²** : Cible >= 0.90
- **MAE** : Suivi continu
- **RMSE** : Suivi continu
- **MAPE** : Suivi continu
- **Temps d'inférence** : Cible < 100ms

### Métriques à tracker - Production Solaire
- **R²** : Cible >= 0.92
- **MAE** : Suivi continu
- **RMSE** : Suivi continu
- **Temps d'inférence** : Cible < 100ms

### Alertes - Consommation
- ⚠️ **Warning** : R² < 0.88
- 🔴 **Critical** : R² < 0.85 → Réentraînement immédiat

### Alertes - Production Solaire
- ⚠️ **Warning** : R² < 0.90
- 🔴 **Critical** : R² < 0.88 → Réentraînement immédiat

### Données à logger
- Chaque prediction : timestamp, features, output
- Chaque entraînement : métriques, hyperparams, données utilisées
- Chaque drift : date, metrique affectée, magnitude
