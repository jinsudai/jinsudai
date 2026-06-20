"""
API pour récupérer les vacances scolaires et jours fériés en France.

Sources :
- Vacances scolaires : https://raw.githubusercontent.com/AntoineAugusti/vacances-scolaires/master/data.csv
- Jours fériés : https://calendrier.api.gouv.fr/jours-feries/metropole/

Exemple d'utilisation :
    from analytics.utils.api.holidays.holidays_api import VacancesAPI, JoursFeriesAPI
    
    vacances = VacancesAPI()
    df_vacances = vacances.fetch(year=2024, zone="C")
    
    jours_feries = JoursFeriesAPI()
    df_feries = jours_feries.fetch(year=2024)
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from pathlib import Path
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Constants
VACANCES_SCOLAIRES_URL = "https://raw.githubusercontent.com/AntoineAugusti/vacances-scolaires/refs/heads/master/data.csv"
JOURS_FERIES_BASE_URL = "https://calendrier.api.gouv.fr/jours-feries/metropole/"


def calculate_easter(year: int) -> datetime:
    """
    Calculate Easter Sunday for a given year using the computus algorithm.

    Args:
        year: Year to calculate Easter for

    Returns:
        datetime object for Easter Sunday
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime(year, month, day)


def parse_french_date(date_str: str, year: int) -> datetime:
    """
    Parse a French date string (e.g., "1er janvier", "25 décembre") into a datetime object.
    Also handles movable holidays like "Lundi de Pâques" and fixed holidays by name.

    Args:
        date_str: French date string or holiday name
        year: Year to use for the date

    Returns:
        datetime object
    """
    # Handle movable holidays
    movable_holidays = {
        'Lundi de Pâques': lambda y: calculate_easter(y) + timedelta(days=1),
        'Jeudi de l\'Ascension': lambda y: calculate_easter(y) + timedelta(days=39),
        'Lundi de Pentecôte': lambda y: calculate_easter(y) + timedelta(days=50),
        'Ascension': lambda y: calculate_easter(y) + timedelta(days=39),
        'Pentecôte': lambda y: calculate_easter(y) + timedelta(days=50),
    }

    if date_str in movable_holidays:
        return movable_holidays[date_str](year)

    # Handle fixed holidays by name
    fixed_holidays = {
        'Assomption': (8, 15),
        'Toussaint': (11, 1),
        'Armistice': (11, 11),
        'Noël': (12, 25),
        'Jour de Noël': (12, 25),
    }

    if date_str in fixed_holidays:
        month, day = fixed_holidays[date_str]
        return datetime(year, month, day)

    # Mapping of French month names to month numbers
    french_months = {
        'janvier': 1,
        'février': 2,
        'mars': 3,
        'avril': 4,
        'mai': 5,
        'juin': 6,
        'juillet': 7,
        'août': 8,
        'septembre': 9,
        'octobre': 10,
        'novembre': 11,
        'décembre': 12
    }

    # Handle "1er" format (1st) - convert to "1"
    date_str = re.sub(r'(\d+)er', r'\1', date_str)

    # Split into day and month
    parts = date_str.strip().split()
    if len(parts) != 2:
        raise ValueError(f"Invalid French date format: {date_str}")

    day = int(parts[0])
    month_name = parts[1].lower()

    if month_name not in french_months:
        raise ValueError(f"Unknown French month: {month_name}")

    month = french_months[month_name]
    return datetime(year, month, day)


