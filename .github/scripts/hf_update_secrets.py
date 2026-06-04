#!/usr/bin/env python3
"""
Update secrets in HuggingFace Spaces
Triggers when .github/scripts/secrets/ changes
Distributes AWS credentials + service-specific secrets to each space
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import HfApi

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def get_services():
    """Read service list from .env ServicesNames variable"""
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    services_str = os.getenv("ServicesNames", "")
    if not services_str:
        print("[ERR] ServicesNames not defined in .env")
        return []
    
    return [s.strip() for s in services_str.split(",") if s.strip()]

def _get_env_secret(env_var, context=""):
    """Helper to get environment variable and log warning if not found"""
    value = os.getenv(env_var)
    if not value:
        context_str = f" for {context}" if context else ""
        print(f"[WARN] '{env_var}' not defined{context_str}")
    return value


def get_shared_secrets():
    """Get AWS shared credentials"""
    shared_env_vars = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
        "AWS_REGION",
        "AWS_ENDPOINT_URL"
    ]
    
    secrets = {}
    for env_var in shared_env_vars:
        value = _get_env_secret(env_var)
        if value:
            secrets[env_var] = value
        else:
            print(f"[WARN] '{env_var}' not defined")
    
    return secrets

def get_service_secrets(service):
    """Get service-specific secrets from environment (e.g., AIRFLOW_PASSWORD)"""
    # Mapping of service -> environment variables
    service_secrets_map = {
        "Airflow": ["AIRFLOW_ADMIN_USER", "AIRFLOW_ADMIN_PASSWORD", "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN", "AIRFLOW__WEBSERVER__SECRET_KEY"],
        "MLflow": ["MLFLOW_POSTGRES_URI", "MLFLOW_S3_ENDPOINT_URL"],
        "JupyterLab": ["JUPYTER_TOKEN", "NEON_POSTGRES_URI"],
        "Streamlit": ["NEON_POSTGRES_URI"],
        "n8n": ["N8N_ENCRYPTION_KEY", "DB_TYPE", "DB_POSTGRESDB_USER", "DB_POSTGRESDB_PASSWORD", "DB_POSTGRESDB_HOST", "DB_POSTGRESDB_PORT", "DB_POSTGRESDB_DATABASE"],
        "Producer": ["KAFKA_PASSWORD"],
        "consumer": ["KAFKA_PASSWORD", "POSTGRES_URI", "MLFLOW_POSTGRES_URI", "MLFLOW_S3_ENDPOINT_URL"]
    }
    
    secrets = {}
    env_vars = service_secrets_map.get(service, [])
    
    if not env_vars:
        print(f"[WARN] No specific secrets mapped for service '{service}'")
        return secrets
    
    for env_var in env_vars:
        value = _get_env_secret(env_var, service)
        if value:
            secrets[env_var] = value
    
    return secrets

def add_space_secret(api, space_id, secret_name, secret_value):
    """Add or update a secret in a HuggingFace Space"""
    try:
        api.add_space_secret(
            repo_id=space_id,
            key=secret_name,
            value=secret_value
        )
        print(f"[OK] Secret '{secret_name}' updated in '{space_id}'")
        return True
    except Exception as e:
        print(f"[ERR] Failed to update secret '{secret_name}': {str(e)}")
        return False

def main():
    """Main function: update secrets in all spaces"""
    token = os.getenv("HF_TOKEN")
    if not token:
        print("[ERR] HF_TOKEN environment variable not set")
        sys.exit(1)
    
    api = HfApi(token=token)
    username = api.whoami()["name"]
    
    services = get_services()
    if not services:
        print("[*] No services configured in .env")
        return
    
    shared_secrets = get_shared_secrets()
    
    print("[*] Updating secrets in spaces...")
    print("=" * 60)
    
    for service in services:
        space_id = f"{username}/{service}"
        print(f"\n[*] Processing space: {space_id}")
        
        # Add shared AWS secrets
        if not shared_secrets:
            print(f"[WARN] No shared AWS secrets available")
        else:
            for secret_name, secret_value in shared_secrets.items():
                if not secret_value:
                    print(f"[WARN] {secret_name} is empty, skipping")
                else:
                    add_space_secret(api, space_id, secret_name, secret_value)
        
        # Add service-specific secrets
        service_secrets = get_service_secrets(service)
        if service_secrets:
            for secret_name, secret_value in service_secrets.items():
                add_space_secret(api, space_id, secret_name, secret_value)
    
    print("\n" + "=" * 60)
    print("[OK] Secrets update completed")

if __name__ == "__main__":
    main()
