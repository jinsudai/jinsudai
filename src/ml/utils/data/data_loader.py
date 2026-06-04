"""
Chargement et préparation des données.

Spécifications (voir SPECIFICATIONS.md) :
- Source : Fichiers CSV depuis data/raw/
- Format : UTF-8, séparateur virgule ou point-virgule (PRM)
- Structure : Features PRM, météo, calendrier + cible Valeur (kWh)
- Validation : Vérification des colonnes et types
- Valeurs manquantes : Max 5% par feature

Fonctions principales :
- load_data() : Charge CSV depuis data/raw/
- Retourne : DataFrame pandas avec contrôle qualité
"""
import pandas as pd
import numpy as np
from pathlib import Path

from ml.config import load_config


def load_data(file_path):
    """Charge les données depuis un fichier CSV"""
    data = pd.read_csv(file_path, sep=",", lineterminator="\n", encoding="utf-8")
    try:
        data = pd.read_csv(file_path, sep=",", lineterminator="\n", encoding="utf-8")
        # data = pd.read_csv(file_path, sep=None, engine="python")
        print(f"Données chargées avec succès_: {file_path}")
        print(f"Forme des données: {data.shape}")
        print(f"Colonnes: {list(data.columns)}")
        print(f"Types: {data.dtypes.to_dict()}")
        print(f"Head: {data.head(5)}")
        print("Attention: Moins de 2 colonnes détectées, vérifier le séparateur")
        # Vérifier les données
        if data.empty:
            print("Attention: Le fichier est vide")

        if data.isnull().sum().sum() > 0:
            print(f"Attention: {data.isnull().sum().sum()} valeurs manquantes détectées")
        
        return data
    except FileNotFoundError:
        print(f"Erreur: Fichier non trouvé - {file_path}")
        return None
    except Exception as e:
        print(f"Erreur lors du chargement: {e}")
        return None





def save_data(data, file_path):
    """Sauvegarde les données dans un fichier CSV"""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(file_path, index=False)
    print(f"Données sauvegardées: {file_path}")
