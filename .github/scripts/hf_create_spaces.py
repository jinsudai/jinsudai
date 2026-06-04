#!/usr/bin/env python3
"""
Create HuggingFace Spaces for services defined in .env
Triggers when .env changes
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

def create_space(api, space_name, private=False):
    """Create a HuggingFace Space if it doesn't exist"""
    try:
        # Check if space already exists
        try:
            api.space_info(f"{api.whoami()['name']}/{space_name}")
            print(f"[*] Space '{space_name}' already exists")
            return True
        except:
            pass
        
        # Create space
        api.create_repo(
            repo_id=space_name,
            repo_type="space",
            space_sdk="docker",
            private=private,
            exist_ok=True
        )
        print(f"[OK] Space '{space_name}' created successfully")
        return True
    except Exception as e:
        print(f"[ERR] Failed to create space '{space_name}': {str(e)}")
        return False

def main():
    """Main function: create all spaces from .env"""
    token = os.getenv("HF_TOKEN")
    if not token:
        print("[ERR] HF_TOKEN environment variable not set")
        sys.exit(1)
    
    api = HfApi(token=token)
    
    services = get_services()
    if not services:
        print("[*] No services configured in .env")
        return
    
    print(f"[*] Creating spaces for services: {', '.join(services)}")
    print("=" * 60)
    
    success_count = 0
    for service in services:
        if create_space(api, service):
            success_count += 1
    
    print("=" * 60)
    print(f"[*] Created {success_count}/{len(services)} spaces")

if __name__ == "__main__":
    main()
