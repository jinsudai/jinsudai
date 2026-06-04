# NE pas modifier ce fichier directement, il doit être remplacer par l'usage de la librarie


"""
Transformation des données avant entraînement ou inférence.
Permet de supprimer les colonnes configurées dans le YAML, de nettoyer les noms,
 et de transformer les colonnes de date.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def drop_columns(data: pd.DataFrame, columns_to_drop):
    """Supprime les colonnes listées dans la configuration.

    Args:
        data: DataFrame à transformer
        columns_to_drop: liste des colonnes à supprimer

    Returns:
        DataFrame avec les colonnes supprimées
    """
    if data is None:
        raise ValueError("Aucune donnée fournie pour la suppression des colonnes")

    unnamed_columns = [col for col in data.columns if str(col).strip() == "" or str(col).startswith("Unnamed")]
    if unnamed_columns:
        logger.info(f"Détection de colonnes sans nom: {unnamed_columns}")

    if columns_to_drop is None:
        columns_to_drop = []

    if not isinstance(columns_to_drop, (list, tuple)):
        raise ValueError("drop_columns attend une liste de noms de colonnes")

    missing_columns = [col for col in columns_to_drop if col not in data.columns]
    columns_to_drop = [col for col in columns_to_drop if col in data.columns]

    if missing_columns:
        logger.warning(f"Colonnes à supprimer non trouvées dans les données: {missing_columns}")

    all_columns_to_drop = unnamed_columns + columns_to_drop
    if not all_columns_to_drop:
        logger.info("Aucune colonne valide à supprimer après vérification")
        return data.copy()

    transformed = data.drop(columns=all_columns_to_drop)
    logger.info(f"Supprimé {len(all_columns_to_drop)} colonne(s): {all_columns_to_drop}")
    return transformed


def clean_data(data: pd.DataFrame, columns_to_drop=None, transform_dates=True, drop_original_dates=True):
    """Nettoie les données en supprimant colonnes définies, noms vides et formats de dates.

    Args:
        data: DataFrame à transformer
        columns_to_drop: liste des colonnes à supprimer
        transform_dates: bool, si True transforme les colonnes datetime
        drop_original_dates: bool, si True supprime les colonnes datetime originales

    Returns:
        DataFrame nettoyé
    """
    if data is None:
        raise ValueError("Aucune donnée fournie pour le nettoyage")

    cleaned = data.copy()
    cleaned.columns = cleaned.columns.str.strip()

    cleaned = drop_columns(cleaned, columns_to_drop)

    if transform_dates:
        cleaned = transform_date_columns(cleaned, drop_original=drop_original_dates)

    cleaned.columns = cleaned.columns.str.strip()
    logger.info("Nettoyage des données terminé")
    return cleaned


def transform_date_columns(data: pd.DataFrame, drop_original=True):
    """Détecte et transforme automatiquement les colonnes dates."""
    if data is None:
        raise ValueError("Aucune donnée fournie pour la transformation des dates")

    data = data.copy()

    # Détection automatique des colonnes potentiellement datetime
    for col in data.columns:
        try:
            converted = pd.to_datetime(data[col], format="%Y-%m-%d %H:%M:%S", errors='coerce')
            if converted.notna().sum() > 0:
                data[col] = converted
        except Exception:
            continue

    datetime_cols = data.select_dtypes(include=['datetime64[ns]']).columns

    for col in datetime_cols:
        data[f"{col}_month"] = data[col].dt.month
        data[f"{col}_hour"] = data[col].dt.hour
        data[f"{col}_weekday"] = data[col].dt.weekday
        data[f"{col}_is_weekend"] = (data[col].dt.weekday >= 5).astype(int)

    if drop_original and len(datetime_cols) > 0:
        data.drop(columns=datetime_cols, inplace=True)

    return data