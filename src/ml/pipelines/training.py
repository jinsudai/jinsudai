"""
Pipeline complet d'entraînement : données -> validation -> entraînement -> monitoring.

Spécifications (voir SPECIFICATIONS.md) :
- Étapes :
  1. Data Loading : Charge depuis data/raw/
  2. Validation : Vérification schéma, valeurs manquantes
  3. Préparation : Nettoyage, normalisation
  4. Transformation : Feature engineering
  5. Entraînement : RandomForest ou Autogluon
  6. Évaluation : Métriques (R², MAE, RMSE selon domaine)
  7. Tracking : Log dans MLflow
  8. Monitoring : Performance baseline vs nouveau modèle
- Performance : < 1h complet
- Output : Modèle versionné MLflow + métriques

Classe principale :
- TrainingPipeline : Orchestration complète du cycle train
"""
import logging
import os
import shutil
from pathlib import Path

from ml.utils.data.data_loader import load_data
from ml.utils.data.data_validator import validate_data_quality, create_data_validation_report
from ml.utils.data.data_preparation import prepare_data, split_data
from ml.utils.data.data_transformer import clean_data
from ml.utils.models.model import train_model, evaluate_model
from ml.utils.monitoring.performance_monitor import run_monitoring, flatten_monitoring_metrics
from ml.utils.data.s3_handler import S3Handler
from ml.config import load_config, DEFAULT_CONSUMPTION_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrainingPipeline:
    """Pipeline complet pour le projet MLOps"""

    def __init__(self, config_name=DEFAULT_CONSUMPTION_CONFIG, model_name=None):
        """
        Initialise le pipeline avec la configuration.

        Args:
            config_name: Nom de la config (ex: "consumption", "solar_production")
                        Charge depuis src/ml/configs/{config_name}.yaml
            model_name: Nom du modèle (override de la config si fourni)
        """
        self.config = load_config(config_name=config_name)
        self.data = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.preprocessor = None
        self.feature_names = None
        self.model = None
        self.metrics = {}

        # Gestion des stages MLflow
        self.model_name = model_name or self.config.get('mlflow', {}).get('model_name', 'model')
        self.version_staging = None
        self.promotion_result = None

        # Track the actual data path used for training
        self.actual_data_path = None

        logger.info(f"Pipeline MLOps initialisé avec model_name={self.model_name}")

    def _download_train_from_s3(self, local_path: str) -> tuple:
        """
        Télécharge le dernier fichier train concaténé depuis S3.

        Args:
            local_path: Chemin local de destination (répertoire ou fichier)

        Returns:
            tuple: (success: bool, downloaded_path: str ou None)
        """
        try:
            from ml.config import load_config
            global_config = load_config('config.yaml')
            s3_config = global_config.get('s3', {})
            bucket = os.environ.get('AWS_BUCKET') or s3_config.get('bucket', 'data-store')

            s3_handler = S3Handler(bucket=bucket)
            result = s3_handler.download_latest_train_file(
                local_path=local_path,
                prefix="consumption/prepared",
                prioritize_dated=True
            )

            if result["status"] == "success":
                downloaded_path = result.get("local_path")
                logger.info(f"Fichier téléchargé depuis S3: {downloaded_path}")
                return True, downloaded_path
            else:
                logger.error(f"Erreur lors du téléchargement: {result.get('reason')}")
                return False, None

        except Exception as e:
            logger.error(f"Erreur lors du téléchargement depuis S3: {e}")
            return False, None

    def step_1_load_data(self, data_path=None, download_from_s3_if_missing=True):
        """Étape 1: Chargement des données"""
        logger.info("=== ÉTAPE 1: CHARGEMENT DES DONNÉES ===")

        # Utiliser le chemin depuis la config si non fourni
        if data_path is None:
            data_path = self.config.get('data', {}).get('train_path')

        # Vérifier si le fichier existe, sinon essayer de le télécharger depuis S3
        if not Path(data_path).exists():
            logger.warning(f"Fichier de données non trouvé: {data_path}")
            if download_from_s3_if_missing:
                logger.info("Tentative de téléchargement depuis S3...")
                # Télécharger avec le nom original depuis S3 (utiliser le répertoire parent)
                download_dir = str(Path(data_path).parent)
                success, downloaded_path = self._download_train_from_s3(download_dir)
                if not success or not downloaded_path:
                    logger.error("Impossible de télécharger le fichier depuis S3")
                    return False
                # Mettre à jour data_path avec le fichier téléchargé (nom original conservé)
                data_path = downloaded_path
                logger.info(f"Chemin du fichier téléchargé: {data_path}")
            else:
                logger.error("Fichier de données non trouvé et téléchargement S3 désactivé")
                return False

        # Store the actual path used
        self.actual_data_path = data_path
        self.data = load_data(data_path)
        print(f"Data loaded: {self.data.shape if self.data is not None else 'None'}")

        return self.data is not None

    def step_2_validate_data(self, save_report=True):
        """Étape 2: Validation des données"""
        logger.info("=== ÉTAPE 2: VALIDATION DES DONNÉES ===")

        if self.data is None:
            logger.error("Pas de données à valider")
            return False

        # Validation basique
        validation_results = validate_data_quality(self.data)
        logger.info(f"Résultats de validation: {validation_results['is_valid']}")

        if not validation_results['is_valid']:
            logger.warning("Attention: Problèmes de qualité détectés")

        # Rapport Evidently
        if save_report:
            try:
                create_data_validation_report(
                    self.data,
                    output_path=self.config['monitoring']['report_path']
                )
            except Exception as e:
                logger.warning(f"Rapport Evidently non généré: {e}")

        return validation_results['is_valid']

    def step_3_transform_data(self):
        """Étape 3: Transformation des données (ex: dates, colonnes sans nom)"""
        logger.info("=== ÉTAPE 3: TRANSFORMATION DES DONNÉES ===")

        if self.data is None:
            logger.error("Pas de données à transformer")
            return False

        try:
            self.data = clean_data(
                self.data,
                columns_to_drop=self.config.get('data', {}).get('drop_columns', [])
            )
            logger.info("✓ Données nettoyées et transformées")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la transformation des données: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def step_3_prepare_data(self):
        print("=== ÉTAPE 3: PRÉPARATION ET PRÉTRAITEMENT (stateless)===")

        if not self.step_3_transform_data():
            logger.error("Échec de la transformation des données, préparation interrompue")
            return False

        """Étape 3: Préparation et prétraitement avancé des données"""
        logger.info("=== ÉTAPE 3: PRÉPARATION ET PRÉTRAITEMENT (stateful)===")

        if self.data is None:
            logger.error("Pas de données à préparer")
            return False

        # Division train/test
        logger.info("  → Division train/test...")
        test_size = self.config['model']['test_size']
        random_state = self.config['model']['random_state']
        target_column = self.config['data'].get('target_column')
        logger.info(f"  i Colonne cible (config): {target_column}")

        self.X_train, self.X_test, self.y_train, self.y_test = split_data(
            self.data,
            test_size=test_size,
            random_state=random_state,
            target_column=target_column
        )

        logger.info(f"  ✓ Split effectué: train={self.X_train.shape}, test={self.X_test.shape}")

        # Prétraitement avancé (numériques, catégories, encoding)
        try:
            autogluon_mode = self.config['model'].get('model_type') == 'auto_gluon'

            if autogluon_mode:
                logger.info("  → Prétraitement AutoGluon désactivé (mode brut, AutoGluon gère lui-même le preprocessing)")
            else:
                logger.info("  → Prétraitement avancé (imputation, scaling, encoding)...")

            result = prepare_data(self.X_train, self.X_test, autogluon=autogluon_mode)
            self.X_train = result['X_train']
            self.X_test = result['X_test']
            self.preprocessor = result['preprocessor']
            self.feature_names = result['feature_names']

            logger.info(f"  ✓ Prétraitement effectué: {self.X_train.shape} (train), {self.X_test.shape} (test)")
            logger.info(f"  ✓ Features après preprocessing: {len(self.feature_names)}")

            return True
        except Exception as e:
            logger.error(f"Erreur lors du prétraitement: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def step_4_train_model(self):
        """Étape 4: Entraînement du modèle"""
        logger.info("=== ÉTAPE 4: ENTRAÎNEMENT DU MODÈLE ===")

        if self.X_train is None:
            logger.error("Pas de données d'entraînement")
            return False

        self.model = train_model(
            self.X_train,
            self.y_train,
            model_type=self.config['model']['model_type']
        )

        return self.model is not None

    def step_5_evaluate_model(self):
        """Étape 5: Évaluation du modèle"""
        logger.info("=== ÉTAPE 5: ÉVALUATION DU MODÈLE ===")

        if self.model is None:
            logger.error("Pas de modèle à évaluer")
            return False

        self.metrics = evaluate_model(self.model, self.X_test, self.y_test)

        return self.metrics is not None

    def step_6_monitor_performance(self):
        """Étape 6: Monitoring de la performance"""
        logger.info("=== ÉTAPE 6: MONITORING DE LA PERFORMANCE ===")

        if self.model is None:
            logger.error("Pas de modèle à monitorer")
            return False

        if self.X_train is None or self.X_test is None:
            logger.error("Pas de données de training/test pour le monitoring")
            return False

        try:
            self.monitoring_results = run_monitoring(
                model=self.model,
                X_train=self.X_train,
                X_test=self.X_test,
                y_train=self.y_train,
                y_test=self.y_test,
                feature_names=self.feature_names
            )

            if self.monitoring_results is None:
                logger.error("Monitoring non réalisé")
                return False

            logger.info(f"Résultats du monitoring: Drift={self.monitoring_results['drift']['drift_detected']}")
            logger.info(f"Performance test: {self.monitoring_results.get('performance_test')}")

            return True
        except Exception as e:
            logger.error(f"Erreur lors du monitoring de la performance: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def step_7_log_with_mlflow(self):
        """Étape 7: Logging avec MLflow"""
        logger.info("=== ÉTAPE 7: LOGGING AVEC MLFLOW ===")

        if self.model is None or not self.metrics:
            logger.error("Pas de modèle ou métriques à logger")
            return False

        try:
            from ml.utils.models.models_mlflow import log_training_session

            log_metrics = self.metrics.copy() if self.metrics else {}

            if getattr(self, 'monitoring_results', None):
                log_metrics.update(flatten_monitoring_metrics(self.monitoring_results))

            log_training_session(
                model=self.model,
                metrics=log_metrics,
                params=self.config['model'],
                experiment_name=self.config['mlflow']['experiment_name'],
                tracking_uri=self.config['mlflow']['tracking_uri'],
                artifact_location=self.config['mlflow'].get('artifact_location')
            )

            return True
        except Exception as e:
            logger.error(f"Erreur lors du logging MLflow: {e}")
            return False

    # Step interessante mais non fonctionnel (Refactoring necessaire mais non prioritaire)
    def step_8_cleanup_model(self):
        """Étape 8: Nettoyage du modèle local après MLflow logging"""
        logger.info("=== ÉTAPE 8: NETTOYAGE DU MODÈLE LOCAL ===")

        if self.model is None:
            logger.info("Pas de modèle à nettoyer")
            return True

        try:
            # Vérifier si c'est un modèle AutoGluon
            if type(self.model).__name__ == 'TabularPredictor':
                model_dir = getattr(self.model, 'path', None)
                if model_dir and os.path.exists(model_dir):
                    try:
                        shutil.rmtree(model_dir, ignore_errors=True)
                        logger.info(f"Modèle AutoGluon original supprimé: {model_dir}")
                    except Exception as e:
                        logger.warning(f"Impossible de supprimer le modèle AutoGluon original: {e}")
                else:
                    logger.info(f"Modèle AutoGluon non trouvé ou déjà supprimé: {model_dir}")
            else:
                logger.info("Modèle sklearn - pas de nettoyage nécessaire")

            return True
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
            return False

    def step_8_upload_trained_data_to_s3(self):
        """
        Étape 8: Upload du fichier train.parquet vers S3 après entraînement.
        Upload le fichier de données utilisé pour l'entraînement vers le prefix
        /consumption/trained/ sur S3 pour être utilisé par le retraining.

        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 8: UPLOAD DES DONNÉES ENTRAÎNÉES VERS S3 ===")

        try:
            # Charger la configuration S3
            global_config = load_config('config.yaml')
            s3_config = global_config.get('s3', {})
            bucket = os.environ.get('AWS_BUCKET') or s3_config.get('bucket', 'data-store')
            prefix = "consumption/trained/"

            logger.info(f"Upload vers S3: bucket={bucket}, prefix={prefix}")

            # Initialiser le handler S3
            s3_handler = S3Handler(bucket=bucket)

            if not s3_handler.s3_enabled:
                logger.warning("S3 non disponible (credentials manquants)")
                return False

            # Récupérer le chemin du fichier train utilisé (actual path, not config path)
            train_path = self.actual_data_path or self.config.get('data', {}).get('train_path')

            if not train_path or not Path(train_path).exists():
                logger.error(f"Fichier train non trouvé: {train_path}")
                return False

            # Utiliser le nom de fichier original (format: {start_date}_to_{end_date}_train.parquet)
            train_filename = Path(train_path).name
            s3_key = f"{prefix}{train_filename}"

            logger.info(f"Upload du fichier: {train_path}")
            logger.info(f"Vers: s3://{bucket}/{s3_key}")

            # Upload le fichier
            result = s3_handler.upload_file(
                local_path=train_path,
                s3_key=s3_key,
                metadata={
                    "filename": train_filename,
                    "source": "training_pipeline",
                    "type": "trained_data"
                }
            )

            if result["status"] == "success":
                logger.info(f"✅ Fichier uploadé avec succès: {result['s3_uri']}")
                return True
            elif result["status"] == "skipped":
                logger.info(f"ℹ️ Upload ignoré: {result['reason']}")
                return True
            else:
                logger.error(f"❌ Erreur lors de l'upload: {result.get('reason')}")
                return False

        except Exception as e:
            logger.error(f"Erreur lors de l'upload vers S3: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def step_9_manage_model_stages(self, metric_keys=None, min_improvement=0.0):
        """
        Étape 8: Gestion des Aliases du modèle (Staging -> Production)
        Fonctionne indépendamment - peut être appelée après fermeture de la run MLflow
        Support de plusieurs métriques (ex: pour prédiction énergétique)

        Args:
            metric_keys: Liste de métriques à utiliser pour la comparaison
                        Ex: ["mae", "rmse", "accuracy"] (ordre de priorité)
                        Par défaut: ["mae", "rmse", "accuracy"] pour prédiction énergétique
            min_improvement: Amélioration minimale requise en % (défaut: 0.0)

        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 8: GESTION DES ALIASES DU MODÈLE ===")

        # Définir les métriques par défaut pour prédiction énergétique
        if metric_keys is None:
            metric_keys = ["mae", "rmse", "accuracy"]
        elif isinstance(metric_keys, str):
            metric_keys = [metric_keys]

        try:
            import mlflow
            from ml.utils.models.models_mlflow import (
                promote_model_to_production,
                get_model_version_by_alias,
                register_model_version,
                set_mlflow_tracking
            )

            # Configurer MLflow (ne pas dépendre de la run active)
            tracking_uri = self.config['mlflow']['tracking_uri']
            experiment_name = self.config['mlflow']['experiment_name']
            set_mlflow_tracking(tracking_uri)
            mlflow.set_experiment(experiment_name)

            logger.info("\n[1/4] Récupération du run_id et enregistrement du modèle en Staging...")
            logger.info(f"  Métriques à comparer (priorité): {metric_keys}")

            # Récupérer le run_id de la dernière run
            client = mlflow.tracking.MlflowClient()

            # Chercher la dernière run de l'expérience
            experiment = client.get_experiment_by_name(experiment_name)
            if not experiment:
                logger.error(f"Expérience '{experiment_name}' non trouvée")
                return False

            # Récupérer les runs de l'expérience
            runs = client.search_runs(experiment_ids=[experiment.experiment_id], max_results=1)
            if not runs:
                logger.error("Aucune run trouvée dans l'expérience")
                return False

            run_id = runs[0].info.run_id
            logger.info(f"  ℹ Run trouvée: {run_id}")

            # Enregistrer le modèle
            try:
                model_version = register_model_version(self.model_name, run_id, artifact_path="model")
                if model_version is None:
                    logger.error("Impossible d'enregistrer la version du modèle")
                    return False

                self.version_staging = int(model_version.version)
                logger.info(f"  ✓ Modèle {self.model_name} v{self.version_staging} enregistré")
            except Exception as e:
                logger.error(f"  ✗ Erreur: {e}")
                return False

            if self.version_staging is None:
                logger.error("Impossible de récupérer la version du modèle")
                return False

            # Vérifier les versions existantes avec l'alias "prod"
            logger.info("\n[2/4] État des versions avec alias 'prod'...")
            try:
                prod_version = get_model_version_by_alias(self.model_name, "prod")
                if prod_version:
                    logger.info(f"  ℹ Version actuelle avec alias 'prod': v{prod_version.version}")
                else:
                    logger.info("  ℹ Aucune version avec alias 'prod' (première fois)")
            except Exception:
                logger.info("  ℹ Aucune version avec alias 'prod' (première fois)")

            # Promotion automatique
            logger.info("\n[3/4] Promotion automatique en Production (alias 'prod')...")

            # Promouvoir avec validation des métriques
            self.promotion_result = promote_model_to_production(
                model_name=self.model_name,
                version=self.version_staging,
                alias_prod="prod",
                metric_keys=metric_keys,
                min_improvement=min_improvement
            )

            # Résultat final
            logger.info("\n[4/4] Résultat:")
            logger.info("-" * 60)

            if self.promotion_result['success']:
                logger.info("  ✓ SUCCÈS - Modèle promu avec alias 'prod'")
                logger.info(f"    Version: {self.promotion_result['version']}")
                logger.info(f"    Alias: {self.promotion_result.get('alias_prod', 'prod')}")
                logger.info(f"    Métrique de décision: {self.promotion_result.get('metric_used', 'N/A')}")

                # Afficher tous les métriques de la nouvelle version
                if self.promotion_result.get('metrics_new'):
                    logger.info("    Métriques de la nouvelle version:")
                    for key, val in self.promotion_result['metrics_new'].items():
                        logger.info(f"      • {key}: {val:.4f}")

                # Afficher l'amélioration si disponible
                improvement = self.promotion_result.get('improvement')
                improvement_pct = self.promotion_result.get('improvement_pct')
                if improvement is not None and improvement_pct is not None:
                    logger.info(f"    Amélioration: {improvement:+.4f} ({improvement_pct:+.1f}%)")
            else:
                logger.info(f"  ℹ Modèle v{self.version_staging} pas promu")
                logger.info(f"    Raison: {self.promotion_result['reason']}")
                metric_used = self.promotion_result.get('metric_used', 'N/A')
                logger.info(f"    Métrique de décision: {metric_used}")
                improvement = self.promotion_result.get('improvement')
                improvement_pct = self.promotion_result.get('improvement_pct')
                if improvement is not None and improvement_pct is not None:
                    logger.info(f"    Amélioration: {improvement:+.4f} ({improvement_pct:+.1f}%)")

            logger.info("=" * 60)
            return True

        except Exception as e:
            logger.error(f"Erreur lors de la gestion des aliases: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def run_full_pipeline(self, data_path, download_from_s3=True):
        """Exécute le pipeline complet"""
        logger.info("\n" + "=" * 50)
        logger.info("DÉMARRAGE DU PIPELINE COMPLET")
        logger.info("=" * 50 + "\n")

        steps = [
            ("Chargement", lambda: self.step_1_load_data(data_path, download_from_s3)),
            ("Validation", self.step_2_validate_data),
            ("Transformation des données", self.step_3_transform_data),
            ("Préparation et Prétraitement", self.step_3_prepare_data),
            ("Entraînement", self.step_4_train_model),
            ("Évaluation", self.step_5_evaluate_model),
            ("Monitoring", self.step_6_monitor_performance),
            ("MLflow Logging", self.step_7_log_with_mlflow),
            ("Gestion des Stages", self.step_9_manage_model_stages),
            ("Upload des données entraînées vers S3", self.step_8_upload_trained_data_to_s3),
            ("Nettoyage du modèle", self.step_8_cleanup_model),
        ]

        for step_name, step_func in steps:
            try:
                if not step_func():
                    logger.error(f"Erreur à l'étape: {step_name}")
                    return False
            except Exception as e:
                logger.error(f"Exception à l'étape {step_name}: {e}")
                return False

        logger.info("\n" + "=" * 50)
        logger.info("PIPELINE TERMINÉ AVEC SUCCÈS")
        logger.info("=" * 50 + "\n")

        return True

