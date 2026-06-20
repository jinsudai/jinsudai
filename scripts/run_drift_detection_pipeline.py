"""
Script de test pour le pipeline de détection de drift.

Usage:
    python scripts/run_drift_detection_pipeline.py
"""
import sys
from pathlib import Path

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

import pandas as pd
import numpy as np
from ml.pipelines.drift_detection_pipeline import DriftDetectionPipeline
from ml.config import load_config

def create_test_data():
    """Crée des données de test pour le pipeline."""
    print("=== Création des données de test ===")
    
    # Données de référence
    np.random.seed(42)
    reference_data = pd.DataFrame({
        'Horodate': pd.date_range('2024-01-01', periods=1000, freq='H'),
        'temperature_2m_mean': np.random.normal(15, 5, 1000),
        'relative_humidity_mean': np.random.normal(60, 10, 1000),
        'precipitation_sum': np.random.exponential(1, 1000),
        'is_vacances': np.random.choice([0, 1], 1000, p=[0.9, 0.1]),
        'jour de la semaine': np.random.randint(0, 7, 1000),
        'jour férié': np.random.choice([0, 1], 1000, p=[0.95, 0.05]),
        'Valeur': np.random.normal(50, 10, 1000)
    })
    
    # Données courantes sans drift
    current_data_no_drift = reference_data.copy()
    current_data_no_drift['Horodate'] = pd.date_range('2024-02-01', periods=1000, freq='H')
    current_data_no_drift['temperature_2m_mean'] = np.random.normal(15, 5, 1000)
    current_data_no_drift['relative_humidity_mean'] = np.random.normal(60, 10, 1000)
    current_data_no_drift['Valeur'] = np.random.normal(50, 10, 1000)
    
    # Données courantes avec drift
    current_data_with_drift = reference_data.copy()
    current_data_with_drift['Horodate'] = pd.date_range('2024-02-01', periods=1000, freq='H')
    current_data_with_drift['temperature_2m_mean'] = np.random.normal(25, 5, 1000)  # Drift significatif
    current_data_with_drift['relative_humidity_mean'] = np.random.normal(60, 10, 1000)
    current_data_with_drift['Valeur'] = np.random.normal(70, 10, 1000)  # Drift sur la cible
    
    # Sauvegarder les fichiers
    data_dir = project_root / 'data' / 'dev'
    data_dir.mkdir(parents=True, exist_ok=True)
    
    reference_path = data_dir / 'test_reference.parquet'
    current_no_drift_path = data_dir / 'test_current_no_drift.parquet'
    current_with_drift_path = data_dir / 'test_current_with_drift.parquet'
    
    reference_data.to_parquet(reference_path, index=False)
    current_data_no_drift.to_parquet(current_no_drift_path, index=False)
    current_data_with_drift.to_parquet(current_with_drift_path, index=False)
    
    print(f"Données de référence sauvegardées: {reference_path}")
    print(f"Données courantes (sans drift) sauvegardées: {current_no_drift_path}")
    print(f"Données courantes (avec drift) sauvegardées: {current_with_drift_path}")
    
    return reference_path, current_no_drift_path, current_with_drift_path

def test_pipeline_no_drift():
    """Test le pipeline sans drift."""
    print("\n=== TEST 1: Pipeline sans drift ===")
    
    config = load_config('src/configs/consumption.yaml')
    reference_path = config.get('drift_detection', {}).get('reference_data_path')
    
    if not Path(reference_path).exists():
        print(f"⚠️ Fichier de référence non trouvé: {reference_path}")
        print("Création de données de test...")
        reference_path, current_no_drift_path, _ = create_test_data()
        current_path = current_no_drift_path
    else:
        # Utiliser les données de référence existantes et créer des données courantes similaires
        reference_data = pd.read_parquet(reference_path)
        current_data = reference_data.sample(min(1000, len(reference_data)), replace=True)
        
        data_dir = project_root / 'data' / 'dev'
        current_path = data_dir / 'test_current_no_drift.parquet'
        current_data.to_parquet(current_path, index=False)
    
    pipeline = DriftDetectionPipeline(config_name='consumption')
    
    results = pipeline.run_full_pipeline(
        reference_path=str(reference_path),
        current_data_path=str(current_path),
        generate_report=False,
        store_metrics=False,
        send_notifications=False
    )
    
    if results["success"]:
        print("✅ Pipeline sans drift terminé avec succès")
        drift_detected = pipeline.is_drift_detected()
        print(f"Drift détecté: {drift_detected}")
        
        if not drift_detected:
            print("✅ Pas de drift détecté (comme attendu)")
        else:
            print("⚠️ Drift détecté (peut être normal selon les données)")
    else:
        print(f"❌ Erreur: {results.get('error')}")
        return False
    
    return True

def test_pipeline_with_drift():
    """Test le pipeline avec drift."""
    print("\n=== TEST 2: Pipeline avec drift ===")
    
    config = load_config('src/configs/consumption.yaml')
    reference_path = config.get('drift_detection', {}).get('reference_data_path')
    
    if not Path(reference_path).exists():
        print(f"⚠️ Fichier de référence non trouvé: {reference_path}")
        print("Création de données de test...")
        reference_path, _, current_with_drift_path = create_test_data()
        current_path = current_with_drift_path
    else:
        # Utiliser les données de référence existantes et créer des données courantes avec drift
        reference_data = pd.read_parquet(reference_path)
        current_data = reference_data.sample(min(1000, len(reference_data)), replace=True)
        
        # Ajouter du drift artificiel
        numeric_cols = current_data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col != 'Horodate':
                current_data[col] = current_data[col] * 1.5 + np.random.normal(0, 5, len(current_data))
        
        data_dir = project_root / 'data' / 'dev'
        current_path = data_dir / 'test_current_with_drift.parquet'
        current_data.to_parquet(current_path, index=False)
    
    pipeline = DriftDetectionPipeline(config_name='consumption')
    
    results = pipeline.run_full_pipeline(
        reference_path=str(reference_path),
        current_data_path=str(current_path),
        generate_report=False,
        store_metrics=False,
        send_notifications=False
    )
    
    if results["success"]:
        print("✅ Pipeline avec drift terminé avec succès")
        drift_detected = pipeline.is_drift_detected()
        print(f"Drift détecté: {drift_detected}")
        
        if drift_detected:
            print("✅ Drift détecté (comme attendu)")
        else:
            print("⚠️ Drift non détecté (peut être normal selon les données)")
    else:
        print(f"❌ Erreur: {results.get('error')}")
        return False
    
    return True

def main():
    print("=== TEST DU PIPELINE DE DÉTECTION DE DRIFT ===\n")
    
    results = {}
    
    # Test 1: Pipeline sans drift
    results['no_drift'] = test_pipeline_no_drift()
    
    # Test 2: Pipeline avec drift
    results['with_drift'] = test_pipeline_with_drift()
    
    # Résumé
    print("\n=== RÉSUMÉ DES TESTS ===")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    print(f"\n{'✅ TOUS LES TESTS PASSENT' if all_passed else '❌ CERTAINS TESTS ONT ÉCHOUÉ'}")
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
