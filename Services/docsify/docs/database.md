# Schéma de la Base de Données - PostgreSQL

## Table `consumption_predictions`

### Structure

```sql
CREATE TABLE consumption_predictions (
    prediction_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    target_timestamp TIMESTAMP NOT NULL,
    prediction DOUBLE PRECISION,
    model_version TEXT,
    entity_id TEXT NOT NULL,
    run_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actual_value DOUBLE PRECISION,
    CONSTRAINT unique_target_entity UNIQUE (target_timestamp, entity_id)
);
```

### Description des colonnes

| Colonne | Type | Description | Nullable |
|---------|------|-------------|----------|
| `prediction_id` | BIGINT | Identifiant unique auto-incrémenté de la prédiction (clé primaire) | NON |
| `target_timestamp` | TIMESTAMP | Timestamp de la prédiction (quand la prédiction a été faite) | NON |
| `prediction` | DOUBLE PRECISION | Valeur prédite en kWh (consommation ou production) | OUI |
| `model_version` | TEXT | Version du modèle utilisé pour la prédiction | OUI |
| `entity_id` | TEXT | Identifiant de l'entité (client PRM ou site de production) | NON |
| `run_id` | TEXT | ID du run MLflow associé à la prédiction | OUI |
| `created_at` | TIMESTAMP | Timestamp de création de l'enregistrement en base | NON |
| `actual_value` | DOUBLE PRECISION | Valeur réelle observée (remplie ultérieurement pour monitoring) | OUI |

### Index

```sql
CREATE INDEX idx_consumption_predictions_target_timestamp ON consumption_predictions (target_timestamp);
CREATE INDEX idx_consumption_predictions_entity_id ON consumption_predictions (entity_id);
CREATE INDEX idx_consumption_predictions_run_id ON consumption_predictions (run_id);
```

### Vue triée

```sql
CREATE VIEW consumption_predictions_sorted AS
SELECT * FROM consumption_predictions
ORDER BY target_timestamp DESC;
```

---

## Classe `DatabaseHandler`

### Localisation

`src/ml/utils/data/database_handler.py`

### Méthodes disponibles

#### `__init__(db_uri=None)`
Initialise le handler avec l'URI de connexion PostgreSQL.

**Paramètres :**
- `db_uri` (str, optional) : URI de connexion PostgreSQL (ex: `postgresql://user:password@host:port/database`)

---

#### `verify_connection()`
Vérifie la connexion à la base de données.

**Retourne :**
- `True` si connexion réussie
- `False` sinon

---

#### `create_tables()`
Crée la table `consumption_predictions` avec ses index et la vue triée.

**Comportement :**
- Utilise `CREATE TABLE IF NOT EXISTS` pour éviter les erreurs si la table existe déjà
- Crée les index sur les colonnes fréquemment utilisées
- Crée la vue `consumption_predictions_sorted` pour un accès trié par timestamp

**Retourne :**
- `True` si création réussie
- `False` sinon

---

#### `store_predictions(df_predictions, model_version, run_id=None)`
Stocke un DataFrame de prédictions dans la table.

**Paramètres :**
- `df_predictions` (pd.DataFrame) : DataFrame contenant les prédictions avec colonnes :
  - `target_timestamp` (requis) : Timestamp de la prédiction
  - `prediction` (requis)
- `model_version` (str) : Version du modèle utilisé
- `run_id` (str, optional) : ID du run MLflow

**Comportement :**
- Utilise `ON CONFLICT (target_timestamp, entity_id) DO UPDATE` pour mettre à jour les prédictions existantes
- Insère en batch avec `execute_batch` pour la performance
- `entity_id` est codé en dur à `"550e8400-e29b-41d4-a716-446655440000"`
- `run_id` est codé en dur à `"6ba7b810-9dad-11d1-80b4-00c04fd430c8"` si non fourni

**Retourne :**
- `True` si stockage réussi
- `False` sinon

---

#### `get_recent_predictions(limit=100)`
Récupère les N prédictions les plus récentes.

**Paramètres :**
- `limit` (int, default=100) : Nombre maximum de prédictions à récupérer

**Retourne :**
- `pd.DataFrame` avec les colonnes : `prediction_id`, `target_timestamp`, `prediction`, `model_version`, `entity_id`, `run_id`, `created_at`
- `None` en cas d'erreur

---

#### `get_prediction_stats()`
Récupère les statistiques de la table.

**Retourne :**
- `dict` avec `total_predictions` (int) et `table_exists` (bool)
- `None` en cas d'erreur

---

#### `get_predictions_by_date(start_date, end_date)`
Récupère les prédictions pour une plage de dates.

**Paramètres :**
- `start_date` (datetime ou str) : Date de début
- `end_date` (datetime ou str) : Date de fin

**Retourne :**
- `pd.DataFrame` avec les colonnes : `prediction_id`, `target_timestamp`, `prediction`, `model_version`, `entity_id`, `run_id`, `actual_value`
- `None` en cas d'erreur

---

#### `get_predictions_for_drift_detection(limit=100, start_date=None, end_date=None)`
Récupère les prédictions pour la détection de drift (colonnes utiles uniquement).

**Paramètres :**
- `limit` (int, default=100) : Nombre maximum d'enregistrements
- `start_date` (datetime ou str, optional) : Date de début
- `end_date` (datetime ou str, optional) : Date de fin

**Retourne :**
- `pd.DataFrame` avec les colonnes : `target_timestamp`, `prediction`, `actual_value`
- `None` en cas d'erreur

**Filtre :**
- Ne retourne que les enregistrements où `actual_value IS NOT NULL`
- Si start_date et end_date sont fournis, filtre par plage de dates

---

