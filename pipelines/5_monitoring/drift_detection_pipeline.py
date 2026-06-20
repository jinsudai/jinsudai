"""
Script simple pour exécuter le pipeline de détection de drift.

Usage:
    python pipelines/drift_detection/drift_detection_pipeline.py --reference_path data/dev/train_consumption.parquet
    python pipelines/drift_detection/drift_detection_pipeline.py --reference_path data/dev/train_consumption.parquet --current_data_path data/processed/current_data.parquet
    python pipelines/drift_detection/drift_detection_pipeline.py --reference_path data/dev/train_consumption.parquet --db_uri postgresql://user:pass@host:port/db
"""
import argparse
import sys
from pathlib import Path

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from ml.pipelines.drift_detection_pipeline import DriftDetectionPipeline

def main():
    parser = argparse.ArgumentParser(description='Exécute le pipeline de détection de drift')
    parser.add_argument('--config_name', type=str, default='consumption', 
                        help='Nom de la config (consumption, solar_production)')
    parser.add_argument('--reference_path', type=str, default=None, 
                        help='Chemin vers le fichier de données de référence (entraînement). Si non fourni, utilise la config et télécharge depuis S3 si nécessaire')
    parser.add_argument('--current_data_path', type=str, default=None, 
                        help='Chemin vers le fichier de données courantes (optionnel, utilise BD si non fourni)')
    parser.add_argument('--current_data_limit', type=int, default=1000, 
                        help='Nombre maximum d\'enregistrements depuis la BD')
    parser.add_argument('--db_uri', type=str, default=None, 
                        help='URI de connexion PostgreSQL (optionnel)')
    parser.add_argument('--generate_report', action='store_true', default=True, 
                        help='Générer le rapport Evidently')
    parser.add_argument('--report_output_path', type=str, default=None, 
                        help='Chemin pour sauvegarder le rapport HTML (optionnel)')
    parser.add_argument('--store_metrics', action='store_true', default=True, 
                        help='Stocker les métriques dans MLflow/PostgreSQL')
    parser.add_argument('--send_notifications', action='store_true', default=True, 
                        help='Envoyer les notifications email si drift détecté')
    parser.add_argument('--mlflow_run_id', type=str, default=None, 
                        help='ID de la run MLflow (optionnel)')
    parser.add_argument('--download_from_s3', action='store_true', default=True, 
                        help='Télécharger depuis S3 si le fichier de référence n\'existe pas')
    
    args = parser.parse_args()
    
    print(f"=== Pipeline de détection de drift ===")
    print(f"Config: {args.config_name}")
    print(f"Données référence: {args.reference_path or 'Depuis config/S3'}")
    print(f"Données courantes: {args.current_data_path or 'Base de données'}")
    print(f"Limite données courantes: {args.current_data_limit}")
    print(f"Téléchargement S3: {args.download_from_s3}")
    print()
    
    # Vérifier le fichier de données courantes si fourni
    if args.current_data_path and not Path(args.current_data_path).exists():
        print(f"❌ Erreur: Le fichier de données courantes n'existe pas: {args.current_data_path}")
        sys.exit(1)
    
    try:
        # Initialiser le pipeline
        pipeline = DriftDetectionPipeline(
            config_name=args.config_name,
            db_uri=args.db_uri
        )
        
        # Exécuter le pipeline complet
        results = pipeline.run_full_pipeline(
            reference_path=args.reference_path,
            current_data_path=args.current_data_path,
            current_data_limit=args.current_data_limit,
            generate_report=args.generate_report,
            report_output_path=args.report_output_path,
            store_metrics=args.store_metrics,
            send_notifications=args.send_notifications,
            mlflow_run_id=args.mlflow_run_id,
            download_from_s3=args.download_from_s3
        )
        
        if results["success"]:
            print(f"\n✅ Pipeline terminé avec succès")
            print(f"Étapes complétées: {', '.join(results['steps_completed'])}")
            
            # Afficher les résultats de drift
            drift_results = results.get('drift_results')
            if drift_results:
                data_drift = drift_results.get('data_drift', {})
                concept_drift = drift_results.get('concept_drift', {})
                overall_drift = drift_results.get('overall_drift_detected', False)
                
                print(f"\n=== Résultats de détection de drift ===")
                print(f"Data drift détecté: {data_drift.get('drift_detected', False)}")
                if data_drift.get('drift_detected', False):
                    print(f"  Features avec drift: {data_drift.get('drifted_features_count', 0)}/{data_drift.get('total_features_analyzed', 0)}")
                    print(f"  Score drift global: {data_drift.get('overall_drift_score', 0):.4f}")
                
                print(f"Concept drift détecté: {concept_drift.get('drift_detected', False)}")
                print(f"Drift global détecté: {overall_drift}")
                
                if overall_drift:
                    print(f"\n⚠️ DRIFT DÉTECTÉ - Action requise")
        else:
            print(f"\n❌ Erreur lors de l'exécution du pipeline")
            print(f"Erreur: {results.get('error', 'Unknown')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
