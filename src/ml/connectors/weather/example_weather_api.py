"""
Exemple d'utilisation de la classe WeatherAPI.

Script permettant de :
1. Récupérer les données météo historiques
2. Valider les données
3. Générer un fichier parquet réutilisable
4. Exporter en CSV si nécessaire

Utilisation :
    python src/ml/utils/api/example_weather_api.py
"""

from pathlib import Path
from analytics.utils.api.weather.weather_api import WeatherAPI


def main():
    """Exemple complet d'utilisation de WeatherAPI."""

    # Configuration
    locations = [
        {"lat": 48.8566, "lon": 2.3522, "name": "Paris"},
        # {"lat": 45.1667, "lon": 5.7167, "name": "Grenoble"},
        # {"lat": 43.2965, "lon": 5.3698, "name": "Marseille"},
    ]

    start_date = "2024-01-01"
    end_date = "2024-12-31"

    # Récupération données pour chaque localisation
    for loc in locations:
        print(f"\n{'='*60}")
        print(f"Traitement : {loc['name']}")
        print(f"{'='*60}")

        # Initialisation API
        weather = WeatherAPI(
            latitude=loc["lat"],
            longitude=loc["lon"],
            location_name=loc["name"]
        )

        # Récupération données historiques (données horaires)
        try:
            df = weather.fetch_historical(
                start_date=start_date,
                end_date=end_date,
                hourly=True
            )
            print(f"\nPremières lignes des données :")
            print(df.head(10))
            print(f"\nInformations données :")
            print(f"  - Période : {start_date} à {end_date}")
            print(f"  - Enregistrements : {len(df)}")
            print(f"  - Colonnes : {list(df.columns)}")

        except Exception as e:
            print(f"✗ Erreur récupération données : {e}")
            continue

        # Validation des données
        print(f"\nValidation des données...")
        validation = weather.validate_data()

        print(f"  - Valide : {validation['is_valid']}")
        if validation["errors"]:
            print(f"  - Erreurs :")
            for err in validation["errors"]:
                print(f"    • {err}")
        if validation["warnings"]:
            print(f"  - Avertissements :")
            for warn in validation["warnings"]:
                print(f"    • {warn}")

        # Affichage statistiques
        print(f"\nStatistiques :")
        stats = validation["stats"]
        print(f"  - Nombre d'enregistrements : {stats['n_records']}")
        print(f"  - Période : {stats['date_min']} à {stats['date_max']}")
        temp_stats = stats["temperature_stats"]
        print(f"  - Température : {temp_stats['min']:.1f}°C à {temp_stats['max']:.1f}°C (moy: {temp_stats['mean']:.1f}°C)")
        print(f"  - Précipitations totales : {stats['precipitation_sum']:.1f} mm")

        # Génération fichier parquet
        if validation["is_valid"]:
            print(f"\nGénération fichier parquet...")
            try:
                filepath = weather.generate_parquet()
                print(f"✓ Fichier généré avec succès")

                # Export CSV optionnel
                print(f"\nGénération fichier CSV...")
                csv_path = weather.to_csv()
                print(f"✓ Fichier CSV généré avec succès")

            except Exception as e:
                print(f"✗ Erreur génération fichier : {e}")
        else:
            print(f"\n✗ Données invalides - pas de fichier généré")


if __name__ == "__main__":
    main()
