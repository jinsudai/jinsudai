"""
Script d'entrée pour le pipeline de mise à jour météo quotidienne.

Usage:
    python run_pipeline.py --days_ahead 7
"""
import argparse
import sys
import os

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from ml.workflows.weather_flow import update_weather_daily_flow

def main():
    parser = argparse.ArgumentParser(description='Exécute le pipeline de mise à jour météo quotidienne')
    parser.add_argument('--config_path', type=str, default='src/configs/consumption.yaml', help='Chemin vers la config')
    parser.add_argument('--weather_source_path', type=str, default=None, help='Chemin vers le fichier source brut')
    parser.add_argument('--weather_prod_path', type=str, default=None, help='Chemin vers le fichier prod traité')
    parser.add_argument('--days_ahead', type=int, default=7, help='Nombre de jours à récupérer en avance')
    parser.add_argument('--upload_to_s3', action='store_true', help='Uploader les fichiers sur S3')
    parser.add_argument('--s3_bucket', type=str, default=None, help='Nom du bucket S3')
    parser.add_argument('--s3_prefix', type=str, default='weather', help='Préfixe S3 pour les fichiers')
    parser.add_argument('--aws_access_key_id', type=str, default=None, help='AWS access key ID')
    parser.add_argument('--aws_secret_access_key', type=str, default=None, help='AWS secret access key')
    parser.add_argument('--aws_region', type=str, default='us-east-1', help='AWS region')
    parser.add_argument('--endpoint_url', type=str, default=None, help='URL endpoint custom pour S3-compatible services')
    
    args = parser.parse_args()
    
    print(f"=== Exécution du pipeline de mise à jour météo quotidienne ===")
    print(f"Jours en avance: {args.days_ahead}")
    if args.upload_to_s3:
        print(f"Upload S3 activé: bucket={args.s3_bucket}, prefix={args.s3_prefix}")
    
    result = update_weather_daily_flow(
        config_path=args.config_path,
        weather_source_path=args.weather_source_path,
        weather_prod_path=args.weather_prod_path,
        days_ahead=args.days_ahead,
        upload_to_s3=args.upload_to_s3,
        s3_bucket=args.s3_bucket,
        s3_prefix=args.s3_prefix,
        aws_access_key_id=args.aws_access_key_id,
        aws_secret_access_key=args.aws_secret_access_key,
        aws_region=args.aws_region,
        endpoint_url=args.endpoint_url
    )
    
    print(f"\n=== Résultat ===")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Fichier source: {result.get('source_path')}")
        print(f"Fichier prod: {result.get('prod_path')}")
        print(f"Nouveaux enregistrements: {result.get('n_new_records')}")
        print(f"Total enregistrements: {result.get('n_total_records')}")
        
        if result.get('s3_info'):
            print(f"\n=== Upload S3 ===")
            if result['s3_info'].get('source', {}).get('status') == 'success':
                print(f"Source: {result['s3_info']['source']['s3_uri']}")
            if result['s3_info'].get('prod', {}).get('status') == 'success':
                print(f"Prod: {result['s3_info']['prod']['s3_uri']}")
    
    return result

if __name__ == "__main__":
    main()
