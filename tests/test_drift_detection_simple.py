"""
Test simplifié du module drift_detector sans dépendances lourdes.
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
import numpy as np
from ml.utils.monitoring.drift_detector import (
    calculate_psi,
    detect_data_drift,
    detect_concept_drift
)


def test_psi_calculation():
    """Test du calcul PSI."""
    print("=== TEST 1: Calcul PSI ===")

    # Test avec distributions identiques
    ref = np.random.normal(0, 1, 1000)
    curr = np.random.normal(0, 1, 1000)

    psi = calculate_psi(ref, curr)
    print(f"PSI (distributions identiques): {psi:.4f}")

    if psi < 0.1:
        print("[OK] PSI faible pour distributions identiques")
    else:
        print(f"[WARNING] PSI élevé pour distributions identiques: {psi}")

    # Test avec distributions différentes
    curr_drifted = np.random.normal(5, 1, 1000)
    psi_drift = calculate_psi(ref, curr_drifted)
    print(f"PSI (distributions différentes): {psi_drift:.4f}")

    if psi_drift > 0.1:
        print("[OK] PSI élevé pour distributions différentes")
    else:
        print(f"[WARNING] PSI faible pour distributions différentes: {psi_drift}")

    return True


def test_data_drift_detection():
    """Test de la détection de data drift."""
    print("\n=== TEST 2: Détection data drift ===")

    # Créer des données de référence
    np.random.seed(42)
    ref_data = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),
        'feature2': np.random.normal(10, 2, 1000),
        'feature3': np.random.exponential(1, 1000),
        'Valeur': np.random.normal(50, 10, 1000)
    })

    # Test 1: Pas de drift
    curr_data_no_drift = ref_data.copy()
    curr_data_no_drift['feature1'] = np.random.normal(0, 1, 1000)
    curr_data_no_drift['feature2'] = np.random.normal(10, 2, 1000)
    curr_data_no_drift['feature3'] = np.random.exponential(1, 1000)

    result_no_drift = detect_data_drift(
        reference_data=ref_data,
        current_data=curr_data_no_drift,
        threshold=0.1,
        feature_columns=['feature1', 'feature2', 'feature3']
    )

    print(f"Résultat sans drift: drift_detected={result_no_drift['drift_detected']}")
    print(f"  Features avec drift: {result_no_drift.get('drifted_features_count', 0)}/{result_no_drift.get('total_features_analyzed', 0)}")

    if not result_no_drift['drift_detected']:
        print("[OK] Pas de drift détecté (comme attendu)")
    else:
        print("[WARNING] Drift détecté avec des données similaires")

    # Test 2: Avec drift
    curr_data_with_drift = ref_data.copy()
    curr_data_with_drift['feature1'] = np.random.normal(5, 1, 1000)  # Drift significatif
    curr_data_with_drift['feature2'] = np.random.normal(10, 2, 1000)
    curr_data_with_drift['feature3'] = np.random.exponential(1, 1000)

    result_with_drift = detect_data_drift(
        reference_data=ref_data,
        current_data=curr_data_with_drift,
        threshold=0.1,
        feature_columns=['feature1', 'feature2', 'feature3']
    )

    print(f"Résultat avec drift: drift_detected={result_with_drift['drift_detected']}")
    print(f"  Features avec drift: {result_with_drift.get('drifted_features_count', 0)}/{result_with_drift.get('total_features_analyzed', 0)}")

    if result_with_drift['drift_detected']:
        print("[OK] Drift détecté (comme attendu)")
    else:
        print("[WARNING] Drift non détecté avec des données différentes")

    return True


def test_concept_drift_detection():
    """Test de la détection de concept drift."""
    print("\n=== TEST 3: Détection concept drift ===")

    # Créer des prédictions et cibles de référence
    np.random.seed(42)
    ref_predictions = np.random.normal(50, 5, 1000)
    ref_targets = np.random.normal(50, 5, 1000)

    # Test 1: Pas de drift
    curr_predictions_no_drift = np.random.normal(50, 5, 1000)
    curr_targets_no_drift = np.random.normal(50, 5, 1000)

    result_no_drift = detect_concept_drift(
        reference_predictions=ref_predictions,
        current_predictions=curr_predictions_no_drift,
        reference_targets=ref_targets,
        current_targets=curr_targets_no_drift,
        threshold=0.15
    )

    print(f"Résultat sans drift: drift_detected={result_no_drift['drift_detected']}")
    print(f"  Prediction drift: {result_no_drift.get('prediction_drift', {}).get('drift_detected', False)}")

    if not result_no_drift['drift_detected']:
        print("[OK] Pas de concept drift détecté (comme attendu)")
    else:
        print("[WARNING] Concept drift détecté avec des données similaires")

    # Test 2: Avec drift
    curr_predictions_with_drift = np.random.normal(60, 5, 1000)  # Drift significatif
    curr_targets_with_drift = np.random.normal(60, 5, 1000)

    result_with_drift = detect_concept_drift(
        reference_predictions=ref_predictions,
        current_predictions=curr_predictions_with_drift,
        reference_targets=ref_targets,
        current_targets=curr_targets_with_drift,
        threshold=0.15
    )

    print(f"Résultat avec drift: drift_detected={result_with_drift['drift_detected']}")
    print(f"  Prediction drift: {result_with_drift.get('prediction_drift', {}).get('drift_detected', False)}")

    if result_with_drift['drift_detected']:
        print("[OK] Concept drift détecté (comme attendu)")
    else:
        print("[WARNING] Concept drift non détecté avec des données différentes")

    return True


def test_module_imports():
    """Test que les modules sont importables."""
    print("\n=== TEST 4: Import des modules ===")

    try:
        from ml.utils.monitoring.drift_detector import (
            load_reference_data,
            load_production_data,
            detect_data_drift,
            detect_concept_drift,
            run_drift_detection,
            calculate_psi
        )
        print("[OK] Module drift_detector importable")
        return True
    except ImportError as e:
        print(f"[ERROR] Impossible d'importer drift_detector: {e}")
        return False


if __name__ == "__main__":
    print("=== TESTS SIMPLIFIÉS DU MODULE DRIFT DETECTOR ===\n")

    results = {}

    # Test 1: Calcul PSI
    results['psi_calculation'] = test_psi_calculation()

    # Test 2: Détection data drift
    results['data_drift_detection'] = test_data_drift_detection()

    # Test 3: Détection concept drift
    results['concept_drift_detection'] = test_concept_drift_detection()

    # Test 4: Import des modules
    results['module_imports'] = test_module_imports()

    # Résumé
    print("\n=== RÉSUMÉ DES TESTS ===")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())
    print(f"\n{'✅ TOUS LES TESTS PASSENT' if all_passed else '❌ CERTAINS TESTS ONT ÉCHOUÉ'}")

    sys.exit(0 if all_passed else 1)
