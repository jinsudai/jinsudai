"""
Test simple pour vérifier que tous les imports principaux fonctionnent.

Ce test vérifie que les modules principaux du projet peuvent être importés
sans erreur. Utile pour détecter les problèmes de dépendances ou de structure.
"""
import sys
sys.path.insert(0, 'src')

def test_imports():
    """Teste les imports principaux du projet."""
    errors = []

    # Test imports config
    try:
        from ml.config import load_config
        from ml.config.global_config import load_global_config, get_database_uri
    except Exception as e:
        errors.append(f"Config imports failed: {e}")

    # Test imports pipelines
    try:
        from ml.pipelines.monitoring import MonitoringPipeline
        from ml.pipelines.preparation import PreparationPipeline
        from ml.pipelines.training import TrainingPipeline
    except Exception as e:
        errors.append(f"Pipelines imports failed: {e}")

    # Test imports monitoring
    try:
        from ml.utils.monitoring.drift_detector import (
            load_reference_data,
            run_drift_detection,
            generate_evidently_report,
            save_evidently_report_to_workspace,
            save_evidently_report_to_s3
        )
    except Exception as e:
        errors.append(f"Monitoring imports failed: {e}")

    # Test imports models
    try:
        from ml.utils.models.models_mlflow import (
            get_model_version_by_alias,
            promote_model_to_production
        )
    except Exception as e:
        errors.append(f"MLflow imports failed: {e}")

    # Test imports data handlers
    try:
        from ml.utils.data.s3_handler import S3Handler
    except Exception as e:
        errors.append(f"S3 handler import failed: {e}")

    # Test imports notifications
    try:
        from ml.utils.notifications.email_notifier import EmailNotifier
    except Exception as e:
        errors.append(f"Email notifier import failed: {e}")

    # Afficher les résultats
    if errors:
        print("❌ Import test failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✅ All imports successful")
        sys.exit(0)


if __name__ == "__main__":
    test_imports()
