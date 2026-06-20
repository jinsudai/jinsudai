"""
Validation des données avec Evidently AI.

Spécifications (voir SPECIFICATIONS.md) :
- Validation : Schéma, valeurs manquantes, ranges
- Drift détection : Comparaison reference vs current data
- Output : Rapport HTML Evidently
- Utilisation : Pre-training validation, monitoring post-deployment

Fonctions principales :
- create_data_validation_report() : Génère rapport validation
"""
import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_data_validation_report(current_data, reference_data=None, output_path="outputs/evidently_report.html"):
    """
    Création d'un rapport de validation des données avec Evidently AI
    Utilise Evidently 0.7+ avec interface compatible
    """
    try:
        # Créer le répertoire de sortie
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Importer Evidently de manière flexible selon la version
        try:
            from evidently.report import Report
            from evidently.metrics import DataMissingValuesMetric, DataStatisticsReport

            # Définir les métriques
            report = Report(metrics=[
                DataMissingValuesMetric(),
                DataStatisticsReport(),
            ])

            report.run(reference_data=reference_data, current_data=current_data)
            report.save_html(output_path)
            logger.info(f"Rapport Evidently créé: {output_path}")
            return report
        except ImportError:
            # Fallback si Evidently n'a pas la bonne structure
            logger.warning("Evidently Report API non disponible, utilisation de validation basique")
            return generate_simple_validation_report(current_data, reference_data, output_path)
    except Exception as e:
        logger.error(f"Erreur lors de la création du rapport: {e}")
        return None


def generate_simple_validation_report(current_data, reference_data=None, output_path="outputs/evidently_report.html"):
    """
    Génère un rapport HTML simple de validation (fallback)
    """
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Générer un rapport HTML simple
        html_content = """
        <html>
        <head><title>Rapport de Validation des Données</title></head>
        <body>
        <h1>Rapport de Validation</h1>
        """

        # Ajouter les statistiques des données courantes
        html_content += "<h2>Données Courantes</h2>"
        html_content += f"<p>Shape: {current_data.shape}</p>"
        html_content += "<h3>Valeurs Manquantes</h3>"
        html_content += current_data.isnull().sum().to_frame().to_html()
        html_content += "<h3>Statistiques</h3>"
        html_content += current_data.describe().to_html()

        # Ajouter les statistiques des données de référence si disponibles
        if reference_data is not None:
            html_content += "<h2>Données de Référence</h2>"
            html_content += f"<p>Shape: {reference_data.shape}</p>"
            html_content += "<h3>Valeurs Manquantes</h3>"
            html_content += reference_data.isnull().sum().to_frame().to_html()
            html_content += "<h3>Statistiques</h3>"
            html_content += reference_data.describe().to_html()

        html_content += "</body></html>"

        with open(output_path, 'w') as f:
            f.write(html_content)

        logger.info(f"Rapport simple créé: {output_path}")
        return {"status": "success", "path": output_path}
    except Exception as e:
        logger.error(f"Erreur lors de la création du rapport simple: {e}")
        return None


def validate_data_quality(data, missing_threshold=0.1, duplicate_threshold=0.05):
    """
    Vérification basique de la qualité des données

    Args:
        data: DataFrame à valider
        missing_threshold: Seuil maximal de valeurs manquantes (proportion)
        duplicate_threshold: Seuil maximal de lignes dupliquées (proportion)

    Returns:
        dict: Résultats de la validation
    """
    results = {}

    # Vérifier valeurs manquantes
    missing_ratio = data.isnull().sum().sum() / (data.shape[0] * data.shape[1])
    results['missing_values_ratio'] = missing_ratio
    results['missing_values_ok'] = missing_ratio < missing_threshold

    # Vérifier lignes dupliquées
    duplicate_ratio = data.duplicated().sum() / len(data)
    results['duplicate_rows_ratio'] = duplicate_ratio
    results['duplicate_rows_ok'] = duplicate_ratio < duplicate_threshold

    # Vérifier type des colonnes
    results['column_types'] = data.dtypes.to_dict()

    # Résumé
    results['is_valid'] = results['missing_values_ok'] and results['duplicate_rows_ok']

    logger.info(f"Validation: Valeurs manquantes={missing_ratio:.2%}, Doublons={duplicate_ratio:.2%}")

    return results
