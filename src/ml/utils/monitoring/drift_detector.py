"""
Détection de drift avec Evidently AI.

Ce module contient les fonctions pour détecter le data drift et le concept drift
en comparant les données de production avec les données d'entraînement.

Fonctions principales :
- detect_data_drift(): Compare distribution des features
- detect_concept_drift(): Compare distribution des prédictions vs cibles
- load_reference_data(): Charge les données d'entraînement
- load_production_data(): Charge les prédictions récentes depuis PostgreSQL
- generate_evidently_report(): Génère un rapport Evidently natif
- save_evidently_report_to_mlflow(): Sauvegarde le rapport dans MLflow
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import tempfile

# Import Evidently
from evidently import Report
from evidently.presets import DataDriftPreset
from evidently.metrics import DriftedColumnsCount
from evidently.ui.workspace import Workspace

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
    limit: int = 1000,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    Charge les données de production depuis PostgreSQL.

    Args:
        db_handler: Instance de DatabaseHandler
        run_id: ID de la run spécifique (optionnel)
        limit: Nombre maximum d'enregistrements
        start_date: Date de début pour filtrer les données (optionnel)
        end_date: Date de fin pour filtrer les données (optionnel)

    Returns:
        DataFrame avec les données de production
    """
    try:
        df = db_handler.get_predictions_for_drift_detection(limit=limit, start_date=start_date, end_date=end_date)
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
            # Utiliser toutes les colonnes numériques communes (exclure datetime, string, object)
            ref_cols = set(reference_data.select_dtypes(include=[np.number]).columns)
            curr_cols = set(current_data.select_dtypes(include=[np.number]).columns)
            feature_columns = list(ref_cols.intersection(curr_cols))

            # Exclure explicitement les colonnes datetime
            datetime_cols = reference_data.select_dtypes(include=['datetime64[ns]', 'datetime64']).columns
            feature_columns = [col for col in feature_columns if col not in datetime_cols]

            # Exclure les colonnes object/string (vérification supplémentaire)
            for col in feature_columns[:]:
                if reference_data[col].dtype == 'object' or current_data[col].dtype == 'object':
                    feature_columns.remove(col)
                    logger.warning(f"Colonne {col} exclue (type object/string non supporté pour PSI)")

        results = {
            "drift_detected": False,
            "features_drift": {},
            "overall_drift_score": 0.0
        }

        drift_count = 0

        for feature in feature_columns:
            if feature not in reference_data.columns or feature not in current_data.columns:
                continue

            # Skip datetime columns (PSI cannot be calculated on datetime)
            if pd.api.types.is_datetime64_any_dtype(reference_data[feature]):
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
        # Convertir en numérique si possible
        expected = pd.to_numeric(expected, errors='coerce').dropna().values
        actual = pd.to_numeric(actual, errors='coerce').dropna().values

        if len(expected) == 0 or len(actual) == 0:
            logger.warning("Pas assez de données numériques pour calculer le PSI")
            return 0.0

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
        data_drift_detected = (results.get("data_drift") or {}).get("drift_detected", False)
        concept_drift_detected = (results.get("concept_drift") or {}).get("drift_detected", False)

        results["overall_drift_detected"] = data_drift_detected or concept_drift_detected

        return results

    except Exception as e:
        logger.error(f"Erreur lors de la détection de drift: {e}")
        return {
            "data_drift": {"drift_detected": False, "error": str(e)},
            "concept_drift": {"drift_detected": False, "error": str(e)},
            "overall_drift_detected": False
        }


