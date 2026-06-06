"""
Gestion de l'API météo pour générer un fichier parquet réutilisable.

Spécifications :
- Source : API Open-Meteo (données historiques et prévisions météo)
- Format sortie : Parquet avec colonnes standardisées
- Colonnes générées : temperature_2m_mean, relative_humidity_mean, precipitation_sum
- Utilisation : Prédiction consommation électrique et production solaire
- Validation : Vérification des valeurs manquantes et plages de valeurs

Fonctions principales :
- WeatherAPI.fetch_historical() : Récupère historique météo pour une période
- WeatherAPI.generate_parquet() : Génère fichier parquet réutilisable
- WeatherAPI.validate_data() : Valide la qualité des données
"""

import os
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta
import json

import pandas as pd
import numpy as np
import requests


class WeatherAPI:
    """
    Classe pour gérer l'accès à l'API Open-Meteo et générer des données météo.
    
    Attributs:
        base_url (str): URL de base de l'API Open-Meteo
        latitude (float): Latitude du point d'intérêt
        longitude (float): Longitude du point d'intérêt
        location_name (str): Nom de la localisation (pour logs)
        timeout (int): Timeout en secondes pour les requêtes HTTP
    """
    
    def __init__(
        self,
        latitude: float = 48.8566,  # Paris par défaut
        longitude: float = 2.3522,
        location_name: str = "Paris",
        timeout: int = 30
    ):
        """
        Initialise le gestionnaire API météo.
        
        Args:
            latitude: Latitude de la localisation (défaut: Paris)
            longitude: Longitude de la localisation (défaut: Paris)
            location_name: Nom descriptif de la localisation
            timeout: Timeout en secondes pour les requêtes HTTP
        """
        self.base_url = "https://archive-api.open-meteo.com/v1/archive"
        self.latitude = latitude
        self.longitude = longitude
        self.location_name = location_name
        self.timeout = timeout
        self.data = None
    
    def fetch_historical(
        self,
        start_date: str,
        end_date: str,
        hourly: bool = True
    ) -> pd.DataFrame:
        """
        Récupère les données météo historiques de Open-Meteo.
        
        Args:
            start_date: Date de début au format YYYY-MM-DD
            end_date: Date de fin au format YYYY-MM-DD
            hourly: Si True, récupère données horaires; sinon journalières
        
        Returns:
            DataFrame pandas avec colonnes temporelles et météo
        
        Raises:
            requests.RequestException: En cas d'erreur API
            ValueError: Si paramètres invalides
        """
        # Validation des dates
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if start > end:
                raise ValueError(f"start_date ({start_date}) > end_date ({end_date})")
        except ValueError as e:
            print(f"Erreur format date : {e}")
            raise
        
        # Construction des paramètres de requête
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "Europe/Paris"
        }
        
        # Ajout des variables météo à récupérer
        if hourly:
            params["hourly"] = "temperature_2m,relative_humidity_2m,precipitation"
        else:
            params["daily"] = "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum"
        
        print(f"[{self.location_name}] Récupération données {start_date} à {end_date}...")
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Vérification présence données
            if "hourly" not in data and "daily" not in data:
                raise ValueError("Aucune donnée météo reçue de l'API")
            
            print(f"✓ {len(data.get('hourly', {}).get('time', []))} enregistrements récupérés")
            
            return self._parse_weather_data(data, hourly)
        
        except requests.RequestException as e:
            print(f"Erreur API : {e}")
            raise
    
    def _parse_weather_data(self, data: dict, hourly: bool = True) -> pd.DataFrame:
        """
        Parse les données météo brutes de l'API en DataFrame structuré.
        
        Args:
            data: Dictionnaire réponse de l'API
            hourly: Si True, utilise données horaires; sinon journalières
        
        Returns:
            DataFrame avec colonnes standardisées
        """
        if hourly:
            times = data["hourly"]["time"]
            temps = pd.to_datetime(times)
            
            df = pd.DataFrame({
                "Horodate": temps,
                "temperature_2m_mean": np.array(data["hourly"]["temperature_2m"], dtype=float),
                "relative_humidity_mean": np.array(data["hourly"]["relative_humidity_2m"], dtype=float),
                "precipitation_sum": np.array(data["hourly"]["precipitation"], dtype=float)
            })
        else:
            times = data["daily"]["time"]
            temps = pd.to_datetime(times)
            
            df = pd.DataFrame({
                "Horodate": temps,
                "temperature_2m_mean": np.array(data["daily"]["temperature_2m_mean"], dtype=float),
                "relative_humidity_mean": np.array(data["daily"]["relative_humidity_2m_mean"], dtype=float),
                "precipitation_sum": np.array(data["daily"]["precipitation_sum"], dtype=float)
            })
        
        self.data = df
        return df
    
    def validate_data(self) -> dict:
        """
        Valide la qualité des données météo récupérées.
        
        Vérifications :
        - Absence de valeurs manquantes
        - Plages de valeurs normales (température, humidité)
        - Cohérence temporelle
        
        Returns:
            Dictionnaire avec résultats validation :
            - is_valid (bool): True si données valides
            - errors (list): Liste des erreurs détectées
            - warnings (list): Liste des avertissements
            - stats (dict): Statistiques descriptives
        """
        if self.data is None:
            return {
                "is_valid": False,
                "errors": ["Aucune donnée chargée"],
                "warnings": [],
                "stats": {}
            }
        
        errors = []
        warnings = []
        
        # Vérification colonnes
        colonnes_attendues = ["Horodate", "temperature_2m_mean", "relative_humidity_mean", "precipitation_sum"]
        colonnes_manquantes = [col for col in colonnes_attendues if col not in self.data.columns]
        if colonnes_manquantes:
            errors.append(f"Colonnes manquantes : {colonnes_manquantes}")
        
        # Vérification valeurs manquantes
        for col in ["temperature_2m_mean", "relative_humidity_mean", "precipitation_sum"]:
            if col in self.data.columns:
                pct_null = self.data[col].isnull().sum() / len(self.data) * 100
                if pct_null > 5:  # Max 5% selon spécifications
                    errors.append(f"{col} : {pct_null:.1f}% valeurs manquantes (max 5%)")
                elif pct_null > 0:
                    warnings.append(f"{col} : {pct_null:.2f}% valeurs manquantes")
        
        # Vérification plages de valeurs
        temp_col = "temperature_2m_mean"
        if temp_col in self.data.columns and not self.data[temp_col].isnull().all():
            temp_min = self.data[temp_col].min()
            temp_max = self.data[temp_col].max()
            # Plages réalistes pour France: -15 à +45°C
            if temp_min < -30 or temp_max > 50:
                warnings.append(f"Température anormale : [{temp_min:.1f}, {temp_max:.1f}]°C")
        
        hum_col = "relative_humidity_mean"
        if hum_col in self.data.columns and not self.data[hum_col].isnull().all():
            hum_min = self.data[hum_col].min()
            hum_max = self.data[hum_col].max()
            if hum_min < 0 or hum_max > 100:
                errors.append(f"Humidité invalide : [{hum_min:.1f}, {hum_max:.1f}]% (attendu [0, 100])")
        
        # Vérification cohérence temporelle
        if "Horodate" in self.data.columns and len(self.data) > 1:
            diffs = self.data["Horodate"].diff().dropna()
            mode_diff = diffs.mode()
            if len(mode_diff) > 0:
                # Fréquence attendue
                expected_freq = mode_diff[0]
                if expected_freq != timedelta(hours=1) and expected_freq != timedelta(days=1):
                    warnings.append(f"Fréquence temporelle inhabituelle : {expected_freq}")
        
        # Statistiques
        stats = {
            "n_records": len(self.data),
            "date_min": str(self.data["Horodate"].min()) if "Horodate" in self.data.columns else None,
            "date_max": str(self.data["Horodate"].max()) if "Horodate" in self.data.columns else None,
            "temperature_stats": {
                "mean": float(self.data[temp_col].mean()) if temp_col in self.data.columns else None,
                "min": float(self.data[temp_col].min()) if temp_col in self.data.columns else None,
                "max": float(self.data[temp_col].max()) if temp_col in self.data.columns else None,
            },
            "precipitation_sum": float(self.data["precipitation_sum"].sum()) if "precipitation_sum" in self.data.columns else None,
        }
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": stats
        }
    
    def generate_parquet(
        self,
        output_path: Optional[str] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Génère un fichier parquet réutilisable avec les données météo.
        
        Args:
            output_path: Chemin du répertoire de sortie (défaut : data/processed/)
            filename: Nom du fichier (défaut : weather_<location>_YYYY-MM-DD.parquet)
        
        Returns:
            Chemin complet du fichier généré
        
        Raises:
            ValueError: Si aucune donnée disponible
            IOError: En cas d'erreur d'écriture
        """
        if self.data is None or self.data.empty:
            raise ValueError("Aucune donnée chargée. Appelez d'abord fetch_historical()")
        
        # Construction du chemin de sortie
        if output_path is None:
            output_path = Path(__file__).resolve().parents[3] / "data" / "processed"
        else:
            output_path = Path(output_path)
        
        # Création du répertoire s'il n'existe pas
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Construction du nom de fichier
        if filename is None:
            date_min = self.data["Horodate"].min().strftime("%Y-%m-%d")
            date_max = self.data["Horodate"].max().strftime("%Y-%m-%d")
            filename = f"weather_{self.location_name}_{date_min}_{date_max}.parquet"
        
        filepath = output_path / filename
        
        # Sauvegarde en parquet
        try:
            self.data.to_parquet(filepath, index=False, compression="snappy")
            print(f"✓ Fichier généré : {filepath}")
            print(f"  - Taille : {len(self.data)} enregistrements")
            print(f"  - Colonnes : {list(self.data.columns)}")
            return str(filepath)
        
        except IOError as e:
            print(f"Erreur écriture fichier : {e}")
            raise
    
    def to_csv(
        self,
        output_path: Optional[str] = None,
        filename: Optional[str] = None,
        separator: str = ";"
    ) -> str:
        """
        Exporte les données météo en CSV (format compatible avec template).
        
        Args:
            output_path: Chemin du répertoire de sortie
            filename: Nom du fichier
            separator: Séparateur CSV (défaut : ";")
        
        Returns:
            Chemin complet du fichier généré
        """
        if self.data is None or self.data.empty:
            raise ValueError("Aucune donnée chargée")
        
        if output_path is None:
            output_path = Path(__file__).resolve().parents[3] / "data" / "processed"
        else:
            output_path = Path(output_path)
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        if filename is None:
            date_min = self.data["Horodate"].min().strftime("%Y-%m-%d")
            date_max = self.data["Horodate"].max().strftime("%Y-%m-%d")
            filename = f"weather_{self.location_name}_{date_min}_{date_max}.csv"
        
        filepath = output_path / filename
        
        self.data.to_csv(
            filepath,
            sep=separator,
            index=False,
            encoding="utf-8"
        )
        print(f"✓ Fichier CSV généré : {filepath}")
        return str(filepath)
