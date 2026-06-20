"""
Guide d'intégration de WeatherAPI dans le pipeline ML.

Ce script montre comment intégrer les données météo dans les pipelines
de prédiction (consommation + production solaire).

Utilisation :
    python src/ml/utils/api/integration_example.py
"""

from pathlib import Path
import sys

# Ajout du répertoire src au path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
try:
    from analytics.utils.api.weather.weather_api import WeatherAPI
except ImportError:
    from ml.utils.api import WeatherAPI


def integrate_weather_for_consumption():
    """
    Intègre les données météo pour le domaine consommation électrique.

    Pipeline :
    1. Récupère données météo (Open-Meteo)
    2. Charge données consommation brutes
    3. Fusionne sur horodate
    4. Valide qualité données
    5. Exporte fichier préparé
    """
    print("=" * 70)
    print("INTÉGRATION MÉTÉO - CONSOMMATION ÉLECTRIQUE")
    print("=" * 70)

    # Paramètres localisation
    # À adapter selon point de mesure
    locations = {
        "Paris": {"lat": 48.8566, "lon": 2.3522},
        "Grenoble": {"lat": 45.1667, "lon": 5.7167},
        "Marseille": {"lat": 43.2965, "lon": 5.3698},
    }

    for location_name, coords in locations.items():
        print(f"\n[{location_name}] Préparation données...")

        # 1. Initialisation API météo
        weather = WeatherAPI(
            latitude=coords["lat"],
            longitude=coords["lon"],
            location_name=location_name
        )

        # 2. Récupération données historiques
        try:
            weather_df = weather.fetch_historical(
                start_date="2024-01-01",
                end_date="2024-12-31",
                hourly=True
            )
            print(f"  ✓ {len(weather_df)} enregistrements météo récupérés")
        except Exception as e:
            print(f"  ✗ Erreur récupération météo : {e}")
            continue

        # 3. Validation données météo
        validation = weather.validate_data()
        if not validation["is_valid"]:
            print(f"  ✗ Données météo invalides : {validation['errors']}")
            continue
        print("  ✓ Données météo validées")

        # 4. Simulation chargement données consommation
        # (À remplacer par load_data() du module data)
        print("  → Simul. données consommation...")
        consumption_df = pd.DataFrame({
            "Horodate": weather_df["Horodate"],
            "Valeur": [300 + i % 200 for i in range(len(weather_df))],  # Fictif
        })

        # 5. Fusion données météo + consommation
        merged_df = consumption_df.merge(
            weather_df[[
                "Horodate",
                "temperature_2m_mean",
                "relative_humidity_mean",
                "precipitation_sum"
            ]],
            on="Horodate",
            how="left"
        )

        print(f"  ✓ Données fusionnées : {len(merged_df)} lignes")
        print(f"    Colonnes : {list(merged_df.columns)}")

        # 6. Export fichier préparé
        try:
            output_path = Path("data/processed")
            output_path.mkdir(parents=True, exist_ok=True)

            filename = f"consumption_{location_name}_weather_2024.parquet"
            filepath = output_path / filename

            merged_df.to_parquet(filepath, index=False, compression="snappy")
            print(f"  ✓ Fichier généré : {filepath}")

            # Affichage aperçu
            print("\n  Aperçu données (5 premières lignes) :")
            print(merged_df.head().to_string())

        except Exception as e:
            print(f"  ✗ Erreur export : {e}")


def integrate_weather_for_solar():
    """
    Intègre les données météo pour le domaine production solaire.

    La production solaire nécessite variables spécifiques :
    - Rayonnement global (irradiance)
    - Couverture nuageuse

    Note : Open-Meteo fournit limited support irradiance.
    Pour données complètes, envisager API spécialisée (PVGIS, CAMS).
    """
    print("\n" + "=" * 70)
    print("INTÉGRATION MÉTÉO - PRODUCTION SOLAIRE")
    print("=" * 70)

    # Localisation site solaire
    location_name = "Grenoble_Solar"
    lat, lon = 45.1667, 5.7167

    print(f"\n[{location_name}] Préparation données...")

    # 1. Initialisation API météo
    weather = WeatherAPI(
        latitude=lat,
        longitude=lon,
        location_name=location_name
    )

    # 2. Récupération données
    try:
        weather_df = weather.fetch_historical(
            start_date="2024-01-01",
            end_date="2024-12-31",
            hourly=True
        )
        print(f"  ✓ {len(weather_df)} enregistrements météo récupérés")
    except Exception as e:
        print(f"  ✗ Erreur : {e}")
        return

    # 3. Validation
    validation = weather.validate_data()
    if not validation["is_valid"]:
        print(f"  ✗ Données invalides : {validation['errors']}")
        return
    print("  ✓ Données validées")

    # 4. Simulation données production solaire
    print("  → Simul. données production solaire...")
    solar_df = pd.DataFrame({
        "Horodate": weather_df["Horodate"],
        "Production_kWh": [
            max(0, 500 - 100 * i % 600) for i in range(len(weather_df))
        ],  # Fictif
    })

    # 5. Fusion
    merged_df = solar_df.merge(
        weather_df[[
            "Horodate",
            "temperature_2m_mean",
            "relative_humidity_mean",
            "precipitation_sum"
        ]],
        on="Horodate",
        how="left"
    )

    print(f"  ✓ Données fusionnées : {len(merged_df)} lignes")

    # 6. Export
    try:
        output_path = Path("data/processed")
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"solar_{location_name}_weather_2024.parquet"
        filepath = output_path / filename

        merged_df.to_parquet(filepath, index=False, compression="snappy")
        print(f"  ✓ Fichier généré : {filepath}")

        print(f"\n  Aperçu données (5 premières lignes) :")
        print(merged_df.head().to_string())

    except Exception as e:
        print(f"  ✗ Erreur export : {e}")

    print("\n  ⚠ Note : Pour variables complètes solaire (irradiance, cloud cover),")
    print("    envisager API spécialisée (PVGIS, CAMS ou Weather API premium)")


def main():
    """Exécute l'intégration complète."""

    # Intégration consommation
    integrate_weather_for_consumption()

    # Intégration solaire
    integrate_weather_for_solar()

    # Résumé
    print("\n" + "=" * 70)
    print("RÉSUMÉ INTÉGRATION")
    print("=" * 70)
    print("""
Fichiers générés :
  - data/processed/consumption_*_weather_2024.parquet
  - data/processed/solar_*_weather_2024.parquet

Utilisation dans pipelines ML :
  1. data_loader.py : Charge fichiers parquet générés
  2. data_preparation.py : Nettoyage + normalisation
  3. data_transformer.py : Feature engineering (heure, jour, saison)
  4. training_pipeline.py : Entraînement modèle
  
Pipeline complet (avec vacances + jours fériés) :
  
  WeatherAPI
      ↓
  fetch_historical() → weather_2024.parquet
      ↓
  VacancesAPI (TODO)
      ↓
  fetch() → vacances_2024.parquet
      ↓
  JoursFeriesAPI (TODO)
      ↓
  fetch() → jours_feries_2024.parquet
      ↓
  [Fusion 3 fichiers]
      ↓
  data_transformer.py
      ↓
  features_finales.parquet
      ↓
  training_pipeline.py
""")


if __name__ == "__main__":
    main()