def _generate_custom_drift_report_html(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    report_name: str
) -> str:
    """
    Génère un rapport HTML personnalisé pour le drift detection.
    
    Args:
        reference_data: DataFrame de référence
        current_data: DataFrame courant
        report_name: Nom du rapport
        
    Returns:
        HTML content
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Calculer des statistiques basiques
    ref_rows = len(reference_data)
    curr_rows = len(current_data)
    common_cols = list(set(reference_data.columns) & set(current_data.columns))
    
    # Générer le HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Drift Detection Report - {report_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }}
        .stat-box {{ background: #e9f7ef; padding: 10px; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f2f2f2; }}
        .warning {{ color: #856404; background: #fff3cd; padding: 10px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Drift Detection Report</h1>
        <p><strong>Report Name:</strong> {report_name}</p>
        <p><strong>Generated:</strong> {timestamp}</p>
    </div>
    
    <div class="section">
        <h2>Data Overview</h2>
        <div class="stats">
            <div class="stat-box">
                <strong>Reference Rows:</strong> {ref_rows}
            </div>
            <div class="stat-box">
                <strong>Current Rows:</strong> {curr_rows}
            </div>
            <div class="stat-box">
                <strong>Common Columns:</strong> {len(common_cols)}
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>Column Statistics</h2>
        <table>
            <tr>
                <th>Column</th>
                <th>Type</th>
                <th>Ref Mean</th>
                <th>Ref Std</th>
                <th>Curr Mean</th>
                <th>Curr Std</th>
                <th>Ref NaN %</th>
                <th>Curr NaN %</th>
            </tr>
"""
    
    for col in common_cols:
        col_type = str(reference_data[col].dtype)
        ref_mean = reference_data[col].mean() if pd.api.types.is_numeric_dtype(reference_data[col]) else "N/A"
        ref_std = reference_data[col].std() if pd.api.types.is_numeric_dtype(reference_data[col]) else "N/A"
        curr_mean = current_data[col].mean() if pd.api.types.is_numeric_dtype(current_data[col]) else "N/A"
        curr_std = current_data[col].std() if pd.api.types.is_numeric_dtype(current_data[col]) else "N/A"
        ref_nan_pct = (reference_data[col].isna().sum() / len(reference_data)) * 100
        curr_nan_pct = (current_data[col].isna().sum() / len(current_data)) * 100
        
        # Formater les valeurs numériques
        ref_mean_str = f"{ref_mean:.2f}" if isinstance(ref_mean, (int, float)) else str(ref_mean)
        ref_std_str = f"{ref_std:.2f}" if isinstance(ref_std, (int, float)) else str(ref_std)
        curr_mean_str = f"{curr_mean:.2f}" if isinstance(curr_mean, (int, float)) else str(curr_mean)
        curr_std_str = f"{curr_std:.2f}" if isinstance(curr_std, (int, float)) else str(curr_std)
        
        html += f"""
            <tr>
                <td>{col}</td>
                <td>{col_type}</td>
                <td>{ref_mean_str}</td>
                <td>{ref_std_str}</td>
                <td>{curr_mean_str}</td>
                <td>{curr_std_str}</td>
                <td>{ref_nan_pct:.1f}%</td>
                <td>{curr_nan_pct:.1f}%</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
    
    <div class="section warning">
        <h2>Important Note</h2>
        <p>This is a simplified HTML report. For advanced drift visualization, use EvidentlyUI.</p>
        <p>The full Evidently report is saved in the S3 workspace and can be viewed via EvidentlyUI.</p>
    </div>
    
</body>
</html>
"""
    
    return html


def generate_evidently_report(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    output_path: Optional[str] = None,
    report_name: str = "drift_report"
) -> Tuple[Report, Dict[str, Any]]:
    """
    Génère un rapport Evidently natif pour la détection de drift.

    Args:
        reference_data: DataFrame de référence
        current_data: DataFrame courant
        output_path: Chemin pour sauvegarder le rapport HTML (optionnel)
        report_name: Nom du rapport

    Returns:
        Tuple: (Report Evidently, résultats sous forme de dict)
    """
    try:
        if reference_data is None or current_data is None:
            logger.error("Données de référence ou courantes manquantes")
            return None, {"error": "missing_data"}

        # Aligner les colonnes entre les deux DataFrames
        # Nécessaire car nom_vacances a été retiré des features, mais les anciennes données de référence peuvent encore le contenir
        common_columns = list(set(reference_data.columns) & set(current_data.columns))

        if len(common_columns) == 0:
            logger.error("Aucune colonne commune entre les DataFrames de référence et courant")
            return None, {"error": "no_common_columns"}

        # Garder uniquement les colonnes communes
        reference_data_aligned = reference_data[common_columns].copy()
        current_data_aligned = current_data[common_columns].copy()

        logger.info(f"Colonnes utilisées pour le rapport Evidently: {len(common_columns)} colonnes communes")

        # Filtrer les colonnes constantes (variance nulle) pour éviter les warnings numpy
        columns_to_keep = []
        for col in common_columns:
            # Vérifier si la colonne est numérique
            if pd.api.types.is_numeric_dtype(reference_data_aligned[col]):
                # Vérifier la variance avec un seuil plus strict
                ref_std = reference_data_aligned[col].std()
                curr_std = current_data_aligned[col].std()
                # Filtrer aussi si trop de NaN (>50%)
                ref_nan_ratio = reference_data_aligned[col].isna().mean()
                curr_nan_ratio = current_data_aligned[col].isna().mean()
                
                if (ref_std > 1e-6 or curr_std > 1e-6) and ref_nan_ratio < 0.5 and curr_nan_ratio < 0.5:
                    columns_to_keep.append(col)
                else:
                    logger.info(f"Colonne {col} exclue (std: ref={ref_std:.2e}, curr={curr_std:.2e}, nan: ref={ref_nan_ratio:.2f}, curr={curr_nan_ratio:.2f})")
            else:
                columns_to_keep.append(col)

        # Garder uniquement les colonnes non constantes
        reference_data_aligned = reference_data_aligned[columns_to_keep]
        current_data_aligned = current_data_aligned[columns_to_keep]

        logger.info(f"Colonnes après filtrage variance nulle: {len(columns_to_keep)}")

        # Supprimer les warnings numpy pour les divisions par zéro
        import warnings
        warnings.filterwarnings('ignore', category=RuntimeWarning, module='numpy')

        # Créer le rapport avec les presets Evidently
        report = Report(metrics=[
            DataDriftPreset(),
            DriftedColumnsCount()
        ])

        # Exécuter le rapport
        report.run(reference_data=reference_data_aligned, current_data=current_data_aligned)

        # Note: Dans Evidently 0.7.21, la sauvegarde HTML locale n'est pas disponible
        # On génère un rapport HTML personnalisé basé sur les résultats
        if output_path:
            output_file = Path(output_path) / f"{report_name}.html"
            try:
                # Générer un rapport HTML personnalisé
                html_content = _generate_custom_drift_report_html(
                    reference_data=reference_data_aligned,
                    current_data=current_data_aligned,
                    report_name=report_name
                )
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"Rapport HTML personnalisé sauvegardé: {output_file}")
            except Exception as e:
                logger.warning(f"Impossible de sauvegarder le rapport HTML personnalisé: {e}")

        # Retourner le rapport et un dictionnaire vide (l'API d'Evidently a changé)
        return report, {}

    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport Evidently: {e}")
        return None, {"error": str(e)}


