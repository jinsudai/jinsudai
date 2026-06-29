## 1. WeatherAPI

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

# Récupération prévisions météo (lendemain par défaut)
df_forecast = weather.fetch_forecast(
    forecast_days=1,  # 1 jour = lendemain
    hourly=True
)

# Récupération prévisions sur plusieurs jours (jusqu'à 16)
df_forecast_week = weather.fetch_forecast(
    forecast_days=7,  # 7 jours
    hourly=True
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
