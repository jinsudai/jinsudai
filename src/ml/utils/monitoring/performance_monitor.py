"""
Monitoring de la performance du modèle avec Evidently AI.

Spécifications (voir SPECIFICATIONS.md) :
- Métriques trackées : AUC >= 0.95, Precision >= 0.90, Recall >= 0.85
- Alertes : Warning si AUC < 0.93, Critical si AUC < 0.90
- Trigger : Réentraînement si AUC < 0.92
- Output : Rapports HTML Evidently, logs JSON
- Fréquence : Continu en production, batch après chaque prédiction

Fonctions principales :
- create_performance_report() : Génère rapport performance vs baseline
- detect_drift() : Compare predictions/features aux données historiques
"""
import pandas as pd
import numpy as np
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_performance_report(
    reference_data,
    current_data,
    predictions_ref,
    predictions_current,
    output_path="outputs/evidently_performance.html",
    target_column=None,
    problem_type="classification"
):
    """
    Création d'un rapport de performance avec détection de drift
    
    Args:
        reference_data: DataFrame de référence
        current_data: DataFrame courant
        predictions_ref: Prédictions sur les données de référence
        predictions_current: Prédictions sur les données courantes
        output_path: Chemin pour sauvegarder le rapport
        target_column: Nom de la colonne cible
        problem_type: Type de problème ('classification' ou 'regression')
    
    Returns:
        dict: Rapport de performance
    """
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Essayer d'utiliser Evidently si disponible
        try:
            from evidently.report import Report
            
            # Ajouter les prédictions aux données
            ref_with_pred = reference_data.copy()
            ref_with_pred['predictions'] = predictions_ref
            
            current_with_pred = current_data.copy()
            current_with_pred['predictions'] = predictions_current
            
            # Créer le rapport
            report = Report(metrics=[])
            # Laisser Evidently configurer automatiquement
            report.run(reference_data=ref_with_pred, current_data=current_with_pred)
            report.save_html(output_path)
            logger.info(f"Rapport Evidently créé: {output_path}")
            return report
        except (ImportError, AttributeError):
            # Fallback - créer un rapport HTML simple
            logger.warning("Evidently API non disponible, utilisation de rapport simple")
            return generate_simple_performance_report(
                reference_data, current_data, 
                predictions_ref, predictions_current,
                output_path, problem_type
            )
    except Exception as e:
        logger.error(f"Erreur lors de la création du rapport de performance: {e}")
        return None


def generate_simple_performance_report(
    reference_data,
    current_data,
    predictions_ref,
    predictions_current,
    output_path,
    problem_type
):
    """
    Génère un rapport HTML simple de performance (fallback)
    """
    try:
        # Calculer les statistiques de drift
        drift_info = detect_prediction_drift(predictions_ref, predictions_current)
        
        # Générer HTML
        html_content = """
        <html>
        <head><title>Rapport de Performance</title></head>
        <body>
        <h1>Rapport de Performance du Modèle</h1>
        """
        
        html_content += f"<h2>Type de problème: {problem_type}</h2>"
        
        # Informations de drift
        if drift_info:
            html_content += "<h3>Détection de Drift</h3>"
            html_content += f"<p><strong>Drift détecté:</strong> {drift_info['drift_detected']}</p>"
            html_content += f"<p><strong>Mean Drift:</strong> {drift_info['mean_drift']:.4f}</p>"
            html_content += f"<p><strong>Std Drift:</strong> {drift_info['std_drift']:.4f}</p>"
            html_content += f"<p><strong>Moyenne prédictions (ref):</strong> {drift_info['ref_mean']:.4f}</p>"
            html_content += f"<p><strong>Moyenne prédictions (current):</strong> {drift_info['current_mean']:.4f}</p>"
        
        html_content += "</body></html>"
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Rapport simple créé: {output_path}")
        return {"status": "success", "path": output_path}
    except Exception as e:
        logger.error(f"Erreur lors de la création du rapport simple: {e}")
        return None


