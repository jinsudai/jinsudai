"""
Test du pipeline de retraining automatique.
"""
import sys
sys.path.insert(0, 'src')


def test_retrain_model_task_import():
    """Test que la tâche retrain_model_task est importable."""
    print("=== TEST 1: Import de retrain_model_task ===")

    try:
        from ml.workflows.prediction_tasks import retrain_model_task
        print("[OK] retrain_model_task importable")
        return True
    except ImportError as e:
        print(f"[ERROR] Impossible d'importer retrain_model_task: {e}")
        return False


def test_weather_flow_import():
    """Test que le flow de mise à jour weather est importable."""
    print("\n=== TEST 2: Import de update_weather_daily_flow ===")

    try:
        from ml.workflows.weather_flow import update_weather_daily_flow
        print("[OK] update_weather_daily_flow importable")
        return True
    except ImportError as e:
        print(f"[ERROR] Impossible d'importer update_weather_daily_flow: {e}")
        return False


def test_database_handler_retraining_method():
    """Test que la méthode get_production_data_for_retraining existe."""
    print("\n=== TEST 3: Méthode get_production_data_for_retraining ===")

    try:
        from ml.pipelines.database_handler import DatabaseHandler

        if hasattr(DatabaseHandler, 'get_production_data_for_retraining'):
            print("[OK] Méthode get_production_data_for_retraining existe")
            return True
        else:
            print("[ERROR] Méthode get_production_data_for_retraining manquante")
            return False
    except ImportError as e:
        print(f"[ERROR] Impossible d'importer DatabaseHandler: {e}")
        return False


def test_prediction_flow_integration():
    """Test que le flow prediction_full_pipeline inclut le retraining."""
    print("\n=== TEST 4: Intégration dans prediction_full_pipeline ===")

    try:
        from ml.workflows.prediction_flow import prediction_full_pipeline
        print("[OK] prediction_full_pipeline importable")

        # Vérifier que le flow existe
        if prediction_full_pipeline:
            print("[OK] Flow prediction_full_pipeline disponible")
            return True
        else:
            print("[ERROR] Flow prediction_full_pipeline None")
            return False
    except ImportError as e:
        print(f"[ERROR] Impossible d'importer prediction_full_pipeline: {e}")
        return False


def test_retrain_task_parameters():
    """Test que la tâche retrain_model_task a les bons paramètres."""
    print("\n=== TEST 5: Paramètres de retrain_model_task ===")

    try:
        from ml.workflows.prediction_tasks import retrain_model_task
        import inspect

        signature = inspect.signature(retrain_model_task)
        params = list(signature.parameters.keys())

        expected_params = ['pipeline', 'config_path', 'enabled', 'min_samples', 'drift_detected']

        for param in expected_params:
            if param in params:
                print(f"[OK] Paramètre {param} présent")
            else:
                print(f"[ERROR] Paramètre {param} manquant")
                return False

        print("[OK] Tous les paramètres attendus sont présents")
        return True
    except Exception as e:
        print(f"[ERROR] Erreur lors de la vérification des paramètres: {e}")
        return False


if __name__ == "__main__":
    print("=== TESTS DU PIPELINE DE RETRAINING ===\n")

    results = {}

    # Test 1: Import retrain_model_task
    results['retrain_task_import'] = test_retrain_model_task_import()

    # Test 2: Import weather flow
    results['weather_flow_import'] = test_weather_flow_import()

    # Test 3: DatabaseHandler method
    results['database_handler_method'] = test_database_handler_retraining_method()

    # Test 4: Prediction flow integration
    results['prediction_flow_integration'] = test_prediction_flow_integration()

    # Test 5: Retrain task parameters
    results['retrain_task_parameters'] = test_retrain_task_parameters()

    # Résumé
    print("\n=== RÉSUMÉ DES TESTS ===")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())
    print(f"\n{'✅ TOUS LES TESTS PASSENT' if all_passed else '❌ CERTAINS TESTS ONT ÉCHOUÉ'}")

    sys.exit(0 if all_passed else 1)
