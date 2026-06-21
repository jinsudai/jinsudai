#!/usr/bin/env python3
"""
Push service files to HuggingFace Spaces
Triggers when Services/** or .env changes
Only pushes if actual changes exist (git diff check)
Copies .env to each service before pushing
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import HfApi

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

def get_services():
    """Read service list from config.yaml"""
    from ml.config.global_config import get_services_names
    return get_services_names()

def get_satellites():
    """Read satellite list from config.yaml"""
    from ml.config.global_config import get_satellites_names
    return get_satellites_names()

def get_hf_token_for_service(service_name):
    """Get HF_TOKEN for a specific service or satellite"""
    # Try satellite-specific token first (e.g., AIRFLOW_HF_TOKEN)
    satellite_token = os.getenv(f"{service_name.upper()}_HF_TOKEN")
    if satellite_token:
        return satellite_token
    # Fall back to default HF_TOKEN
    return os.getenv("HF_TOKEN")

def has_changes(path):
    """Check if there are changes between HEAD~1 and HEAD in a path"""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD", "--quiet", path],
            capture_output=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )
        return result.returncode != 0
    except Exception as e:
        print(f"[ERR] Git diff check failed: {str(e)}")
        return False

def check_critical_files_changed():
    """Check if any critical files have changed that require all services to be pushed"""
    repo_root = Path(__file__).parent.parent.parent
    critical_files = [
        repo_root / ".github" / "scripts" / "hf_push_services.py",
        repo_root / ".github" / "scripts" / "hf_create_spaces.py",
        repo_root / ".env"
    ]
    
    for critical_file in critical_files:
        if critical_file.exists() and has_changes(str(critical_file)):
            return True
    
    return False

def push_service_to_hf(api, service, username):
    """Push service directory to HuggingFace Space (includes .env)"""
    service_path = Path(__file__).parent.parent.parent / "Services" / service
    repo_root = Path(__file__).parent.parent.parent
    env_file = repo_root / ".env"
    toml_file = repo_root / "pyproject.toml"
    
    if not service_path.exists():
        print(f"[ERR] Service directory not found: {service_path}")
        return False
    
    try:
        # Copier .env dans le dossier service avant upload
        if env_file.exists():
            service_env_path = service_path / ".env"
            shutil.copy2(env_file, service_env_path)
            print(f"[*] Copied .env to {service}")

        # Copier pyproject.toml dans le dossier service avant upload
        #if toml_file.exists():
        #    service_toml_path = service_path / "pyproject.toml"
        #    shutil.copy2(toml_file, service_toml_path)
        #    print(f"[*] Copied pyproject.toml to {service}")

        # Copier le répertoire src dans le dossier service avant upload
        src_dir = repo_root / "src"
        service_src_path = service_path / "src"
        if src_dir.exists():
            if service_src_path.exists():
                shutil.rmtree(service_src_path)
            shutil.copytree(src_dir, service_src_path)
            print(f"[*] Copied src to {service}")
        
        space_id = f"{username}/{service}"
        
        # Upload the entire service directory to the space
        api.upload_folder(
            folder_path=str(service_path),
            repo_id=space_id,
            repo_type="space",
            commit_message=f"Update {service} from repository"
        )
        
        # Nettoyer: supprimer le .env et le src copiés localement (ne pas les commiter)
        service_env_path = service_path / ".env"
        if service_env_path.exists():
            service_env_path.unlink()

        if service_src_path.exists():
            shutil.rmtree(service_src_path)
        
        print(f"[OK] '{service}' pushed to HuggingFace Space")
        return True
    except Exception as e:
        print(f"[ERR] Failed to push '{service}': {str(e)}")
        return False

def main():
    """Main function: push only services with changes (or all if --force-push)"""
    # Parse command line arguments
    force_push = "--force-push" in sys.argv
    
    token = os.getenv("HF_TOKEN")
    if not token:
        print("[ERR] HF_TOKEN environment variable not set")
        sys.exit(1)
    
    api = HfApi(token=token)
    
    try:
        username = api.whoami()["name"]
    except Exception as e:
        print(f"[ERR] Failed to authenticate with HuggingFace: {str(e)}")
        sys.exit(1)
    
    services = get_services()
    satellites = get_satellites()
    all_spaces = services + satellites
    
    if not all_spaces:
        print("[*] No services or satellites configured in config.yaml")
        return
    
    # Check for changes in Services directory or .env
    services_dir = Path(__file__).parent.parent.parent / "Services"
    env_file = Path(__file__).parent.parent.parent / ".env"
    
    print("[*] Checking for changes...")
    print("=" * 60)
    
    spaces_to_push = []
    
    if force_push:
        # Mode force push: mettre à jour tous les services et satellites
        print("[*] Force push mode - will update all services and satellites")
        spaces_to_push = all_spaces
    elif check_critical_files_changed():
        # Si fichiers critiques ont changé, pousser tous les services et satellites
        print("[*] Critical files have changed - will push all services and satellites")
        spaces_to_push = all_spaces
    else:
        # Vérifier chaque service et satellite pour des changements
        for space in all_spaces:
            space_path = services_dir / space
            if space_path.exists() and has_changes(str(space_path)):
                print(f"[*] Changes detected in '{space}'")
                spaces_to_push.append(space)
    
    if not spaces_to_push:
        print("[*] No changes detected, skipping push")
        return
    
    print("=" * 60)
    print(f"[*] Pushing {len(spaces_to_push)} space(s)...")
    print("=" * 60)
    
    success_count = 0
    for space in spaces_to_push:
        # Get appropriate token for this space
        space_token = get_hf_token_for_service(space)
        if not space_token:
            print(f"[WARN] No HF_TOKEN found for '{space}' (tried {space.upper()}_HF_TOKEN and HF_TOKEN)")
            continue
        
        space_api = HfApi(token=space_token)
        try:
            space_username = space_api.whoami()["name"]
        except Exception as e:
            print(f"[ERR] Failed to authenticate with HuggingFace for '{space}': {str(e)}")
            continue
        
        if push_service_to_hf(space_api, space, space_username):
            success_count += 1
    
    print("=" * 60)
    print(f"[*] Pushed {success_count}/{len(spaces_to_push)} spaces")

if __name__ == "__main__":
    main()