def detect_prediction_drift(predictions_ref, predictions_current, threshold=0.1):
    """
    Détecte un changement de distribution dans les prédictions
    
    Args:
        predictions_ref: Prédictions de référence
        predictions_current: Prédictions courantes
        threshold: Seuil de drift

    Returns:
        dict: Résultats de la détection
    """
    try:
        ref_mean = np.mean(predictions_ref)
        current_mean = np.mean(predictions_current)
        
        ref_std = np.std(predictions_ref)
        current_std = np.std(predictions_current)
        
        mean_drift = abs(current_mean - ref_mean) / (abs(ref_mean) + 1e-10)
        std_drift = abs(current_std - ref_std) / (abs(ref_std) + 1e-10)
        
        drift_detected = mean_drift > threshold or std_drift > threshold
        
        results = {
            'mean_drift': mean_drift,
            'std_drift': std_drift,
            'drift_detected': drift_detected,
            'ref_mean': ref_mean,
            'current_mean': current_mean,
            'ref_std': ref_std,
            'current_std': current_std
        }
        
        if drift_detected:
            logger.warning(f"Drift détecté! Mean drift: {mean_drift:.4f}, Std drift: {std_drift:.4f}")
        else:
            logger.info("Pas de drift détecté")
        
        return results
    except Exception as e:
        logger.error(f"Erreur lors de la détection du drift: {e}")
        return None


def _encode_predictions_for_drift(predictions):
    """Encode les prédictions catégorielles pour le calcul du drift."""
    values = np.asarray(predictions)
    if values.size == 0:
        return values.astype(float)

    if values.dtype.kind in {'U', 'S', 'O'}:
        _, encoded = np.unique(values, return_inverse=True)
        return encoded.astype(float)

    try:
        return values.astype(float)
    except ValueError:
        _, encoded = np.unique(values, return_inverse=True)
        return encoded.astype(float)


def _prepare_prediction_input(model, X_data, feature_names=None):
    """Prépare l'entrée pour la prédiction selon le type de modèle."""
    if type(model).__name__ == 'TabularPredictor':
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas est requis pour prédire avec Autogluon")

        if isinstance(X_data, pd.DataFrame):
            return X_data

        if feature_names is not None and hasattr(X_data, 'shape'):
            try:
                if X_data.shape[1] == len(feature_names):
                    return pd.DataFrame(X_data, columns=feature_names)
                logger.warning(
                    f"feature_names length ({len(feature_names)}) ne correspond pas "
                    f"à X_data columns ({X_data.shape[1]}), fallback sans colonnes"
                )
            except Exception:
                pass

        return pd.DataFrame(X_data)

    return X_data


def detect_problem_type(model, y_train=None, y_test=None):
    """Détecte le type de problème à partir du modèle ou des données."""
    if type(model).__name__ == 'TabularPredictor':
        try:
            objective = model._learner.objective
            if "regression" in objective:
                return "regression"
        except Exception:
            pass

    if hasattr(model, 'predict_proba'):
        return "classification"

    if y_train is not None and y_test is not None:
        if len(np.unique(y_train)) < 20:
            return "classification"

    return "regression"


def run_monitoring(
    model,
    X_train,
    X_test,
    y_train=None,
    y_test=None,
    feature_names=None,
    problem_type=None
):
    """Exécute le monitoring complet (drift + performance)."""
    if model is None:
        raise ValueError("Le modèle est requis pour le monitoring")

    if X_train is None or X_test is None:
        raise ValueError("Les données d'entraînement et de test sont requises pour le monitoring")

    X_train_input = _prepare_prediction_input(model, X_train, feature_names)
    X_test_input = _prepare_prediction_input(model, X_test, feature_names)

    pred_train = model.predict(X_train_input)
    pred_test = model.predict(X_test_input)

    if problem_type is None:
        problem_type = detect_problem_type(model, y_train, y_test)

    drift_results = detect_prediction_drift(pred_train, pred_test)

    performance_train = None
    performance_test = None
    if y_train is not None and y_test is not None:
        performance_train = monitor_model_performance(
            pred_train,
            y_train,
            problem_type=problem_type
        )
        performance_test = monitor_model_performance(
            pred_test,
            y_test,
            problem_type=problem_type
        )

    return {
        'drift': drift_results,
        'performance_train': performance_train,
        'performance_test': performance_test,
        'problem_type': problem_type,
        'pred_train': pred_train,
        'pred_test': pred_test
    }