class VacancesAPI:
    """
    Classe pour récupérer les dates de vacances scolaires par zone.

    Source : https://github.com/AntoineAugusti/vacances-scolaires
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialise l'API des vacances scolaires.

        Args:
            cache_dir: Répertoire pour cache les données (optionnel)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._raw_data = None

    def _fetch_raw_data(self) -> pd.DataFrame:
        """Récupère les données brutes depuis GitHub."""
        if self._raw_data is not None:
            return self._raw_data

        try:
            response = requests.get(VACANCES_SCOLAIRES_URL, timeout=10)
            response.raise_for_status()

            # Charger CSV depuis l'URL avec les colonnes correctes
            raw_df = pd.read_csv(
                VACANCES_SCOLAIRES_URL,
                sep=",",
                parse_dates=["date"],
                dayfirst=True
            )

            # Transformer le format quotidien en format de périodes (start_date, end_date)
            # Le CSV original a: date, vacances_zone_a, vacances_zone_b, vacances_zone_c, nom_vacances
            # Nous devons le convertir en: start_date, end_date, zone, type

            periods = []

            for zone in ['A', 'B', 'C']:
                zone_col = f"vacances_zone_{zone.lower()}"

                # Trouver les périodes continues de vacances pour cette zone
                in_vacation = False
                start_date = None
                current_nom = ""

                for _, row in raw_df.iterrows():
                    is_vacance = row[zone_col]
                    nom = row.get('nom_vacances', '')

                    if is_vacance and not in_vacation:
                        # Début d'une période de vacances
                        in_vacation = True
                        start_date = row['date']
                        current_nom = nom
                    elif not is_vacance and in_vacation:
                        # Fin d'une période de vacances
                        end_date = row['date']
                        periods.append({
                            'start_date': start_date,
                            'end_date': end_date,
                            'zone': zone,
                            'type': current_nom if current_nom else 'Vacances'
                        })
                        in_vacation = False
                        start_date = None
                        current_nom = ""

                # Si on est toujours en vacances à la fin du dataset
                if in_vacation and start_date is not None:
                    periods.append({
                        'start_date': start_date,
                        'end_date': raw_df['date'].max(),
                        'zone': zone,
                        'type': current_nom if current_nom else 'Vacances'
                    })

            self._raw_data = pd.DataFrame(periods)
            self._raw_data["start_date"] = pd.to_datetime(self._raw_data["start_date"])
            self._raw_data["end_date"] = pd.to_datetime(self._raw_data["end_date"])
            logger.info(f"Données vacances scolaires chargées: {len(self._raw_data)} périodes")
            return self._raw_data

        except requests.RequestException as e:
            logger.error(f"Erreur lors de la récupération des vacances scolaires: {e}")
            raise

    def fetch(
        self,
        year: Optional[Union[int, List[int]]] = None,
        zone: str = "C",
        types: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Récupère les vacances scolaires pour une année et une zone donnée.

        Args:
            year: Année (int) ou liste d'années. Si None, récupère toutes les années.
            zone: Zone scolaire (A, B ou C)
            types: Liste des types de vacances à filtrer (optionnel)
                   Ex: ["hiver", "printemps", "été"]

        Returns:
            DataFrame avec colonnes: start_date, end_date, zone, type
        """
        raw_data = self._fetch_raw_data()

        # Filtrer par année
        if year is None:
            year_data = raw_data.copy()
        elif isinstance(year, int):
            year_data = raw_data[
                (raw_data["start_date"].dt.year == year) |
                (raw_data["end_date"].dt.year == year)
            ].copy()
        elif isinstance(year, list):
            year_data = raw_data[
                raw_data["start_date"].dt.year.isin(year) |
                raw_data["end_date"].dt.year.isin(year)
            ].copy()
        else:
            year_data = raw_data.copy()

        # Filtrer par zone
        if zone:
            year_data = year_data[year_data["zone"] == zone.upper()]

        # Filtrer par type
        if types:
            year_data = year_data[year_data["type"].isin(types)]

        # Reset index
        year_data = year_data.reset_index(drop=True)

        logger.info(f"Vacances scolaires pour {year} (zone {zone}): {len(year_data)} périodes")
        return year_data

    def get_all_years(self, zone: str = "C") -> pd.DataFrame:
        """Récupère toutes les vacances pour toutes les années disponibles."""
        raw_data = self._fetch_raw_data()
        if zone:
            raw_data = raw_data[raw_data["zone"] == zone.upper()]
        return raw_data.reset_index(drop=True)


class JoursFeriesAPI:
    """
    Classe pour récupérer les jours fériés en France métropolitaine.

    Source : https://calendrier.api.gouv.fr/jours-feries/metropole/
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialise l'API des jours fériés.

        Args:
            cache_dir: Répertoire pour cache les données (optionnel)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None

    def fetch(
        self,
        year: Optional[Union[int, List[int]]] = None
    ) -> pd.DataFrame:
        """
        Récupère les jours fériés pour une ou plusieurs années.

        Args:
            year: Année (int) ou liste d'années. Si None, récupère l'année courante.

        Returns:
            DataFrame avec colonnes: date, nom, is_ferie (toujours 1)
        """
        if year is None:
            year = [datetime.now().year]
        elif isinstance(year, int):
            year = [year]

        all_feries = []

        for y in year:
            try:
                url = f"{JOURS_FERIES_BASE_URL}{y}.json"
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                data = response.json()

                for nom, date_str in data.items():
                    all_feries.append({
                        "date": parse_french_date(date_str, y),
                        "nom": nom,
                        "is_ferie": 1
                    })

                logger.info(f"Jours fériés pour {y}: {len(data)} jours")

            except requests.RequestException as e:
                logger.error(f"Erreur lors de la récupération des jours fériés pour {y}: {e}")
                raise

        df = pd.DataFrame(all_feries)
        df = df.sort_values("date").reset_index(drop=True)
        return df

    def fetch_range(
        self,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Récupère les jours fériés entre deux dates.

        Args:
            start_date: Date de début (format: YYYY-MM-DD)
            end_date: Date de fin (format: YYYY-MM-DD)

        Returns:
            DataFrame avec les jours fériés dans la plage
        """
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        # Récupérer toutes les années entre start et end
        years = list(range(start.year, end.year + 1))
        df = self.fetch(years)

        # Filtrer par plage de dates
        mask = (df["date"] >= start) & (df["date"] <= end)
        return df[mask].reset_index(drop=True)


