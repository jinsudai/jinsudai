#!/usr/bin/env python3
"""
Script pour configurer les GitHub Secrets à partir d'un fichier JSON local.

Usage:
    python setup_secrets.py --config secrets.json --repo owner/repo --token ghp_***

Le fichier secrets.json doit contenir les secrets au format JSON:
{
    "HF_TOKEN": "hf_xxx",
    "AWS_ACCESS_KEY_ID": "AKIA***",
    ...
}
"""

import json
import argparse
import sys
from pathlib import Path
import base64
import hashlib
from typing import Dict, Any

try:
    import requests
except ImportError:
    print("❌ Erreur: 'requests' n'est pas installé.")
    print("   Installez-le avec: pip install requests pynacl")
    sys.exit(1)

try:
    from nacl import public, utils, encoding
except ImportError:
    print("❌ Erreur: 'pynacl' n'est pas installé.")
    print("   Installez-le avec: pip install pynacl")
    sys.exit(1)


class GitHubSecretsManager:
    """Gestionnaire des secrets GitHub."""
    
    def __init__(self, repo: str, token: str):
        """
        Initialise le gestionnaire.
        
        Args:
            repo: Format "owner/repo"
            token: Token d'authentification GitHub (avec 'repo' et 'workflow' scopes)
        """
        self.repo = repo
        self.owner, self.repo_name = repo.split("/")
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        self.public_key = None
        self.public_key_id = None
    
    def _get_public_key(self) -> bool:
        """Récupère la clé publique pour le chiffrement des secrets."""
        url = f"{self.base_url}/repos/{self.repo}/actions/secrets/public-key"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            self.public_key = data["key"]
            self.public_key_id = data["key_id"]
            
            print(f"✅ Clé publique récupérée (ID: {self.public_key_id})")
            return True
        
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                print(f"❌ Erreur: Dépôt '{self.repo}' non trouvé ou pas d'accès")
            else:
                print(f"❌ Erreur HTTP {response.status_code}: {response.text}")
            return False
        except Exception as e:
            print(f"❌ Erreur lors de la récupération de la clé publique: {e}")
            return False
    
    def _encrypt_secret(self, secret_value: str) -> str:
        """
        Chiffre un secret avec la clé publique GitHub.
        
        Args:
            secret_value: Valeur du secret à chiffrer
        
        Returns:
            Valeur chiffrée encodée en base64
        """
        if not self.public_key:
            raise ValueError("La clé publique n'a pas été récupérée")
        
        # Décoder la clé publique
        public_key = public.PublicKey(self.public_key, encoder=encoding.Base64Encoder())
        
        # Créer une boîte scellée pour le chiffrement
        sealed_box = public.SealedBox(public_key)
        
        # Chiffrer le secret
        secret_bytes = secret_value.encode("utf-8")
        encrypted = sealed_box.encrypt(secret_bytes)
        
        # Encoder en base64
        return base64.b64encode(encrypted).decode("utf-8")
    
    def create_or_update_secret(self, secret_name: str, secret_value: str) -> bool:
        """
        Crée ou met à jour un secret GitHub.
        
        Args:
            secret_name: Nom du secret (ex: "HF_TOKEN")
            secret_value: Valeur du secret
        
        Returns:
            True si succès, False sinon
        """
        url = f"{self.base_url}/repos/{self.repo}/actions/secrets/{secret_name}"
        
        try:
            # Chiffrer le secret
            encrypted_value = self._encrypt_secret(secret_value)
            
            # Préparer le payload
            payload = {
                "encrypted_value": encrypted_value,
                "key_id": self.public_key_id
            }
            
            # Envoyer la requête
            response = requests.put(
                url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            status_code = response.status_code
            if status_code == 201:
                print(f"  ✅ Secret créé: {secret_name}")
            elif status_code == 204:
                print(f"  ✅ Secret mis à jour: {secret_name}")
            else:
                print(f"  ⚠️  Réponse inattendue ({status_code}): {secret_name}")
            
            return True
        
        except requests.exceptions.HTTPError as e:
            print(f"  ❌ Erreur HTTP {response.status_code} pour {secret_name}: {response.text}")
            return False
        except Exception as e:
            print(f"  ❌ Erreur lors de la création du secret {secret_name}: {e}")
            return False
    
    def create_or_update_secrets(self, secrets: Dict[str, str]) -> Dict[str, bool]:
        """
        Crée ou met à jour plusieurs secrets.
        
        Args:
            secrets: Dictionnaire {nom_secret: valeur_secret}
        
        Returns:
            Dictionnaire avec les résultats {nom_secret: succès}
        """
        if not self._get_public_key():
            return {name: False for name in secrets.keys()}
        
        results = {}
        print(f"\n📝 Configuration de {len(secrets)} secrets...")
        
        for secret_name, secret_value in secrets.items():
            # Passer les secrets vides
            if not secret_value:
                print(f"  ⏭️  Ignoré (vide): {secret_name}")
                results[secret_name] = None
                continue
            
            # Créer ou mettre à jour
            success = self.create_or_update_secret(secret_name, secret_value)
            results[secret_name] = success
        
        return results
    
    def list_secrets(self) -> bool:
        """Liste tous les secrets configurés."""
        url = f"{self.base_url}/repos/{self.repo}/actions/secrets"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            secrets = data.get("secrets", [])
            
            if not secrets:
                print("❌ Aucun secret configuré")
                return False
            
            print(f"\n✅ Secrets configurés ({len(secrets)}):")
            for secret in secrets:
                created = secret["created_at"]
                updated = secret["updated_at"]
                print(f"  • {secret['name']}")
                print(f"    - Créé: {created}")
                print(f"    - Mis à jour: {updated}")
            
            return True
        
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des secrets: {e}")
            return False


def load_secrets_from_file(config_file: Path) -> Dict[str, str]:
    """Charge les secrets depuis un fichier JSON."""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            secrets = json.load(f)
        
        if not isinstance(secrets, dict):
            print(f"❌ Erreur: Le fichier doit contenir un objet JSON")
            return {}
        
        print(f"✅ {len(secrets)} secret(s) chargé(s) depuis {config_file}")
        return secrets
    
    except FileNotFoundError:
        print(f"❌ Erreur: Fichier '{config_file}' non trouvé")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Erreur de parsing JSON: {e}")
        return {}
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(
        description="Configure les GitHub Secrets à partir d'un fichier JSON"
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Fichier JSON contenant les secrets (ex: secrets.json)"
    )
    parser.add_argument(
        "--repo",
        type=str,
        required=True,
        help="Dépôt GitHub au format owner/repo (ex: SustCoop/MLOps)"
    )
    parser.add_argument(
        "--token",
        type=str,
        help="Token GitHub (GITHUB_TOKEN). Si non fourni, utilise GITHUB_TOKEN env"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lister les secrets existants sans en ajouter"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Afficher les secrets qui seraient configurés sans les créer"
    )
    
    args = parser.parse_args()
    
    # Récupérer le token
    if not args.token:
        import os
        args.token = os.getenv("GITHUB_TOKEN")
        if not args.token:
            print("❌ Erreur: Token GitHub non fourni")
            print("   Utilisez --token ou la variable d'environnement GITHUB_TOKEN")
            sys.exit(1)
    
    # Initialiser le gestionnaire
    manager = GitHubSecretsManager(args.repo, args.token)
    
    # Mode list
    if args.list:
        print(f"📋 Listing des secrets pour {args.repo}...")
        manager.list_secrets()
        return
    
    # Charger les secrets
    secrets = load_secrets_from_file(args.config)
    if not secrets:
        sys.exit(1)
    
    # Mode dry-run
    if args.dry_run:
        print(f"\n🧪 Mode DRY-RUN - Les secrets suivants seraient configurés:")
        for name, value in secrets.items():
            masked_value = value[:3] + "*" * (len(value) - 6) if len(value) > 6 else "***"
            print(f"  • {name} = {masked_value}")
        return
    
    # Configurer les secrets
    print(f"🔐 Configuration des secrets pour {args.repo}...")
    results = manager.create_or_update_secrets(secrets)
    
    # Résumé
    print("\n" + "=" * 60)
    success_count = sum(1 for v in results.values() if v is True)
    skipped_count = sum(1 for v in results.values() if v is None)
    failed_count = sum(1 for v in results.values() if v is False)
    
    print(f"📊 Résumé:")
    print(f"  ✅ Succès: {success_count}")
    print(f"  ⏭️  Ignorés: {skipped_count}")
    print(f"  ❌ Erreurs: {failed_count}")
    
    if failed_count > 0:
        print("\n❌ Certains secrets n'ont pas pu être configurés")
        sys.exit(1)
    else:
        print("\n✅ Tous les secrets ont été configurés avec succès!")


if __name__ == "__main__":
    main()
