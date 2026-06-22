# Schéma de la Base de Données - PostgreSQL

## Table `predictions_pipeline`

### Structure

```sql
CREATE TABLE predictions_pipeline (
    prediction_id UUID PRIMARY KEY,
    prediction_timestamp TIMESTAMP NOT NULL,
    prediction_index INTEGER NOT NULL,
    prediction DOUBLE PRECISION NOT NULL,
    model_version TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actual_value DOUBLE PRECISION
);
```

### Description des colonnes

| Colonne | Type | Description | Nullable |
|---------|------|-------------|----------|
| `prediction_id` | UUID | Identifiant unique de la prédiction (clé primaire) | NON |
| `prediction_timestamp` | TIMESTAMP | Timestamp de la prédiction (quand la prédiction a été faite) | NON |
| `prediction_index` | INTEGER | Index de la prédiction (pour différencier plusieurs prédictions par timestamp) | NON |
| `prediction` | DOUBLE PRECISION | Valeur prédite en kWh (consommation ou production) | NON |
| `model_version` | TEXT | Version du modèle utilisé pour la prédiction | NON |
| `entity_id` | TEXT | Identifiant de l'entité (client PRM ou site de production) | NON |
| `run_id` | TEXT | ID du run MLflow associé à la prédiction | NON |
| `created_at` | TIMESTAMP | Timestamp de création de l'enregistrement en base | NON |
| `actual_value` | DOUBLE PRECISION | Valeur réelle observée (remplie ultérieurement pour monitoring) | OUI |

### Index

```sql
CREATE INDEX idx_predictions_pipeline_prediction_timestamp ON predictions_pipeline (prediction_timestamp);
CREATE INDEX idx_predictions_pipeline_prediction_index ON predictions_pipeline (prediction_index);
CREATE INDEX idx_predictions_pipeline_entity_id ON predictions_pipeline (entity_id);
CREATE INDEX idx_predictions_pipeline_run_id ON predictions_pipeline (run_id);
```

### Vue triée

```sql
CREATE VIEW predictions_pipeline_sorted AS
SELECT * FROM predictions_pipeline
ORDER BY prediction_timestamp DESC;
```

---

## Classe `DatabaseHandler`

### Localisation

`src/ml/pipelines/database_handler.py`

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
Crée la table `predictions_pipeline` avec ses index et la vue triée.

**Comportement :**
- Utilise `CREATE TABLE IF NOT EXISTS` pour éviter les erreurs si la table existe déjà
- Crée les index sur les colonnes fréquemment utilisées
- Crée la vue `predictions_pipeline_sorted` pour un accès trié par timestamp

**Retourne :**
- `True` si création réussie
- `False` sinon

---

#### `store_predictions(df_predictions, model_version, run_id=None)`
Stocke un DataFrame de prédictions dans la table.

**Paramètres :**
- `df_predictions` (pd.DataFrame) : DataFrame contenant les prédictions avec colonnes :
  - `prediction_timestamp` ou `horodate` ou `timestamp` (optionnel, généré si absent)
  - `prediction_index` (optionnel, généré si absent)
  - `prediction` (requis)
- `model_version` (str) : Version du modèle utilisé
- `run_id` (str, optional) : ID du run MLflow

**Comportement :**
- Génère un UUID pour chaque prédiction
- Gère les colonnes de timestamp automatiquement
- Utilise `ON CONFLICT (prediction_id) DO NOTHING` pour éviter les doublons d'UUID
- Insère en batch avec `execute_batch` pour la performance

**Retourne :**
- `True` si stockage réussi
- `False` sinon

---

#### `get_recent_predictions(limit=100)`
Récupère les N prédictions les plus récentes.

**Paramètres :**
- `limit` (int, default=100) : Nombre maximum de prédictions à récupérer

**Retourne :**
- `pd.DataFrame` avec les colonnes : `prediction_id`, `prediction_timestamp`, `prediction`, `model_version`, `entity_id`, `run_id`, `created_at`
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
- `pd.DataFrame` avec les colonnes : `prediction_id`, `prediction_timestamp`, `prediction_index`, `prediction`, `model_version`, `entity_id`, `run_id`, `actual_value`
- `None` en cas d'erreur

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

#### `add_actual_value_column()`
Ajoute la colonne `actual_value` si elle n'existe pas déjà.

**Utilité :**
- Migration pour les tables existantes créées avant l'ajout de cette colonne

**Retourne :**
- `True` si ajout réussi ou colonne existe déjà
- `False` sinon

---

#### `get_production_data_for_retraining(limit=None)`
Récupère les données de production avec valeurs réelles pour le retraining.

**Paramètres :**
- `limit` (int, optional) : Nombre maximum d'enregistrements

**Retourne :**
- `pd.DataFrame` avec les colonnes : `prediction_timestamp`, `prediction`, `actual_value`
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
    'prediction_timestamp': pd.date_range('2024-01-01', periods=48, freq='30min'),
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
training_data = db_handler.get_production_data_for_retraining(limit=1000)
```

---

## Notes importantes

### UUID et doublons
- Chaque prédiction reçoit un UUID unique généré par `uuid.uuid4()`
- La clause `ON CONFLICT (prediction_id) DO NOTHING` empêche les insertions avec le même UUID
- **Attention :** Il n'y a PAS de contrainte UNIQUE sur les champs métier (`prediction_timestamp`, `entity_id`), donc des doublons métier peuvent exister

### Timestamps
- `prediction_timestamp` : Quand la prédiction a été faite (timestamp métier)
- `created_at` : Quand l'enregistrement a été créé en base (timestamp système)
- Si `prediction_timestamp` est absent, il est déduit de `horodate`, `timestamp`, ou utilise l'heure actuelle

### entity_id
- Actuellement codé en dur à `"550e8400-e29b-41d4-a716-446655440000"` dans `store_predictions`
- À modifier pour utiliser l'entity_id réel du client ou du site

### run_id
- Actuellement codé en dur à `"6ba7b810-9dad-11d1-80b4-00c04fd430c8"` si non fourni
- Devrait être passé depuis le modèle MLflow pour la traçabilité

---

## Migration et maintenance

### Ajouter la colonne actual_value (si absent)

```python
db_handler.add_actual_value_column()
```

### Recréer la table (suppression des données)

```python
# Attention : cela supprime toutes les données existantes
# À utiliser uniquement en développement ou si les données ne sont pas importantes
db_handler.create_tables()  # Note : actuellement ne supprime PAS la table existante
```

Pour supprimer et recréer la table, il faut exécuter manuellement :

```sql
DROP TABLE IF EXISTS predictions_pipeline CASCADE;
```

Puis appeler `create_tables()`.
