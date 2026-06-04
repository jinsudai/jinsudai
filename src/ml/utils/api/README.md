# Module API - Gestion des données externes

Module pour accès centralisé aux APIs externes (météo, vacances, jours fériés) et génération de fichiers parquet réutilisables.

## Architecture

```
src/ml/utils/api/
├── weather_api.py          # ✓ Classe WeatherAPI (implémentée)
├── vacances_api.py         # TODO: Classe VacancesAPI
├── jours_feries_api.py     # TODO: Classe JoursFeriesAPI
├── example_weather_api.py  # Exemple d'utilisation
└── __init__.py
```

## 1. WeatherAPI ✓ (Implémentée)

Classe pour récupérer et gérer les données météo via [Open-Meteo](https://open-meteo.com/).

### Caractéristiques

- **Source** : API Open-Meteo (données historiques + prévisions)
- **Variables** : température, humidité relative, précipitations
- **Format sortie** : Parquet + CSV
- **Validation** : Vérification valeurs manquantes et plages

### Utilisation

```python
from ml.utils.api import WeatherAPI

# Initialisation pour Paris
weather = WeatherAPI(
    latitude=48.8566,
    longitude=2.3522,
    location_name="Paris"
)

# Récupération données historiques (2024)
df = weather.fetch_historical(
    start_date="2024-01-01",
    end_date="2024-12-31",
    hourly=True  # Données horaires
)

# Validation
validation = weather.validate_data()
print(f"Données valides : {validation['is_valid']}")
print(f"Statistiques : {validation['stats']}")

# Génération fichier parquet
weather.generate_parquet(
    output_path="data/processed/",
    filename="weather_paris_2024.parquet"
)

# Export CSV optionnel
weather.to_csv(
    output_path="data/processed/",
    separator=";"  # Format template
)
```

### Colonnes générées

| Colonne | Type | Description |
|---------|------|-------------|
| `Horodate` | datetime | Timestamp (UTC) |
| `temperature_2m_mean` | float | Température en °C |
| `relative_humidity_mean` | float | Humidité relative en % |
| `precipitation_sum` | float | Cumul précipitations en mm |

### Validation automatique

```python
validation_result = weather.validate_data()
# Retourne :
# {
#   "is_valid": bool,
#   "errors": [...],      # Erreurs bloquantes
#   "warnings": [...],    # Avertissements
#   "stats": {            # Statistiques descriptives
#     "n_records": int,
#     "date_min": str,
#     "date_max": str,
#     "temperature_stats": {...},
#     "precipitation_sum": float
#   }
# }
```

### Exemple d'exécution

```bash
cd src/ml/utils/api/
python example_weather_api.py
```

Résultat attendu :
```
============================================================
Traitement : Paris
============================================================
[Paris] Récupération données 2024-01-01 à 2024-12-31...
✓ 8784 enregistrements récupérés

Premières lignes des données :
            Horodate  temperature_2m_mean  relative_humidity_mean  precipitation_sum
0 2024-01-01 00:00:00                 5.5                    75.0                0.0
1 2024-01-01 01:00:00                 4.8                    78.0                0.0
...

Validation des données...
  - Valide : True
  - Avertissements :
    • Aucun

Statistiques :
  - Nombre d'enregistrements : 8784
  - Période : 2024-01-01 00:00:00 à 2024-12-31 23:00:00
  - Température : -12.5°C à 35.2°C (moy: 11.3°C)
  - Précipitations totales : 652.3 mm

✓ Fichier parquet généré : data/processed/weather_Paris_2024-01-01_2024-12-31.parquet
✓ Fichier CSV généré : data/processed/weather_Paris_2024-01-01_2024-12-31.csv
```

## 2. VacancesAPI (TODO)

Classe pour récupérer les dates de vacances scolaires.

### Source

- **API** : [GitHub - vacances-scolaires](https://raw.githubusercontent.com/AntoineAugusti/vacances-scolaires/refs/heads/master/data.csv)
- **Données** : Vacances scolaires par zones (A, B, C)

### Utilisation envisagée

```python
from ml.utils.api import VacancesAPI

vacances = VacancesAPI()
df = vacances.fetch(year=2024)
df.to_parquet("data/processed/vacances_2024.parquet")
```

### Colonnes attendues

| Colonne | Type | Description |
|---------|------|-------------|
| `start_date` | date | Début vacances |
| `end_date` | date | Fin vacances |
| `zone` | string | Zone A, B ou C |
| `type` | string | Type (hiver, printemps, etc.) |

## 3. JoursFeriesAPI (TODO)

Classe pour récupérer les jours fériés en France.

### Source

- **API** : [calendrier.api.gouv.fr](https://calendrier.api.gouv.fr/jours-feries/metropole/)
- **Données** : Jours fériés nationaux

### Utilisation envisagée

```python
from ml.utils.api import JoursFeriesAPI

jours_feries = JoursFeriesAPI()
df = jours_feries.fetch(year=2024)
df.to_parquet("data/processed/jours_feries_2024.parquet")
```

### Exemple API

```javascript
// Exemple de réponse API
// GET https://calendrier.api.gouv.fr/jours-feries/metropole/2024.json

{
  "Jour de l'an": "2024-01-01",
  "Lundi de Pâques": "2024-04-01",
  "Fête du Travail": "2024-05-01",
  "Victoire 1945": "2024-05-08",
  "Ascension": "2024-05-09",
  "Lundi de Pentecôte": "2024-05-20",
  "Fête nationale": "2024-07-14",
  "Assomption": "2024-08-15",
  "Toussaint": "2024-11-01",
  "Armistice 1918": "2024-11-11",
  "Noël": "2024-12-25"
}
```

## Pipeline d'utilisation

Utilisation typique dans les pipelines :

```
1. fetch_historical() / fetch()     → Récupération données API
2. validate_data()                  → Vérification qualité
3. generate_parquet() / to_csv()    → Export fichier réutilisable
4. data_transformer.py              → Intégration dans pipeline ML
```

## Dépendances requises

```
requests>=2.28.0    # Requêtes HTTP
pandas>=1.5.0       # DataFrames
numpy>=1.23.0       # Calculs numériques
pyarrow>=10.0.0     # Compression parquet
```

## Notes

- Toutes les dates sont en UTC (timezone Europe/Paris pour Open-Meteo)
- Les fichiers parquet utilisent compression Snappy
- Validation : Max 5% valeurs manquantes par feature (specs SPECIFICATIONS.md)
- Export CSV : Séparateur ";" pour compatibilité template



#Source vacances
https://www.data.gouv.fr/api/1/datasets/r/c3781037-dffb-4789-9af9-15a955336771 -> Lien vers l'url suivante
https://raw.githubusercontent.com/AntoineAugusti/vacances-scolaires/refs/heads/master/data.csv
-> Idealement faire une API pour obtenir juste les années souhaitées


#source jours fériés
async function getJoursFeriesDeuxAnnees(annee1, annee2) {
    const [r1, r2] = await Promise.all([
        fetch(`https://calendrier.api.gouv.fr/jours-feries/metropole/${annee1}.json`),
        fetch(`https://calendrier.api.gouv.fr/jours-feries/metropole/${annee2}.json`)
    ]);

    const jf1 = await r1.json();
    const jf2 = await r2.json();

    return { ...jf1, ...jf2 };
}

getJoursFeriesDeuxAnnees(2026, 2027)
    .then(console.log);