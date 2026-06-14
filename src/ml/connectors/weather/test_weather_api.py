"""
Tests unitaires pour la classe WeatherAPI.

Tests couverts :
- Initialisation de la classe
- Parsing des données météo
- Validation des données (valeurs normales, plages)
- Génération fichiers (parquet et CSV)

Utilisation :
    pytest src/ml/utils/api/test_weather_api.py -v
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from pathlib import Path
import tempfile
import pandas as pd
import numpy as np
import requests

from src.ml.connectors.weather.weather_api import WeatherAPI


class TestWeatherAPI(unittest.TestCase):
    """Tests pour la classe WeatherAPI."""
    
    def setUp(self):
        """Configuration initiale pour chaque test."""
        self.weather = WeatherAPI(
            latitude=48.8566,
            longitude=2.3522,
            location_name="Paris"
        )
    
    def test_initialization(self):
        """Test l'initialisation de la classe."""
        self.assertEqual(self.weather.latitude, 48.8566)
        self.assertEqual(self.weather.longitude, 2.3522)
        self.assertEqual(self.weather.location_name, "Paris")
        self.assertIsNone(self.weather.data)
    
    def test_parse_weather_data_hourly(self):
        """Test le parsing des données horaires."""
        mock_data = {
            "hourly": {
                "time": ["2024-01-01T00:00", "2024-01-01T01:00"],
                "temperature_2m": [5.0, 4.5],
                "relative_humidity_2m": [80, 82],
                "precipitation": [0.0, 0.1]
            }
        }
        
        df = self.weather._parse_weather_data(mock_data, hourly=True)
        
        self.assertEqual(len(df), 2)
        self.assertIn("Horodate", df.columns)
        self.assertIn("temperature_2m_mean", df.columns)
        self.assertIn("relative_humidity_mean", df.columns)
        self.assertIn("precipitation_sum", df.columns)
        self.assertEqual(df["temperature_2m_mean"].iloc[0], 5.0)
    
    def test_parse_weather_data_daily(self):
        """Test le parsing des données journalières."""
        mock_data = {
            "daily": {
                "time": ["2024-01-01", "2024-01-02"],
                "temperature_2m_mean": [5.0, 6.0],
                "relative_humidity_2m_mean": [80, 82],
                "precipitation_sum": [2.5, 1.2]
            }
        }
        
        df = self.weather._parse_weather_data(mock_data, hourly=False)
        
        self.assertEqual(len(df), 2)
        self.assertEqual(df["temperature_2m_mean"].iloc[0], 5.0)
        self.assertEqual(df["precipitation_sum"].iloc[0], 2.5)
    
    def test_validate_data_no_data(self):
        """Test la validation quand aucune donnée n'est chargée."""
        validation = self.weather.validate_data()
        
        self.assertFalse(validation["is_valid"])
        self.assertIn("Aucune donnée chargée", validation["errors"])
    
    def test_validate_data_valid(self):
        """Test la validation avec données valides."""
        # Création de données valides
        self.weather.data = pd.DataFrame({
            "Horodate": pd.date_range("2024-01-01", periods=10, freq="h"),
            "temperature_2m_mean": np.random.uniform(-10, 30, 10),
            "relative_humidity_mean": np.random.uniform(30, 95, 10),
            "precipitation_sum": np.random.uniform(0, 2, 10)
        })
        
        validation = self.weather.validate_data()
        
        self.assertTrue(validation["is_valid"])
        self.assertEqual(len(validation["errors"]), 0)
        self.assertEqual(validation["stats"]["n_records"], 10)
    
    def test_validate_data_humidity_out_of_range(self):
        """Test la validation avec humidité invalide."""
        self.weather.data = pd.DataFrame({
            "Horodate": pd.date_range("2024-01-01", periods=5, freq="h"),
            "temperature_2m_mean": [5.0] * 5,
            "relative_humidity_mean": [110.0] * 5,  # Invalide: > 100%
            "precipitation_sum": [0.0] * 5
        })
        
        validation = self.weather.validate_data()
        
        self.assertFalse(validation["is_valid"])
        self.assertTrue(any("Humidité invalide" in e for e in validation["errors"]))
    
    def test_validate_data_missing_values(self):
        """Test la validation avec valeurs manquantes excessives."""
        self.weather.data = pd.DataFrame({
            "Horodate": pd.date_range("2024-01-01", periods=100, freq="h"),
            "temperature_2m_mean": [5.0] * 94 + [np.nan] * 6,  # 6% manquantes > 5%
            "relative_humidity_mean": [80.0] * 100,
            "precipitation_sum": [0.0] * 100
        })
        
        validation = self.weather.validate_data()
        
        self.assertFalse(validation["is_valid"])
        self.assertTrue(any("valeurs manquantes" in e.lower() for e in validation["errors"]))
    
    def test_generate_parquet(self):
        """Test la génération du fichier parquet."""
        # Création de données
        self.weather.data = pd.DataFrame({
            "Horodate": pd.date_range("2024-01-01", periods=100, freq="h"),
            "temperature_2m_mean": np.random.uniform(-5, 20, 100),
            "relative_humidity_mean": np.random.uniform(50, 90, 100),
            "precipitation_sum": np.random.uniform(0, 1, 100)
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = self.weather.generate_parquet(
                output_path=tmpdir,
                filename="test.parquet"
            )
            
            # Vérification fichier généré
            self.assertTrue(Path(filepath).exists())
            
            # Vérification contenu
            loaded_df = pd.read_parquet(filepath)
            self.assertEqual(len(loaded_df), 100)
            self.assertEqual(list(loaded_df.columns), [
                "Horodate", "temperature_2m_mean", 
                "relative_humidity_mean", "precipitation_sum"
            ])
    
    def test_generate_parquet_no_data(self):
        """Test que generate_parquet lève erreur sans données."""
        with self.assertRaises(ValueError):
            self.weather.generate_parquet()
    
    def test_to_csv(self):
        """Test l'export en CSV."""
        # Création de données
        self.weather.data = pd.DataFrame({
            "Horodate": pd.date_range("2024-01-01", periods=10, freq="h"),
            "temperature_2m_mean": [5.0] * 10,
            "relative_humidity_mean": [80.0] * 10,
            "precipitation_sum": [0.0] * 10
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = self.weather.to_csv(
                output_path=tmpdir,
                filename="test.csv",
                separator=";"
            )
            
            # Vérification fichier généré
            self.assertTrue(Path(filepath).exists())
            
            # Vérification contenu
            loaded_df = pd.read_csv(filepath, sep=";")
            self.assertEqual(len(loaded_df), 10)
    
    @patch('requests.get')
    def test_fetch_historical_success(self, mock_get):
        """Test la récupération de données historiques réussie."""
        # Mock de la réponse API
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hourly": {
                "time": ["2024-01-01T00:00", "2024-01-01T01:00"],
                "temperature_2m": [5.0, 4.5],
                "relative_humidity_2m": [80, 82],
                "precipitation": [0.0, 0.1]
            }
        }
        mock_get.return_value = mock_response
        
        df = self.weather.fetch_historical("2024-01-01", "2024-01-02")
        
        self.assertEqual(len(df), 2)
        self.assertIsNotNone(self.weather.data)
        mock_get.assert_called_once()
    
    def test_fetch_historical_invalid_dates(self):
        """Test avec dates invalides."""
        with self.assertRaises(ValueError):
            self.weather.fetch_historical("2024-12-31", "2024-01-01")  # start > end
    
    @patch('requests.get')
    def test_fetch_historical_invalid_format(self, mock_get):
        """Test avec format de date invalide."""
        with self.assertRaises(ValueError):
            self.weather.fetch_historical("01/01/2024", "02/01/2024")

    @patch('requests.get')
    def test_fetch_forecast_success(self, mock_get):
        """Test la récupération de prévisions météo réussie."""
        # Mock de la réponse API pour forecast
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hourly": {
                "time": ["2024-01-01T00:00", "2024-01-01T01:00", "2024-01-01T02:00"],
                "temperature_2m": [5.0, 4.5, 4.0],
                "relative_humidity_2m": [80, 82, 84],
                "precipitation": [0.0, 0.1, 0.0]
            }
        }
        mock_get.return_value = mock_response
        
        df = self.weather.fetch_forecast(forecast_days=1, hourly=True)
        
        self.assertEqual(len(df), 3)
        self.assertIsNotNone(self.weather.data)
        self.assertIn("temperature_2m_mean", df.columns)
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_fetch_forecast_daily(self, mock_get):
        """Test la récupération de prévisions météo journalières."""
        # Mock de la réponse API pour forecast daily
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "daily": {
                "time": ["2024-01-01", "2024-01-02"],
                "temperature_2m_mean": [5.0, 6.0],
                "relative_humidity_2m_mean": [80, 82],
                "precipitation_sum": [2.5, 1.2]
            }
        }
        mock_get.return_value = mock_response
        
        df = self.weather.fetch_forecast(forecast_days=2, hourly=False)
        
        self.assertEqual(len(df), 2)
        self.assertEqual(df["temperature_2m_mean"].iloc[0], 5.0)
        self.assertEqual(df["precipitation_sum"].iloc[0], 2.5)

    def test_fetch_forecast_invalid_days_too_low(self):
        """Test fetch_forecast avec nombre de jours invalide (trop bas)."""
        with self.assertRaises(ValueError) as context:
            self.weather.fetch_forecast(forecast_days=0)
        self.assertIn("forecast_days doit être entre 1 et 16", str(context.exception))

    def test_fetch_forecast_invalid_days_too_high(self):
        """Test fetch_forecast avec nombre de jours invalide (trop haut)."""
        with self.assertRaises(ValueError) as context:
            self.weather.fetch_forecast(forecast_days=17)
        self.assertIn("forecast_days doit être entre 1 et 16", str(context.exception))

    @patch('requests.get')
    def test_fetch_forecast_max_days(self, mock_get):
        """Test fetch_forecast avec le maximum de jours (16)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hourly": {
                "time": ["2024-01-01T00:00"],
                "temperature_2m": [5.0],
                "relative_humidity_2m": [80],
                "precipitation": [0.0]
            }
        }
        mock_get.return_value = mock_response
        
        df = self.weather.fetch_forecast(forecast_days=16, hourly=True)
        
        self.assertEqual(len(df), 1)
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_fetch_forecast_api_error(self, mock_get):
        """Test fetch_forecast avec erreur API."""
        mock_get.side_effect = requests.RequestException("API Error")
        
        with self.assertRaises(requests.RequestException):
            self.weather.fetch_forecast(forecast_days=1)


class TestWeatherAPIIntegration(unittest.TestCase):
    """Tests d'intégration (optionnels, avec vraie API)."""
    
    @unittest.skip("Désactivé : nécessite connexion Internet")
    def test_fetch_real_data(self):
        """Test avec vraies données de l'API (intégration)."""
        weather = WeatherAPI(
            latitude=48.8566,
            longitude=2.3522,
            location_name="Paris"
        )
        
        df = weather.fetch_historical("2024-01-01", "2024-01-31", hourly=True)
        
        # Vérifications
        self.assertGreater(len(df), 0)
        self.assertIn("temperature_2m_mean", df.columns)
        
        # Validation
        validation = weather.validate_data()
        self.assertTrue(validation["is_valid"])


if __name__ == "__main__":
    # Exécution des tests
    unittest.main(verbosity=2)
