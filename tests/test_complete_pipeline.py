"""
Test du pipeline complet drift detection → retraining.
"""
import sys
from pathlib import Path

def test_drift_detection_integration():
    """Test que la détection de drift est intégrée dans prediction_flow."""
    print("=== TEST 1: Intégration drift detection dans prediction_flow ===")
    
    file_path = Path("src/ml/workflows/prediction_flow.py")
    content = file_path.read_text(encoding='utf-8')
    
    checks = [
        ("detect_drift_task", "Tâche detect_drift_task"),
        ("drift_info", "Variable drift_info"),
        ("drift_detection", "Clé drift_detection dans le retour")
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"[OK] {description} trouvé")
        else:
            print(f"[ERROR] {description} non trouvé")
            all_found = False
    
    return all_found

def test_retraining_integration():
    """Test que le retraining est intégré dans prediction_flow."""
    print("\n=== TEST 2: Intégration retraining dans prediction_flow ===")
    
    file_path = Path("src/ml/workflows/prediction_flow.py")
    content = file_path.read_text(encoding='utf-8')
    
    checks = [
        ("retrain_model_task", "Tâche retrain_model_task"),
        ("retraining_info", "Variable retraining_info"),
        ("drift_detected", "Variable drift_detected"),
        ("retraining", "Clé retraining dans le retour")
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"[OK] {description} trouvé")
        else:
            print(f"[ERROR] {description} non trouvé")
            all_found = False
    
    return all_found

def test_retraining_triggers_consumption_flow():
    """Test que retrain_model_task déclenche consumption_full_pipeline."""
    print("\n=== TEST 3: Déclenchement consumption_full_pipeline ===")
    
    file_path = Path("src/ml/workflows/prediction_tasks.py")
    content = file_path.read_text(encoding='utf-8')
    
    checks = [
        ("from ml.workflows.consumption_flow import consumption_full_pipeline", "Import consumption_full_pipeline"),
        ("consumption_full_pipeline(", "Appel consumption_full_pipeline"),
        ("consumption_result", "Variable consumption_result")
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"[OK] {description} trouvé")
        else:
            print(f"[ERROR] {description} non trouvé")
            all_found = False
    
    return all_found

def test_weather_flow_exists():
    """Test que le flow de mise à jour weather existe."""
    print("\n=== TEST 4: Existence update_weather_daily_flow ===")
    
    file_path = Path("src/ml/workflows/weather_flow.py")
    if not file_path.exists():
        print(f"[ERROR] Fichier {file_path} non trouvé")
        return False
    
    content = file_path.read_text(encoding='utf-8')
    
    if "def update_weather_daily_flow" in content:
        print("[OK] update_weather_daily_flow trouvé")
        return True
    else:
        print("[ERROR] update_weather_daily_flow non trouvé")
        return False

def test_weather_flow_uses_config():
    """Test que le flow weather lit la configuration."""
    print("\n=== TEST 5: Lecture configuration dans weather_flow ===")
    
    file_path = Path("src/ml/workflows/weather_flow.py")
    content = file_path.read_text(encoding='utf-8')
    
    checks = [
        ("load_config(config_path)", "Chargement de la config"),
        ("weather_latitude", "Lecture weather_latitude"),
        ("weather_longitude", "Lecture weather_longitude"),
        ("weather_location", "Lecture weather_location")
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"[OK] {description} trouvé")
        else:
            print(f"[ERROR] {description} non trouvé")
            all_found = False
    
    return all_found

def test_pipeline_flow_order():
    """Test l'ordre des étapes dans prediction_flow."""
    print("\n=== TEST 6: Ordre des étapes dans prediction_flow ===")
    
    file_path = Path("src/ml/workflows/prediction_flow.py")
    content = file_path.read_text(encoding='utf-8')
    
    # Vérifier l'ordre : drift detection puis retraining
    drift_pos = content.find("detect_drift_task")
    retrain_pos = content.find("retrain_model_task")
    
    if drift_pos > 0 and retrain_pos > 0:
        if drift_pos < retrain_pos:
            print(f"[OK] Ordre correct: drift detection avant retraining")
            return True
        else:
            print(f"[ERROR] Ordre incorrect: retraining avant drift detection")
            return False
    else:
        print(f"[ERROR] Impossible de trouver les positions")
        return False

def test_retraining_conditional_logic():
    """Test la logique conditionnelle du retraining."""
    print("\n=== TEST 7: Logique conditionnelle retraining ===")
    
    file_path = Path("src/ml/workflows/prediction_tasks.py")
    content = file_path.read_text(encoding='utf-8')
    
    checks = [
        ("if not enabled", "Vérification enabled"),
        ("if not drift_detected", "Vérification drift_detected"),
        ("if not pipeline.db_handler", "Vérification database handler"),
        ("if len(production_data) < min_samples", "Vérification min_samples")
    ]
    
    all_found = True
    for check, description in checks:
        if check in content:
            print(f"[OK] {description} trouvé")
        else:
            print(f"[ERROR] {description} non trouvé")
            all_found = False
    
    return all_found

if __name__ == "__main__":
    print("=== TESTS DU PIPELINE COMPLET ===\n")
    
    results = {}
    
    # Test 1: Intégration drift detection
    results['drift_detection_integration'] = test_drift_detection_integration()
    
    # Test 2: Intégration retraining
    results['retraining_integration'] = test_retraining_integration()
    
    # Test 3: Déclenchement consumption flow
    results['retraining_triggers_consumption'] = test_retraining_triggers_consumption_flow()
    
    # Test 4: Existence weather flow
    results['weather_flow_exists'] = test_weather_flow_exists()
    
    # Test 5: Lecture config weather
    results['weather_flow_uses_config'] = test_weather_flow_uses_config()
    
    # Test 6: Ordre des étapes
    results['pipeline_flow_order'] = test_pipeline_flow_order()
    
    # Test 7: Logique conditionnelle
    results['retraining_conditional_logic'] = test_retraining_conditional_logic()
    
    # Résumé
    print("\n=== RÉSUMÉ DES TESTS ===")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    print(f"\n{'✅ TOUS LES TESTS PASSENT' if all_passed else '❌ CERTAINS TESTS ONT ÉCHOUÉ'}")
    
    sys.exit(0 if all_passed else 1)
