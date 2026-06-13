"""
Détection de drift avec Evidently AI.

Ce module contient les fonctions pour détecter le data drift et le concept drift
en comparant les données de production avec les données d'entraînement.

Fonctions principales :
- detect_data_drift(): Compare distribution des features
- detect_concept_drift(): Compare distribution des prédictions vs cibles
- load_reference_data(): Charge les données d'entraînement
- load_production_data(): Charge les prédictions récentes depuis PostgreSQL
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_reference_data(
    reference_path: str,
    target_column: str = "Valeur",
    feature_columns: Optional[list] = None
) -> pd.DataFrame:
    """
    Charge les données de référence (entraînement) depuis un fichier Parquet.
    
    Args:
        reference_path: Chemin vers le fichier Parquet de référence
        target_column: Nom de la colonne cible
        feature_columns: Liste des colonnes features (optionnel)
    
    Returns:
        DataFrame avec les données de référence
    """
    try:
        df = pd.read_parquet(reference_path)
        logger.info(f"Données de référence chargées: {len(df)} enregistrements")
        
        # Filtrer les colonnes si spécifiées
        if feature_columns:
            available_columns = [col for col in feature_columns if col in df.columns]
            if target_column in df.columns:
                available_columns.append(target_column)
            df = df[available_columns]
        
        return df
    except Exception as e:
        logger.error(f"Erreur lors du chargement des données de référence: {e}")
        return None


def load_production_data(
    db_handler,
    run_id: Optional[str] = None,
    limit: int = 1000
) -> pd.DataFrame:
    """
    Charge les données de production depuis PostgreSQL.
    
    Args:
        db_handler: Instance de DatabaseHandler
        run_id: ID de la run spécifique (optionnel)
        limit: Nombre maximum d'enregistrements
    
    Returns:
        DataFrame avec les données de production
    """
    try:
        df = db_handler.get_recent_predictions(limit=limit)
        if df is not None and not df.empty:
            logger.info(f"Données de production chargées: {len(df)} enregistrements")
            return df
        else:
            logger.warning("Aucune donnée de production disponible")
            return None
    except Exception as e:
        logger.error(f"Erreur lors du chargement des données de production: {e}")
        return None


def detect_data_drift(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    threshold: float = 0.1,
    feature_columns: Optional[list] = None
) -> Dict[str, Any]:
    """
    Détecte le data drift en comparant les distributions des features.
    
    Args:
        reference_data: DataFrame de référence
        current_data: DataFrame courant
        threshold: Seuil de drift (Population Stability Index)
        feature_columns: Liste des features à analyser
    
    Returns:
        Dict avec les résultats de drift detection
    """
    try:
        if reference_data is None or current_data is None:
            logger.error("Données de référence ou courantes manquantes")
            return {"drift_detected": False, "error": "missing_data"}
        
        if feature_columns is None:
            # Utiliser toutes les colonnes numériques communes
            ref_cols = set(reference_data.select_dtypes(include=[np.number]).columns)
            curr_cols = set(current_data.select_dtypes(include=[np.number]).columns)
            feature_columns = list(ref_cols.intersection(curr_cols))
        
        results = {
            "drift_detected": False,
            "features_drift": {},
            "overall_drift_score": 0.0
        }
        
        drift_count = 0
        
        for feature in feature_columns:
            if feature not in reference_data.columns or feature not in current_data.columns:
                continue
            
            ref_values = reference_data[feature].dropna()
            curr_values = current_data[feature].dropna()
            
            if len(ref_values) == 0 or len(curr_values) == 0:
                continue
            
            # Calculer le Population Stability Index (PSI)
            psi_score = calculate_psi(ref_values, curr_values)
            
            results["features_drift"][feature] = {
                "psi": psi_score,
                "drift_detected": psi_score > threshold
            }
            
            if psi_score > threshold:
                drift_count += 1
            
            results["overall_drift_score"] += psi_score
        
        # Moyenne des PSI
        if len(results["features_drift"]) > 0:
            results["overall_drift_score"] /= len(results["features_drift"])
        
        results["drift_detected"] = drift_count > 0
        results["drifted_features_count"] = drift_count
        results["total_features_analyzed"] = len(results["features_drift"])
        
        if results["drift_detected"]:
            logger.warning(f"Data drift détecté sur {drift_count}/{len(results['features_drift'])} features")
        else:
            logger.info("Pas de data drift détecté")
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection de data drift: {e}")
        return {"drift_detected": False, "error": str(e)}


def detect_concept_drift(
    reference_predictions: np.ndarray,
    current_predictions: np.ndarray,
    reference_targets: Optional[np.ndarray] = None,
    current_targets: Optional[np.ndarray] = None,
    threshold: float = 0.15
) -> Dict[str, Any]:
    """
    Détecte le concept drift en comparant les distributions des prédictions.
    
    Args:
        reference_predictions: Prédictions de référence
        current_predictions: Prédictions courantes
        reference_targets: Cibles de référence (optionnel)
        current_targets: Cibles courantes (optionnel)
        threshold: Seuil de drift
    
    Returns:
        Dict avec les résultats de drift detection
    """
    try:
        results = {
            "drift_detected": False,
            "prediction_drift": {},
            "performance_drift": {}
        }
        
        # Drift sur les prédictions
        ref_mean = np.mean(reference_predictions)
        curr_mean = np.mean(current_predictions)
        
        ref_std = np.std(reference_predictions)
        curr_std = np.std(current_predictions)
        
        mean_drift = abs(curr_mean - ref_mean) / (abs(ref_mean) + 1e-10)
        std_drift = abs(curr_std - ref_std) / (abs(ref_std) + 1e-10)
        
        results["prediction_drift"] = {
            "mean_drift": mean_drift,
            "std_drift": std_drift,
            "ref_mean": ref_mean,
            "curr_mean": curr_mean,
            "ref_std": ref_std,
            "curr_std": curr_std,
            "drift_detected": mean_drift > threshold or std_drift > threshold
        }
        
        # Drift sur la performance si les cibles sont disponibles
        if reference_targets is not None and current_targets is not None:
            from sklearn.metrics import mean_absolute_error, r2_score
            
            ref_mae = mean_absolute_error(reference_targets, reference_predictions)
            curr_mae = mean_absolute_error(current_targets, current_predictions)
            
            ref_r2 = r2_score(reference_targets, reference_predictions)
            curr_r2 = r2_score(current_targets, current_predictions)
            
            mae_drift = abs(curr_mae - ref_mae) / (abs(ref_mae) + 1e-10)
            r2_drift = abs(curr_r2 - ref_r2) / (abs(ref_r2) + 1e-10)
            
            results["performance_drift"] = {
                "mae_drift": mae_drift,
                "r2_drift": r2_drift,
                "ref_mae": ref_mae,
                "curr_mae": curr_mae,
                "ref_r2": ref_r2,
                "curr_r2": curr_r2,
                "drift_detected": mae_drift > threshold or r2_drift > threshold
            }
        
        # Détection globale
        prediction_drift_detected = results["prediction_drift"]["drift_detected"]
        performance_drift_detected = results.get("performance_drift", {}).get("drift_detected", False)
        
        results["drift_detected"] = prediction_drift_detected or performance_drift_detected
        
        if results["drift_detected"]:
            logger.warning(f"Concept drift détecté (predictions: {prediction_drift_detected}, performance: {performance_drift_detected})")
        else:
            logger.info("Pas de concept drift détecté")
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection de concept drift: {e}")
        return {"drift_detected": False, "error": str(e)}


def calculate_psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """
    Calcule le Population Stability Index (PSI).
    
    Args:
        expected: Valeurs attendues (référence)
        actual: Valeurs actuelles
        bins: Nombre de bins pour l'histogramme
    
    Returns:
        PSI score
    """
    try:
        # Définir les bins basés sur les données attendues
        min_val = min(expected.min(), actual.min())
        max_val = max(expected.max(), actual.max())
        
        # Créer les bins
        bin_edges = np.linspace(min_val, max_val, bins + 1)
        
        # Calculer les histogrammes
        expected_counts, _ = np.histogram(expected, bins=bin_edges)
        actual_counts, _ = np.histogram(actual, bins=bin_edges)
        
        # Convertir en proportions
        expected_props = expected_counts / len(expected)
        actual_props = actual_counts / len(actual)
        
        # Éviter les divisions par zéro
        expected_props = np.where(expected_props == 0, 0.0001, expected_props)
        actual_props = np.where(actual_props == 0, 0.0001, actual_props)
        
        # Calculer PSI
        psi = np.sum((actual_props - expected_props) * np.log(actual_props / expected_props))
        
        return psi
        
    except Exception as e:
        logger.error(f"Erreur lors du calcul du PSI: {e}")
        return 0.0


def run_drift_detection(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Exécute la détection de drift complète (data drift + concept drift).
    
    Args:
        reference_data: DataFrame de référence
        current_data: DataFrame courant
        config: Configuration avec les seuils
    
    Returns:
        Dict avec tous les résultats de drift detection
    """
    try:
        results = {
            "data_drift": None,
            "concept_drift": None,
            "overall_drift_detected": False
        }
        
        # Configuration
        data_drift_threshold = config.get("data_drift_threshold", 0.1)
        concept_drift_threshold = config.get("concept_drift_threshold", 0.15)
        feature_columns = config.get("feature_columns", None)
        target_column = config.get("target_column", "Valeur")
        
        # Data drift
        if reference_data is not None and current_data is not None:
            results["data_drift"] = detect_data_drift(
                reference_data=reference_data,
                current_data=current_data,
                threshold=data_drift_threshold,
                feature_columns=feature_columns
            )
        
        # Concept drift (si on a les prédictions)
        # Note: Pour l'instant, on utilise les valeurs cibles si disponibles
        if target_column in reference_data.columns and target_column in current_data.columns:
            ref_targets = reference_data[target_column].values
            curr_targets = current_data[target_column].values
            
            # Simuler des prédictions (en pratique, on utiliserait les vraies prédictions)
            ref_predictions = ref_targets * 0.95  # Simulation
            curr_predictions = curr_targets * 0.95  # Simulation
            
            results["concept_drift"] = detect_concept_drift(
                reference_predictions=ref_predictions,
                current_predictions=curr_predictions,
                reference_targets=ref_targets,
                current_targets=curr_targets,
                threshold=concept_drift_threshold
            )
        
        # Détection globale
        data_drift_detected = results.get("data_drift", {}).get("drift_detected", False)
        concept_drift_detected = results.get("concept_drift", {}).get("drift_detected", False)
        
        results["overall_drift_detected"] = data_drift_detected or concept_drift_detected
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection de drift: {e}")
        return {
            "data_drift": {"drift_detected": False, "error": str(e)},
            "concept_drift": {"drift_detected": False, "error": str(e)},
            "overall_drift_detected": False
        }
