"""
Module API pour accès aux données externes (météo, vacances, jours fériés).

Classes :
- WeatherAPI : Gestion API Open-Meteo pour données météo

Utilisation :
    from ml.utils.api import WeatherAPI

    weather = WeatherAPI(latitude=48.8566, longitude=2.3522, location_name="Paris")
    df = weather.fetch_historical("2024-01-01", "2024-12-31")
    weather.validate_data()
    weather.generate_parquet()
"""

from .weather_api import WeatherAPI

__all__ = ["WeatherAPI"]
