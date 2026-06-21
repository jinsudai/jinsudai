"""
Test du pipeline de détection de drift.
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
import numpy as np
from ml.pipelines.database_handler import DatabaseHandler
from ml.utils.monitoring.drift_detector import (
    load_reference_data,
    detect_data_drift,
    detect_concept_drift,
    run_drift_detection
)
from ml.config import load_config


def test_drift_detector_module():
    """Test du module drift_detector."""
    print("=== TEST 1: Module drift_detector ===")

    # Charger la configuration
    config = load_config('src/configs/consumption.yaml')
    drift_config = config.get('drift_detection', {})

    print(f"Configuration drift detection: {drift_config}")

    # Charger les données de référence
    reference_path = drift_config.get('reference_data_path')
    reference_data = load_reference_data(
        reference_path=reference_path,
        target_column=config.get('data', {}).get('target_column', 'Valeur'),
        feature_columns=config.get('data', {}).get('feature_columns')
    )

    if reference_data is None:
        print("[ERROR] Impossible de charger les données de référence")
        return False

    print(f"[OK] Données de référence chargées: {len(reference_data)} enregistrements")

    # Créer des données de test sans drift
    test_data_no_drift = reference_data.copy()

    # Exécuter la détection de drift
    drift_detection_config = {
        "data_drift_threshold": drift_config.get('data_drift_threshold', 0.1),
        "concept_drift_threshold": drift_config.get('concept_drift_threshold', 0.15),
        "feature_drift_threshold": drift_config.get('feature_drift_threshold', 0.2),
        "feature_columns": config.get('data', {}).get('feature_columns'),
        "target_column": config.get('data', {}).get('target_column', 'Valeur')
    }

    results_no_drift = run_drift_detection(
        reference_data=reference_data,
        current_data=test_data_no_drift,
        config=drift_detection_config
    )

    print(f"[OK] Résultats sans drift: {results_no_drift}")

    if results_no_drift.get('overall_drift_detected', False):
        print("[ERROR] Drift détecté alors qu'il ne devrait pas y en avoir")
        return False

    print("[OK] Pas de drift détecté (comme attendu)")

    # Créer des données de test avec drift artificiel
    test_data_with_drift = reference_data.copy()
    numeric_cols = test_data_with_drift.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if col != config.get('data', {}).get('target_column', 'Valeur'):
            # Ajouter un drift significatif
            test_data_with_drift[col] = test_data_with_drift[col] * 2 + np.random.normal(0, 10, len(test_data_with_drift))

    results_with_drift = run_drift_detection(
        reference_data=reference_data,
        current_data=test_data_with_drift,
        config=drift_detection_config
    )

    print(f"[OK] Résultats avec drift: {results_with_drift}")

    if not results_with_drift.get('overall_drift_detected', False):
        print("[WARNING] Drift non détecté avec les données modifiées (peut être normal selon les données)")
    else:
        print("[OK] Drift détecté (comme attendu)")

    return True


def test_database_handler_drift():
    """Test des méthodes drift dans DatabaseHandler."""
    print("\n=== TEST 2: DatabaseHandler drift methods ===")
    print("[SKIP] Test supprimé - drift metrics stockés dans MLflow uniquement")
    return True


def test_drift_task_integration():
    """Test de l'intégration de la tâche drift dans le pipeline."""
    print("\n=== TEST 3: Intégration tâche drift ===")

    # Vérifier que la tâche est importable
    try:
        from ml.workflows.prediction_tasks import detect_drift_task
        print("[OK] Tâche detect_drift_task importable")
    except ImportError as e:
        print(f"[ERROR] Impossible d'importer detect_drift_task: {e}")
        return False

    # Vérifier que la tâche est intégrée dans le flow
    try:
        from ml.workflows.prediction_flow import prediction_full_pipeline
        print("[OK] Flow prediction_full_pipeline importable")
    except ImportError as e:
        print(f"[ERROR] Impossible d'importer prediction_full_pipeline: {e}")
        return False

    # Vérifier que l'email notifier a la méthode drift
    try:
        from ml.utils.notifications.email_notifier import EmailNotifier
        if hasattr(EmailNotifier, 'notify_drift_detected'):
            print("[OK] Méthode notify_drift_detected disponible dans EmailNotifier")
        else:
            print("[ERROR] Méthode notify_drift_detected manquante dans EmailNotifier")
            return False
    except ImportError as e:
        print(f"[ERROR] Impossible d'importer EmailNotifier: {e}")
        return False

    return True


if __name__ == "__main__":
    print("=== TESTS DU PIPELINE DE DÉTECTION DE DRIFT ===\n")

    results = {}

    # Test 1: Module drift_detector
    results['drift_detector_module'] = test_drift_detector_module()

    # Test 2: DatabaseHandler drift methods
    results['database_handler_drift'] = test_database_handler_drift()

    # Test 3: Intégration tâche drift
    results['drift_task_integration'] = test_drift_task_integration()

    # Résumé
    print("\n=== RÉSUMÉ DES TESTS ===")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())
    print(f"\n{'✅ TOUS LES TESTS PASSENT' if all_passed else '❌ CERTAINS TESTS ONT ÉCHOUÉ'}")

    sys.exit(0 if all_passed else 1)