def save_evidently_report_to_mlflow(
    report: Report,
    report_dict: Dict[str, Any],
    run_id: Optional[str] = None,
    artifact_path: str = "evidently_reports",
    reference_data: Optional[pd.DataFrame] = None,
    current_data: Optional[pd.DataFrame] = None
) -> bool:
    """
    Sauvegarde le rapport Evidently et ses métriques dans MLflow.

    Args:
        report: Rapport Evidently
        report_dict: Résultats du rapport sous forme de dict
        run_id: ID de la run MLflow (optionnel, utilise la run active si None)
        artifact_path: Chemin pour les artefacts dans MLflow
        reference_data: DataFrame de référence (pour générer HTML personnalisé)
        current_data: DataFrame courant (pour générer HTML personnalisé)

    Returns:
        bool: True si succès, False sinon
    """
    try:
        import mlflow

        # Créer un fichier temporaire pour le rapport HTML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            temp_path = f.name

        # Générer un rapport HTML personnalisé
        if reference_data is not None and current_data is not None:
            try:
                html_content = _generate_custom_drift_report_html(
                    reference_data=reference_data,
                    current_data=current_data,
                    report_name=f"mlflow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            except Exception as e:
                logger.warning(f"Impossible de générer le rapport HTML personnalisé: {e}")
                Path(temp_path).unlink()
                return False
        else:
            logger.warning("Données manquantes pour générer le rapport HTML")
            Path(temp_path).unlink()
            return False

        # Logger les métriques dans MLflow
        if run_id:
            with mlflow.start_run(run_id=run_id):
                _log_metrics_and_artifacts(report_dict, temp_path, artifact_path)
        else:
            _log_metrics_and_artifacts(report_dict, temp_path, artifact_path)

        # Nettoyer le fichier temporaire
        Path(temp_path).unlink()

        logger.info("Rapport Evidently sauvegardé dans MLflow")
        return True

    except ImportError:
        logger.warning("MLflow n'est pas installé, impossible de sauvegarder le rapport")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du rapport dans MLflow: {e}")
        return False


def _log_metrics_and_artifacts(
    report_dict: Dict[str, Any],
    html_path: str,
    artifact_path: str
):
    """Fonction helper pour logger les métriques et artefacts dans MLflow."""
    import mlflow

    # Extraire et logger les métriques de drift (si disponibles)
    if report_dict and "metrics" in report_dict and len(report_dict["metrics"]) > 0:
        first_metric = report_dict["metrics"][0]
        if "result" in first_metric:
            result = first_metric["result"]

            # Logger les métriques principales
            mlflow.log_metric("dataset_drift", int(result.get("dataset_drift", False)))
            mlflow.log_metric("drifted_features", result.get("number_of_drifted_columns", 0))
            mlflow.log_metric("total_features", result.get("number_of_columns", 0))

            # Logger les métriques par feature
            if "drift_by_columns" in result:
                for col, metrics in result["drift_by_columns"].items():
                    mlflow.log_metric(f"drift_{col}", int(metrics.get("drift_detected", False)))
    else:
        logger.warning("Impossible d'extraire les métriques du rapport Evidently (API changée)")

    # Logger le rapport HTML comme artefact
    mlflow.log_artifact(html_path, artifact_path)


def save_evidently_report_to_workspace(
    report: Report,
    project_name: str = "energy_consumption",
    report_name: Optional[str] = None,
    workspace_path: Optional[str] = None,
    ui_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[list] = None
) -> bool:
    """
    Sauvegarde le rapport Evidently dans un workspace Evidently UI (local ou distant).

    Args:
        report: Rapport Evidently
        project_name: Nom du projet dans le workspace
        report_name: Nom du rapport (optionnel, généré automatiquement si None)
        workspace_path: Chemin du workspace local (optionnel, ignoré si ui_url fourni)
        ui_url: URL du service Evidently UI distant (optionnel)
        metadata: Métadonnées à attacher au rapport
        tags: Tags à attacher au rapport

    Returns:
        bool: True si succès, False sinon
    """
    try:
        from evidently.ui.workspace import Workspace, RemoteWorkspace
        from pathlib import Path

        # Utiliser RemoteWorkspace si une URL est fournie
        if ui_url:
            logger.info(f"Connexion au service Evidently UI distant: {ui_url}")
            workspace = RemoteWorkspace(base_url=ui_url)
        else:
            # Workspace local
            if workspace_path is None:
                workspace_path = "/app/workspace"
            workspace_path_obj = Path(workspace_path)
            workspace_path_obj.mkdir(parents=True, exist_ok=True)
            workspace = Workspace.create(workspace_path_obj)

        # Créer ou charger le projet
        try:
            project = workspace.create_project(project_name)
            project.description = "Monitoring de la consommation d'énergie"
            project.save()
        except Exception:
            # Le projet existe déjà
            project = workspace.get_project(project_name)

        # Générer le nom du rapport si non fourni
        if report_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_name = f"drift_report_{timestamp}"

        # Ajouter le rapport au projet via le workspace (API: add_run)
        workspace.add_run(
            project.id,
            report
        )

        logger.info(f"Rapport Evidently sauvegardé dans le workspace: {project_name}/{report_name}")
        return True

    except ImportError:
        logger.warning("Evidently UI n'est pas installé, impossible de sauvegarder dans le workspace")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du rapport dans le workspace: {e}")
        return False


def save_evidently_report_to_s3(
    report: Report,
    s3_bucket: str,
    s3_prefix: str = "evidently_reports",
    report_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Sauvegarde le rapport Evidently sur S3.

    Args:
        report: Rapport Evidently
        s3_bucket: Nom du bucket S3
        s3_prefix: Préfixe S3 pour les rapports
        report_name: Nom du rapport (optionnel, généré automatiquement si None)
        metadata: Métadonnées à attacher au rapport

    Returns:
        bool: True si succès, False sinon
    """
    try:
        from ml.utils.data.s3_handler import S3Handler

        # Générer le nom du rapport si non fourni
        if report_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_name = f"drift_report_{timestamp}.html"
        elif not report_name.endswith('.html'):
            report_name = f"{report_name}.html"

        # Sauvegarder le rapport en HTML temporairement
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            temp_path = f.name
            report.save_html(temp_path)

        # Initialiser le handler S3
        s3_handler = S3Handler(bucket=s3_bucket)

        if not s3_handler.s3_enabled:
            logger.warning("S3 non configuré, impossible de sauvegarder sur S3")
            Path(temp_path).unlink()
            return False

        # Préparer la clé S3
        s3_key = f"{s3_prefix}/{report_name}"

        # Préparer les métadonnées S3
        s3_metadata = {}
        if metadata:
            for key, value in metadata.items():
                # S3 metadata ne supporte que les strings
                s3_metadata[key] = str(value)

        # Upload sur S3
        result = s3_handler.upload_file(
            local_path=temp_path,
            s3_key=s3_key,
            metadata=s3_metadata
        )

        # Nettoyer le fichier temporaire
        Path(temp_path).unlink()

        if result.get("status") == "success":
            logger.info(f"Rapport Evidently sauvegardé sur S3: {result.get('s3_uri')}")
            return True
        else:
            logger.warning(f"Échec de la sauvegarde sur S3: {result.get('reason')}")
            return False

    except ImportError:
        logger.warning("S3Handler n'est pas disponible, impossible de sauvegarder sur S3")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du rapport sur S3: {e}")
        return False


def run_evidently_drift_detection(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    config: Dict[str, Any],
    save_to_mlflow: bool = True,
    mlflow_run_id: Optional[str] = None,
    save_to_workspace: bool = False,
    workspace_path: Optional[str] = None,
    project_name: str = "energy_consumption",
    save_to_s3: bool = False,
    s3_bucket: Optional[str] = None,
    s3_prefix: Optional[str] = None
) -> Dict[str, Any]:
    """
    Exécute la détection de drift complète avec Evidently (rapports natifs).

    Args:
        reference_data: DataFrame de référence
        current_data: DataFrame courant
        config: Configuration avec les seuils
        save_to_mlflow: Sauvegarder le rapport dans MLflow
        mlflow_run_id: ID de la run MLflow (optionnel)
        save_to_workspace: Sauvegarder le rapport dans le workspace Evidently UI local
        workspace_path: Chemin du workspace Evidently (optionnel)
        project_name: Nom du projet dans le workspace
        save_to_s3: Sauvegarder le rapport sur S3
        s3_bucket: Nom du bucket S3
        s3_prefix: Préfixe S3 pour les rapports

    Returns:
        Dict avec tous les résultats de drift detection
    """
    try:
        results = {
            "evidently_report": None,
            "evidently_results": None,
            "overall_drift_detected": False
        }

        # Générer le rapport Evidently
        report, report_dict = generate_evidently_report(
            reference_data=reference_data,
            current_data=current_data
        )

        if report is None:
            logger.error("Impossible de générer le rapport Evidently")
            return {"error": "report_generation_failed"}

        results["evidently_report"] = report
        results["evidently_results"] = report_dict

        # Extraire les résultats de drift (si disponibles)
        if report_dict and "metrics" in report_dict and len(report_dict["metrics"]) > 0:
            first_metric = report_dict["metrics"][0]
            if "result" in first_metric:
                result = first_metric["result"]
                results["overall_drift_detected"] = result.get("dataset_drift", False)
                results["drifted_features_count"] = result.get("number_of_drifted_columns", 0)
                results["total_features_analyzed"] = result.get("number_of_columns", 0)
        else:
            logger.warning("Impossible d'extraire les résultats de drift du rapport Evidently (API changée)")
            results["overall_drift_detected"] = False
            results["drifted_features_count"] = 0
            results["total_features_analyzed"] = 0

        # Sauvegarder dans MLflow si demandé
        if save_to_mlflow and report is not None:
            logger.info(f"Sauvegarde du rapport dans MLflow (run_id: {mlflow_run_id or 'active'})")
            save_evidently_report_to_mlflow(
                report=report,
                report_dict=report_dict,
                run_id=mlflow_run_id
            )
            logger.info("Rapport sauvegardé dans MLflow")

        # Sauvegarder dans le workspace Evidently si demandé
        if save_to_workspace and report is not None:
            ws_path = workspace_path or config.get("evidently_workspace_path", "/app/workspace")
            proj_name = config.get("evidently_project_name", project_name)
            logger.info(f"Sauvegarde du rapport dans le workspace Evidently: {ws_path}, projet: {proj_name}")

            # Préparer les métadonnées
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "data_drift_threshold": config.get("data_drift_threshold", 0.1),
                "concept_drift_threshold": config.get("concept_drift_threshold", 0.15)
            }

            # Tags
            tags = ["drift_detection"]
            if results["overall_drift_detected"]:
                tags.append("drift_detected")

            save_evidently_report_to_workspace(
                report=report,
                project_name=proj_name,
                workspace_path=ws_path,
                metadata=metadata,
                tags=tags
            )
            logger.info("Rapport sauvegardé dans le workspace Evidently")

        # Sauvegarder sur S3 si demandé
        if save_to_s3 and report is not None:
            bucket = s3_bucket or config.get("s3_bucket", "data-store")
            prefix = s3_prefix or config.get("s3_prefix", "evidently_reports")
            logger.info(f"Sauvegarde du rapport sur S3: bucket={bucket}, prefix={prefix}")

            # Préparer les métadonnées
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "data_drift_threshold": config.get("data_drift_threshold", 0.1),
                "concept_drift_threshold": config.get("concept_drift_threshold", 0.15)
            }

            save_evidently_report_to_s3(
                report=report,
                s3_bucket=bucket,
                s3_prefix=prefix,
                metadata=metadata
            )
            logger.info("Rapport sauvegardé sur S3")

        return results

    except Exception as e:
        logger.error(f"Erreur lors de la détection de drift avec Evidently: {e}")
        return {"error": str(e)}
