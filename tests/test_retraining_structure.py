"""
Test de la structure du pipeline de retraining (sans imports).
"""
import sys
from pathlib import Path


def test_retrain_task_exists():
    """Test que le fichier prediction_tasks.py contient retrain_model_task."""
    print("=== TEST 1: Existence de retrain_model_task ===")

    file_path = Path("src/ml/workflows/prediction_tasks.py")
    if not file_path.exists():
        print(f"[ERROR] Fichier {file_path} non trouvé")
        return False

    content = file_path.read_text(encoding='utf-8')

    if "def retrain_model_task" in content:
        print("[OK] retrain_model_task trouvé dans prediction_tasks.py")
        return True
    else:
        print("[ERROR] retrain_model_task non trouvé")
        return False


def test_weather_flow_exists():
    """Test que le fichier weather_flow.py existe."""
    print("\n=== TEST 2: Existence de weather_flow.py ===")

    file_path = Path("src/ml/workflows/weather_flow.py")
    if not file_path.exists():
        print(f"[ERROR] Fichier {file_path} non trouvé")
        return False

    content = file_path.read_text(encoding='utf-8')

    if "def update_weather_daily_flow" in content:
        print("[OK] update_weather_daily_flow trouvé dans weather_flow.py")
        return True
    else:
        print("[ERROR] update_weather_daily_flow non trouvé")
        return False


def test_database_handler_method():
    """Test que DatabaseHandler a la méthode get_production_data_for_retraining."""
    print("\n=== TEST 3: Méthode get_production_data_for_retraining ===")

    file_path = Path("src/ml/utils/pipelines/database_handler.py")
    if not file_path.exists():
        print(f"[ERROR] Fichier {file_path} non trouvé")
        return False

    content = file_path.read_text(encoding='utf-8')

    if "def get_production_data_for_retraining" in content:
        print("[OK] get_production_data_for_retraining trouvé dans database_handler.py")
        return True
    else:
        print("[ERROR] get_production_data_for_retraining non trouvé")
        return False


def test_prediction_flow_integration():
    """Test que prediction_flow.py importe retrain_model_task."""
    print("\n=== TEST 4: Intégration dans prediction_flow.py ===")

    file_path = Path("src/ml/workflows/prediction_flow.py")
    if not file_path.exists():
        print(f"[ERROR] Fichier {file_path} non trouvé")
        return False

    content = file_path.read_text(encoding='utf-8')

    if "retrain_model_task" in content and "retraining_info" in content:
        print("[OK] retrain_model_task intégré dans prediction_flow.py")
        return True
    else:
        print("[ERROR] retrain_model_task non intégré")
        return False


def test_retrain_task_parameters():
    """Test que retrain_model_task a les bons paramètres."""
    print("\n=== TEST 5: Paramètres de retrain_model_task ===")

    file_path = Path("src/ml/workflows/prediction_tasks.py")
    assert file_path.exists(), f"Fichier {file_path} non trouvé"

    content = file_path.read_text(encoding='utf-8')

    expected_params = ["enabled", "min_samples", "drift_detected"]
    all_found = True

    for param in expected_params:
        if param in content:
            print(f"[OK] Paramètre {param} trouvé")
        else:
            print(f"[ERROR] Paramètre {param} non trouvé")
            all_found = False

    assert all_found, "Certains paramètres manquent"


def test_retrain_task_logic():
    """Test que retrain_model_task a la logique de déclenchement."""
    print("\n=== TEST 6: Logique de déclenchement ===")

    file_path = Path("src/ml/workflows/prediction_tasks.py")
    assert file_path.exists(), f"Fichier {file_path} non trouvé"

    content = file_path.read_text(encoding='utf-8')

    checks = [
        ("if not enabled", "Vérification enabled"),
        ("if not drift_detected", "Vérification drift_detected"),
        ("prepare_consumption_features_task", "Enrichissement features"),
        ("train_consumption_model_task", "Entraînement"),
        ("stage_and_log_consumption_model_task", "Staging")
    ]

    all_found = True
    for check, description in checks:
        if check in content:
            print(f"[OK] {description} trouvé")
        else:
            print(f"[ERROR] {description} non trouvé")
            all_found = False

    assert all_found, "Certains éléments de logique manquent"


if __name__ == "__main__":
    print("=== TESTS DE STRUCTURE DU PIPELINE DE RETRAINING ===\n")

    results = {}

    # Test 1: Existence retrain_model_task
    results['retrain_task_exists'] = test_retrain_task_exists()

    # Test 2: Existence weather_flow
    results['weather_flow_exists'] = test_weather_flow_exists()

    # Test 3: DatabaseHandler method
    results['database_handler_method'] = test_database_handler_method()

    # Test 4: Prediction flow integration
    results['prediction_flow_integration'] = test_prediction_flow_integration()

    # Test 5: Retrain task parameters
    results['retrain_task_parameters'] = test_retrain_task_parameters()

    # Test 6: Retrain task logic
    results['retrain_task_logic'] = test_retrain_task_logic()

    # Résumé
    print("\n=== RÉSUMÉ DES TESTS ===")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())
    print(f"\n{'✅ TOUS LES TESTS PASSENT' if all_passed else '❌ CERTAINS TESTS ONT ÉCHOUÉ'}")

    sys.exit(0 if all_passed else 1)
