"""
Gestion de la configuration centralisée.

Spécifications :
- Source : YAML centralisé + variables d'environnement
- Priorité : Env vars override config.yaml
- Utilisé par : tous les modules ML (data, models, monitoring)

Voir SPECIFICATIONS.md pour les variables attendues.
"""
import os
from pathlib import Path

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "config.yaml"


def load_config(config_path=None):
    """Charge la configuration YAML depuis le dépôt."""
    path = Path(config_path or DEFAULT_CONFIG_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Fichier de configuration introuvable: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config or {}


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
