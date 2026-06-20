"""
Gestion de l'inférence du modèle en production via MLflow.

Spécifications (voir SPECIFICATIONS.md) :
- Chargement modèle : Depuis MLflow (version production)
- Input : 50 features numériques dans DataFrame
- Output : Probabilité [0-1] + décision binaire
- Performance : < 100ms par requête
- Tracking : Validation des inputs, logs des prédictions

Classe principale :
- InferenceModel : Charge et utilise modèle en production
"""
import logging
import os
import mlflow
import mlflow.sklearn
import mlflow.pyfunc
import numpy as np
import pandas as pd

from ml.config import get_mlflow_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InferenceModel:
    """Classe pour charger et utiliser un modèle en production"""

    def __init__(
        self,
        mlflow_tracking_uri=None,
        experiment_name=None,
        config_path=None,
    ):
        """
        Initialise la connexion MLflow en utilisant la configuration.

        Args:
            mlflow_tracking_uri: URI du serveur MLflow (optionnel)
            experiment_name: Nom de l'expérience MLflow (optionnel)
            config_path: Chemin vers le fichier de configuration YAML (optionnel)
        """

        mlflow_config = get_mlflow_config(config_path=config_path)

        self.mlflow_tracking_uri = mlflow_tracking_uri or mlflow_config.get("tracking_uri")
        self.experiment_name = experiment_name or mlflow_config.get("experiment_name")
        self.default_model_name = mlflow_config.get("model_name")
        self.default_prod_alias = mlflow_config.get("prod_alias") or "prod"
        self.model = None
        self.model_version = None
        self.run_id = None

        if not self.mlflow_tracking_uri:
            raise ValueError(
                "Le paramètre 'mlflow_tracking_uri' est requis. "
                "Vérifiez la configuration MLflow ou fournissez-le explicitement."
            )

        mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        mlflow.set_experiment(self.experiment_name)
        logger.info(f"MLflow connecté à {self.mlflow_tracking_uri}")

    def load_production_model(self, model_name=None, alias_prod=None):
        """
        Charge le modèle en production depuis MLflow via Alias

        Args:
            model_name: Nom du modèle dans MLflow (optionnel)
            alias_prod: Alias pour la production (optionnel)

        Returns:
            Modèle chargé ou None en cas d'erreur
        """
        model_name = model_name or self.default_model_name
        alias_prod = alias_prod or self.default_prod_alias

        if not model_name:
            logger.error("Le nom du modèle MLflow n'est pas défini.")
            return False

        try:
            # Récupérer la version avec l'alias prod
            client = mlflow.tracking.MlflowClient()
            model_version = client.get_model_version_by_alias(model_name, alias_prod)

            if not model_version:
                logger.error(f"Aucune version avec l'alias '{alias_prod}' pour {model_name}")
                return False

            self.model_version = model_version.version
            self.run_id = model_version.run_id
            logger.info(f"Model registry source: {model_version.source}")

            # Charger le modèle via alias
            model_uri = f"models:/{model_name}@{alias_prod}"

            # Essayer d'abord avec sklearn (compatible modèles sklearn)
            try:
                self.model = mlflow.sklearn.load_model(model_uri)
                logger.info(f"Modèle {model_name} v{self.model_version} chargé via sklearn")
            except Exception as sklearn_error:
                logger.warning(
                    f"Chargement sklearn échoué ({sklearn_error}), "
                    f"tentative chargement pyfunc pour {model_uri}"
                )
                try:
                    self.model = mlflow.pyfunc.load_model(model_uri)
                    logger.info(f"Modèle {model_name} v{self.model_version} chargé via pyfunc")
                except Exception as pyfunc_error:
                    logger.warning(
                        f"Chargement pyfunc échoué ({pyfunc_error}), "
                        "tentative de chargement AutoGluon direct depuis les artefacts MLflow"
                    )
                    # Fallback sur le run source si le registry alias ne résout pas le bon chemin
                    run_id, artifact_path = self._parse_mlflow_source(model_version.source)
                    if run_id is None:
                        run_id = model_version.run_id
                    if artifact_path is None:
                        artifact_path = "model"

                    if run_id is not None:
                        run_uri = f"runs:/{run_id}/{artifact_path}"
                        try:
                            self.model = mlflow.pyfunc.load_model(run_uri)
                            logger.info(f"Modèle {model_name} v{self.model_version} chargé via run URI")
                        except Exception as run_pyfunc_error:
                            logger.warning(
                                f"Chargement pyfunc via run URI échoué ({run_pyfunc_error}), "
                                "tentative de chargement AutoGluon depuis les artefacts du run"
                            )
                            self.model = self._load_autogluon_from_registry(model_version)
                    else:
                        self.model = self._load_autogluon_from_registry(model_version)
                    if self.model is not None:
                        logger.info(f"Modèle {model_name} v{self.model_version} chargé directement comme AutoGluon")

            if self.model is None:
                logger.error(f"Impossible de charger le modèle {model_name} v{self.model_version}")
                return False

            logger.info(f"Modèle {model_name} v{self.model_version} prêt pour l'inférence")
            return True

        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle: {str(e)}")
            return False

    def _load_autogluon_from_registry(self, model_version):
        """Charge un modèle AutoGluon directement depuis les artefacts MLflow."""
        try:
            client = mlflow.tracking.MlflowClient()
            run_id, artifact_path = self._parse_mlflow_source(model_version.source)
            if run_id is None:
                run_id = model_version.run_id
            if artifact_path is None:
                artifact_path = 'model'

            if run_id is None and not model_version.source:
                logger.error("Impossible de déterminer le run_id du modèle MLflow pour le chargement AutoGluon")
                return None

            logger.info(
                f"Chargement AutoGluon depuis le registre MLflow: source={model_version.source}, "
                f"run_id={run_id}, artifact_path={artifact_path}"
            )

            target_dir = None
            if run_id is not None:
                try:
                    target_dir = client.download_artifacts(run_id, artifact_path)
                except Exception as download_error:
                    logger.warning(
                        f"Impossible de télécharger l'artefact '{artifact_path}' du run {run_id}: {download_error}"
                    )

            if not target_dir or not any(os.scandir(target_dir)):
                logger.info("Récupération de l'arborescence complète du run pour trouver le modèle AutoGluon")
                if run_id is not None:
                    target_dir = client.download_artifacts(run_id, "")
                if not target_dir or not any(os.scandir(target_dir)):
                    logger.info(f"Tentative de téléchargement direct depuis la source MLflow: {model_version.source}")
                    try:
                        target_dir = mlflow.artifacts.download_artifacts(model_version.source)
                    except Exception as source_download_error:
                        logger.warning(
                            f"Téléchargement direct depuis la source MLflow échoué: {source_download_error}"
                        )

            predictor_dir = self._find_autogluon_predictor_path(target_dir)

            if predictor_dir is None:
                logger.error("Aucun modèle AutoGluon trouvé dans les artefacts MLflow téléchargés")
                return None

            try:
                from autogluon.tabular import TabularPredictor
            except Exception as e:
                logger.error(f"AutoGluon non disponible pour le chargement du modèle: {e}")
                return None

            logger.info(f"Chargement AutoGluon depuis artefacts MLflow: {predictor_dir}")
            return TabularPredictor.load(predictor_dir)
        except Exception as e:
            logger.error(f"Erreur lors du chargement AutoGluon depuis le registre MLflow: {e}")
            return None

    @staticmethod
    def _parse_mlflow_source(source):
        """Extrait run_id et artifact_path d'une source MLflow de type runs:/..."""
        if not source:
            return None, None

        if source.startswith('runs:/'):
            source = source[len('runs:/'):]
            parts = source.split('/', 1)
            if len(parts) == 2:
                return parts[0], parts[1]
            if len(parts) == 1:
                return parts[0], None
        return None, None

    @staticmethod
    def _find_autogluon_predictor_path(base_dir):
        """Recherche le répertoire contenant predictor.pkl dans un artefact AutoGluon."""
        for root, _, files in os.walk(base_dir):
            if 'predictor.pkl' in files:
                return root
        return None

    def predict(self, X_data):
        """
        Génère des prédictions

        Args:
            X_data: Features pour la prédiction (DataFrame ou array)

        Returns:
            Prédictions et scores de confiance
        """
        if self.model is None:
            logger.error("Modèle non chargé")
            return None, None

        try:
            expected_features = None
            if hasattr(self.model, 'features') and callable(getattr(self.model, 'features')):
                expected_features = self.model.features()
            elif hasattr(self.model, 'feature_names_in_'):
                expected_features = list(self.model.feature_names_in_)
            elif hasattr(self.model, 'feature_names'):
                expected_features = list(self.model.feature_names)

            if expected_features is not None and isinstance(X_data, pd.DataFrame):
                missing_features = [f for f in expected_features if f not in X_data.columns]
                if missing_features:
                    logger.warning(
                        "Les colonnes attendues par le modèle sont manquantes : %s. "
                        "La prédiction sera effectuée avec toutes les colonnes disponibles.",
                        missing_features
                    )
                else:
                    X_data = X_data[expected_features]

            predictions = self.model.predict(X_data)

            confidence_scores = None
            if hasattr(self.model, 'predict_proba'):
                try:
                    proba = self.model.predict_proba(X_data)
                    if isinstance(proba, pd.DataFrame):
                        confidence_scores = (
                            proba[1].values if 1 in proba.columns else proba.iloc[:, 1].values
                        )
                    elif isinstance(proba, np.ndarray):
                        if proba.ndim == 2:
                            confidence_scores = proba[:, 1]
                        else:
                            confidence_scores = proba
                    else:
                        confidence_scores = np.asarray(proba)
                        if confidence_scores.ndim == 2:
                            confidence_scores = confidence_scores[:, 1]
                except (IndexError, KeyError, TypeError) as e:
                    logger.warning(f"Erreur accès predict_proba format: {e}, fallback sur prédictions")
                    confidence_scores = None
            elif hasattr(self.model, 'decision_function'):
                confidence_scores = np.abs(self.model.decision_function(X_data))

            logger.info(f"Prédictions générées pour {len(X_data)} échantillons")
            return predictions, confidence_scores

        except Exception as e:
            logger.error(f"Erreur lors de la prédiction: {str(e)}")
            return None, None

    def get_model_info(self):
        """Retourne les informations du modèle chargé"""
        if self.model is None:
            return None

        return {
            "model_type": type(self.model).__name__,
            "version": self.model_version,
            "run_id": self.run_id,
            "n_features": getattr(self.model, 'n_features_in_', 'unknown')
        }