class HolidaysCombinedAPI:
    """
    API combinée pour vacances scolaires + jours fériés.

    Génère un DataFrame prêt à être fusionné avec les données météo,
    avec les colonnes attendues par le template.
    """

    def __init__(self, zone: str = "C"):
        """
        Initialise l'API combinée.

        Args:
            zone: Zone scolaire par défaut (A, B ou C)
        """
        self.vacances_api = VacancesAPI()
        self.jours_feries_api = JoursFeriesAPI()
        self.zone = zone

    def generate_holidays_dataframe(
        self,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Génère un DataFrame avec toutes les colonnes calendar attendues.

        Args:
            start_date: Date de début (YYYY-MM-DD)
            end_date: Date de fin (YYYY-MM-DD)

        Returns:
            DataFrame avec colonnes:
            - Horodate (datetime)
            - is_vacances (int: 0/1)
            - nom_vacances (str: nom de la période ou "")
            - jour de la semaine (str)
            - jour férié (int: 0/1)
        """
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        # 1. Créer plage de dates (toutes les 30 min comme dans le template)
        date_range = pd.date_range(start, end, freq="30min")
        df = pd.DataFrame({"Horodate": date_range})

        # 2. Ajouter jour de la semaine
        df["jour de la semaine"] = df["Horodate"].dt.day_name()

        # 3. Récupérer vacances scolaires
        vacances_df = self.vacances_api.fetch(
            year=list(range(start.year, end.year + 1)),
            zone=self.zone
        )

        # Créer un mapping Horodate -> is_vacances, nom_vacances
        vacances_list = []
        for _, row in vacances_df.iterrows():
            period_dates = pd.date_range(
                row["start_date"],
                row["end_date"],
                freq="30min"
            )
            for date in period_dates:
                vacances_list.append({
                    "Horodate": date,
                    "is_vacances": 1,
                    "nom_vacances": row["type"]
                })

        vacances_mapping = pd.DataFrame(vacances_list)

        # 4. Récupérer jours fériés
        feries_df = self.jours_feries_api.fetch_range(start_date, end_date)
        feries_list = []
        for _, row in feries_df.iterrows():
            # Les jours fériés sont pour toute la journée
            day_dates = pd.date_range(
                row["date"].replace(hour=0, minute=0),
                row["date"].replace(hour=23, minute=30),
                freq="30min"
            )
            for date in day_dates:
                feries_list.append({
                    "Horodate": date,
                    "jour férié": 1
                })

        feries_mapping = pd.DataFrame(feries_list)
        if len(feries_mapping) == 0:
            feries_mapping = pd.DataFrame(columns=["Horodate", "jour férié"])

        # 5. Fusionner vacances
        df = pd.merge(
            df,
            vacances_mapping,
            on="Horodate",
            how="left"
        )
        df["is_vacances"] = df["is_vacances"].fillna(0).astype(int)
        df["nom_vacances"] = df["nom_vacances"].fillna("")

        # 6. Fusionner jours fériés
        df = pd.merge(
            df,
            feries_mapping,
            on="Horodate",
            how="left"
        )
        df["jour férié"] = df["jour férié"].fillna(0).astype(int)

        return df

    def generate_parquet(
        self,
        start_date: str,
        end_date: str,
        output_path: str
    ) -> Path:
        """
        Génère un fichier Parquet avec les données vacances/jours fériés.

        Args:
            start_date: Date de début (YYYY-MM-DD)
            end_date: Date de fin (YYYY-MM-DD)
            output_path: Chemin de sortie

        Returns:
            Path: Chemin vers le fichier Parquet généré
        """
        df = self.generate_holidays_dataframe(start_date, end_date)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df.to_parquet(output_path)
        logger.info(f"Fichier Parquet généré: {output_path}")
        return output_path
