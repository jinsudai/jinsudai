#!/usr/bin/env python3

"""

Create HuggingFace Spaces for services defined in config.yaml

Triggers when config.yaml changes

"""



import os

import sys

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



def create_space(api, space_name, private=False):

    """Create a HuggingFace Space if it doesn't exist"""

    try:

        # Check if space already exists

        try:
            
            apiName=api.whoami()['name']
            api.space_info(f"{apiName}/{space_name}")

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

    """Main function: create all spaces from config.yaml"""

    # Create spaces for main services

    token = os.getenv("HF_TOKEN")

    if not token:

        print("[ERR] HF_TOKEN environment variable not set")

        sys.exit(1)

    

    api = HfApi(token=token)

    

    services = get_services()

    if not services:

        print("[*] No services configured in config.yaml")

    else:

        print(f"[*] Creating spaces for services: {', '.join(services)}")

        print("=" * 60)

        

        success_count = 0

        for service in services:

            if create_space(api, service):

                success_count += 1

        

        print("=" * 60)

        print(f"[*] Created {success_count}/{len(services)} service spaces")

    

    # Create spaces for satellites with their specific tokens

    satellites = get_satellites()

    if not satellites:

        print("[*] No satellites configured in config.yaml")

    else:

        print(f"[*] Creating spaces for satellites: {', '.join(satellites)}")

        print("=" * 60)

        

        success_count = 0

        for satellite in satellites:

            satellite_token = get_hf_token_for_service(satellite)

            if not satellite_token:

                print(f"[WARN] No HF_TOKEN found for satellite '{satellite}' (tried {satellite.upper()}_HF_TOKEN and HF_TOKEN)")

                continue

            

            satellite_api = HfApi(token=satellite_token)

            if create_space(satellite_api, satellite):

                success_count += 1

        

        print("=" * 60)

        print(f"[*] Created {success_count}/{len(satellites)} satellite spaces")



if __name__ == "__main__":

    main()