#### `update_actual_values(prediction_ids, actual_values)`
Met à jour les valeurs réelles pour les prédictions données.

**Paramètres :**
- `prediction_ids` (list) : Liste des IDs de prédictions à mettre à jour
- `actual_values` (list) : Liste des valeurs réelles correspondantes

**Comportement :**
- Met à jour la colonne `actual_value` pour chaque prediction_id
- Les deux listes doivent avoir la même longueur

**Retourne :**
- `True` si mise à jour réussie
- `False` sinon

---

#### `insert_predictions_with_actual_values(target_timestamps, actual_values, entity_id)`
Insère des enregistrements avec target_timestamp et actual_value uniquement.

**Paramètres :**
- `target_timestamps` (list) : Liste des timestamps cibles
- `actual_values` (list) : Liste des valeurs réelles
- `entity_id` (str) : ID de l'entité

**Comportement :**
- Utilise `ON CONFLICT (target_timestamp, entity_id) DO UPDATE` pour mettre à jour les valeurs existantes
- Les deux listes doivent avoir la même longueur

**Retourne :**
- `True` si insertion réussie
- `False` sinon

---

#### `add_actual_value_column()`
Ajoute la colonne `actual_value` si elle n'existe pas déjà.

**Utilité :**
- Migration pour les tables existantes créées avant l'ajout de cette colonne

**Retourne :**
- `True` si ajout réussi ou colonne existe déjà
- `False` sinon

---

#### `get_production_data(limit=None, include_prediction=True)`
Récupère les données de production avec valeurs réelles pour le retraining.

**Paramètres :**
- `limit` (int, optional) : Nombre maximum d'enregistrements
- `include_prediction` (bool, default=True) : Si True, inclut la colonne prediction

**Retourne :**
- `pd.DataFrame` avec les colonnes : `target_timestamp`, `actual_value` (et `prediction` si include_prediction=True)
- `None` en cas d'erreur

**Filtre :**
- Ne retourne que les enregistrements où `actual_value IS NOT NULL`

---

## Exemples d'utilisation

### Initialisation et création de table

```python
from ml.pipelines.database_handler import DatabaseHandler

# Initialisation
db_handler = DatabaseHandler(db_uri="postgresql://user:password@localhost:5432/mydb")

# Vérifier la connexion
if db_handler.verify_connection():
    print("Connexion réussie")

# Créer la table
if db_handler.create_tables():
    print("Table créée avec succès")
```

### Stocker des prédictions

```python
import pandas as pd

# DataFrame de prédictions
df_predictions = pd.DataFrame({
    'target_timestamp': pd.date_range('2024-01-01', periods=48, freq='30min'),
    'prediction': [100.5, 102.3, 98.7, ...],  # 48 valeurs
})

# Stocker
db_handler.store_predictions(
    df_predictions=df_predictions,
    model_version="v1.0.0",
    run_id="abc123"
)
```

### Récupérer les prédictions récentes

```python
# Récupérer les 10 dernières prédictions
recent = db_handler.get_recent_predictions(limit=10)
print(recent)
```

### Récupérer par plage de dates

```python
from datetime import datetime

# Récupérer les prédictions pour janvier 2024
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 1, 31)
predictions = db_handler.get_predictions_by_date(start_date, end_date)
```

### Mettre à jour les valeurs réelles

```python
# IDs des prédictions à mettre à jour
prediction_ids = ['uuid1', 'uuid2', 'uuid3']
actual_values = [105.2, 98.5, 102.1]

db_handler.update_actual_values(prediction_ids, actual_values)
```

### Récupérer les données pour retraining

```python
# Récupérer les 1000 derniers enregistrements avec valeurs réelles
training_data = db_handler.get_production_data(limit=1000)

# Récupérer sans la colonne prediction
training_data_no_pred = db_handler.get_production_data(limit=1000, include_prediction=False)
```

### Récupérer les données pour drift detection

```python
# Récupérer les 100 derniers enregistrements avec valeurs réelles
drift_data = db_handler.get_predictions_for_drift_detection(limit=100)

# Récupérer pour une plage de dates spécifique
from datetime import datetime
drift_data = db_handler.get_predictions_for_drift_detection(
    limit=1000,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31)
)
```

### Insérer des valeurs réelles

```python
# Insérer des enregistrements avec target_timestamp et actual_value
target_timestamps = pd.date_range('2024-01-01', periods=48, freq='30min')
actual_values = [100.5, 102.3, 98.7, ...]  # 48 valeurs

db_handler.insert_predictions_with_actual_values(
    target_timestamps=target_timestamps,
    actual_values=actual_values,
    entity_id="550e8400-e29b-41d4-a716-446655440000"
)
```

---

## Notes importantes

### ID et doublons
- `prediction_id` est un BIGINT auto-incrémenté (IDENTITY), pas un UUID
- La clause `ON CONFLICT (target_timestamp, entity_id) DO UPDATE` permet de mettre à jour les prédictions existantes au lieu de créer des doublons
- **Contrainte UNIQUE** : Il y a une contrainte UNIQUE sur la combinaison (`target_timestamp`, `entity_id`), empêchant les doublons métier

### Timestamps
- `target_timestamp` : Quand la prédiction a été faite (timestamp métier) - **REQUIS**
- `created_at` : Quand l'enregistrement a été créé en base (timestamp système)

### entity_id
- Actuellement codé en dur à `"550e8400-e29b-41d4-a716-446655440000"` dans `store_predictions`
- À modifier pour utiliser l'entity_id réel du client ou du site

### run_id
- Actuellement codé en dur à `"6ba7b810-9dad-11d1-80b4-00c04fd430c8"` si non fourni
- Devrait être passé depuis le modèle MLflow pour la traçabilité