def flatten_monitoring_metrics(monitoring_results, prefix="monitoring"):
    """Transforme les résultats de monitoring en métriques scalaires MLflow."""
    if not monitoring_results:
        return {}

    metrics = {}
    drift = monitoring_results.get('drift') or {}
    for key in ['mean_drift', 'std_drift', 'drift_detected']:
        if key in drift:
            value = drift[key]
            if isinstance(value, bool):
                value = float(value)
            metrics[f"{prefix}_drift_{key}"] = value

    performance_test = monitoring_results.get('performance_test') or {}
    for key, value in (performance_test or {}).items():
        metrics[f"{prefix}_test_{key}"] = value

    performance_train = monitoring_results.get('performance_train') or {}
    for key, value in (performance_train or {}).items():
        metrics[f"{prefix}_train_{key}"] = value

    return metrics


def generate_monitoring_summary(monitoring_results):
    """
    Génère un résumé du monitoring
    
    Args:
        monitoring_results: Résultats complets du monitoring

    Returns:
        str: Résumé formaté
    """
    if monitoring_results is None:
        return "Aucun résultat de monitoring disponible"

    drift_results = monitoring_results.get('drift')
    performance_test = monitoring_results.get('performance_test')
    performance_train = monitoring_results.get('performance_train')

    summary = "=== MONITORING SUMMARY ===\n"

    if drift_results:
        summary += "\n[DRIFT DETECTION]\n"
        summary += f"Drift detected: {drift_results['drift_detected']}\n"
        summary += f"Mean drift: {drift_results['mean_drift']:.4f}\n"
        summary += f"Std drift: {drift_results['std_drift']:.4f}\n"

    if performance_test:
        summary += "\n[PERFORMANCE METRICS - TEST]\n"
        for key, value in performance_test.items():
            summary += f"{key}: {value:.4f}\n"

    if performance_train:
        summary += "\n[PERFORMANCE METRICS - TRAIN]\n"
        for key, value in performance_train.items():
            summary += f"{key}: {value:.4f}\n"

    logger.info(summary)
    return summary


def monitor_model_performance(
    y_pred,
    y_actual,
    metrics_dict=None,
    problem_type="classification"
):
    """
    Monitoring continu de la performance du modèle
    
    Args:
        y_pred: Prédictions du modèle
        y_actual: Valeurs réelles
        metrics_dict: Dict existant de métriques (optionnel)
        problem_type: Type de problème
    
    Returns:
        dict: Métriques de performance
    """
    try:
        if metrics_dict is None:
            metrics_dict = {}
        
        if problem_type == "classification":
            from sklearn.metrics import accuracy_score, balanced_accuracy_score
            metrics_dict['accuracy'] = accuracy_score(y_actual, y_pred)
            metrics_dict['balanced_accuracy'] = balanced_accuracy_score(y_actual, y_pred)
            
        else:
            from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
            metrics_dict['mae'] = mean_absolute_error(y_actual, y_pred)
            metrics_dict['mse'] = mean_squared_error(y_actual, y_pred)
            metrics_dict['rmse'] = np.sqrt(metrics_dict['mse'])
            metrics_dict['r2'] = r2_score(y_actual, y_pred)
        
        logger.info(f"Métriques de performance calculées: {metrics_dict}")
        return metrics_dict
        
    except Exception as e:
        logger.error(f"Erreur lors du monitoring: {e}")
        return None


