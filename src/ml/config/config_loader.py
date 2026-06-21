"""
Gestion de la configuration centralisée.

Spécifications :
- Source : YAML centralisé + variables d'environnement
- Priorité : Env vars override config.yaml, env-specific override common
- Structure :
  - config.yaml (ou consumption.yaml, etc.) : config base
  - config.{env}.yaml (ex: config.dev.yaml) : overrides par environnement
- Variable ENV : dev (défaut), test, prod
- Utilisé par : tous les modules ML (data, models, monitoring)

Voir SPECIFICATIONS.md pour les variables attendues.
"""
import os
from pathlib import Path

import yaml

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs"

# Chemins par défaut pour chaque domaine
DEFAULT_CONSUMPTION_CONFIG = "consumption"
DEFAULT_SOLAR_PRODUCTION_CONFIG = "solar_production"


def _deep_merge(base: dict, override: dict) -> dict:
    """Fusionne profondément deux dictionnaires, override écrase base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_name: str = None, config_path: str = None) -> dict:
    """
    Charge la configuration YAML avec support des environnements.

    Utilisation flexible :
    - load_config("consumption") → charge consumption.yaml + consumption.{ENV}.yaml
    - load_config(config_name="consumption") → charge consumption.yaml + consumption.{ENV}.yaml
    - load_config(config_path="/abs/path/file.yaml") → charge le fichier spécifique
    - load_config() → charge config.yaml + config.{ENV}.yaml (défaut)

    Args:
        config_name: Nom de la config sans extension (ex: "consumption" → consumption.yaml)
        config_path: Chemin absolu vers un fichier YAML (ignore config_name et ENV si fourni)

    Returns:
        dict: Configuration fusionnée (base + env-specific + env vars override)

    Priority:
        1. Variables d'environnement (via get_config_value)
        2. Fichier env-specific (ex: consumption.prod.yaml)
        3. Fichier base (ex: consumption.yaml)
    """
    # Si chemin absolu fourni, charger directement
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Fichier de configuration introuvable: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # Utiliser config_name fourni, sinon défaut "config"
    config_base_name = config_name or "config"

    # Déterminer l'environnement (défaut: dev)
    env = os.getenv("ENVIRONMENT", "dev").lower()

    # Charger config base
    base_path = DEFAULT_CONFIG_DIR / f"{config_base_name}.yaml"
    config = {}
    if base_path.exists():
        with open(base_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # Charger overrides par environnement
    env_path = DEFAULT_CONFIG_DIR / f"{config_base_name}.{env}.yaml"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            env_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, env_config)

    return config


def get_nested(config, key_path, default=None):
    """Récupère une valeur imbriquée à partir d'une clé de type 'a.b.c'."""
    if config is None:
        return default

    current = config
    for key in key_path.split("."):
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def env_name_for_key(key_path):
    return key_path.replace(".", "_").upper()


def get_config_value(config, key_path, env_var=None, default=None):
    """Retourne la valeur d'une config avec override par variable d'environnement."""
    env_var = env_var or env_name_for_key(key_path)
    env_value = os.getenv(env_var)
    if env_value is not None:
        return env_value
    return get_nested(config, key_path, default)


def get_mlflow_config(config=None, config_path=None):
    """Retourne la configuration MLflow en appliquant les overrides d'environnement."""
    if config is None:
        config = load_config(config_path)

    return {
        "tracking_uri": get_config_value(config, "mlflow.tracking_uri", env_var="MLFLOW_TRACKING_URI"),
        "experiment_name": get_config_value(config, "mlflow.experiment_name", env_var="MLFLOW_EXPERIMENT_NAME", default="experiment"),
        "model_name": get_config_value(config, "mlflow.model_name", env_var="MLFLOW_MODEL_NAME", default="model"),
        "prod_alias": get_config_value(config, "mlflow.prod_alias", env_var="MLFLOW_PROD_ALIAS", default="prod"),
        "artifact_location": get_config_value(config, "mlflow.artifact_location", env_var="MLFLOW_ARTIFACT_LOCATION", default="jinsudai/mlflow"),
    }
