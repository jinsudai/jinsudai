"""
Script simple pour exécuter le pipeline d'entraînement consommation.

Usage:
    python scripts/run_training_pipeline_simple.py --features_path data/processed/consumption_features.parquet
"""
import argparse
import sys
from pathlib import Path
import pandas as pd

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.utils.models.model import train_model, evaluate_model
from ml.config import load_config
from ml.utils.data.data_preparation import split_data

def main():
    parser = argparse.ArgumentParser(description='Exécute le pipeline d\'entraînement consommation')
    parser.add_argument('--features_path', type=str, required=True, help='Chemin vers le fichier de features')
    parser.add_argument('--config_path', type=str, default='src/configs/consumption.yaml', help='Chemin vers la config')
    
    args = parser.parse_args()
    
    print(f"=== Pipeline d'entraînement consommation ===")
    print(f"Features: {args.features_path}")
    print(f"Config: {args.config_path}")
    print()
    
    # Vérifier que le fichier de features existe
    if not Path(args.features_path).exists():
        print(f"❌ Erreur: Le fichier features n'existe pas: {args.features_path}")
        sys.exit(1)
    
    try:
        # Charger la config
        config = load_config(config_path=args.config_path)
        target_column = config.get('data', {}).get('target_column', 'Valeur')
        
        # 1. Entraîner
        print("=== Étape 1: Entraînement ===")
        features_df = pd.read_parquet(args.features_path)
        
        # Préparer les données
        X = features_df.drop(columns=[target_column])
        y = features_df[target_column]
        
        model = train_model(X, y, model_type="random_forest")
        print(f"✅ Modèle entraîné")
        
        # 2. Évaluer
        print("\n=== Étape 2: Évaluation ===")
        _, X_test, _, y_test = split_data(
            features_df,
            test_size=0.2,
            random_state=42,
            target_column=target_column
        )
        
        eval_metrics = evaluate_model(model, X_test, y_test)
        print(f"✅ Évaluation terminée")
        print(f"Métriques: {eval_metrics}")
        
        # 3. Sauvegarder le modèle (simplifié)
        print("\n=== Étape 3: Sauvegarde modèle ===")
        model_path = "models/consumption_model.pkl"
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
        
        import joblib
        joblib.dump(model, model_path)
        print(f"✅ Modèle sauvegardé: {model_path}")
        
        print(f"\n=== Résultat ===")
        print(f"✅ Entraînement terminé avec succès")
        print(f"Métriques: {eval_metrics}")
        print(f"Model sauvegardé: {model_path}")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
