"""
Pipeline complet de détection de drift : données référence -> données production -> détection drift -> stockage/notifications.

Spécifications (voir SPECIFICATIONS.md) :
- Étapes :
  1. Chargement données référence : Depuis fichier Parquet (entraînement)
  2. Chargement données production : Depuis PostgreSQL ou fichier
  3. Détection data drift : PSI sur features
  4. Détection concept drift : Distribution prédictions vs cibles
  5. Génération rapport : Evidently AI
  6. Stockage métriques : PostgreSQL / MLflow
  7. Notifications : Email si drift détecté

- Performance : < 5s complet
- Input : Données référence + données courantes
- Output : Métriques drift + rapport HTML

Classe principale :
- DriftDetectionPipeline : Orchestration complète du cycle de détection de drift
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd

from ml.utils.monitoring.drift_detector import (
    load_reference_data,
    load_production_data,
    run_drift_detection,
    generate_evidently_report,
    save_evidently_report_to_mlflow
)
from ml.config import load_config
from ml.config.global_config import get_database_uri
from .database_handler import DatabaseHandler
from ml.utils.s3_handler import S3Handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DriftDetectionPipeline:
    """Pipeline complet pour la détection de drift"""

    def __init__(self, config_name: str = "consumption", db_uri: Optional[str] = None):
        """
        Initialise le pipeline de détection de drift.

        Args:
            config_name: Nom de la config (ex: "consumption", "solar_production")
            db_uri: URI de connexion PostgreSQL (optionnel)
        """
        self.config = load_config(config_name=config_name)
        self.db_uri = db_uri or get_database_uri()

        # Charger la configuration globale pour Evidently et S3
        global_config = load_config('config.yaml')
        self.evidently_config = global_config.get('evidently', {})
        self.s3_config = global_config.get('s3', {})

        self.reference_data = None
        self.current_data = None
        self.db_handler = None
        self.drift_results = None
        self.evidently_report = None

        logger.info(f"Pipeline de détection de drift initialisé avec config={config_name}")

    def step_1_load_reference_data(self, reference_path: Optional[str] = None,
                                   download_from_s3_if_missing: bool = True) -> bool:
        """
        Étape 1: Chargement des données de référence.

        Args:
            reference_path: Chemin vers le fichier de référence (optionnel)
            download_from_s3_if_missing: Télécharger depuis S3 si le fichier n'existe pas

        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 1: CHARGEMENT DES DONNÉES DE RÉFÉRENCE ===")

        # Utiliser le chemin depuis la config si non fourni
        if reference_path is None:
            drift_config = self.config.get('drift_detection', {})
            reference_path = drift_config.get('reference_data_path')

        if reference_path is None:
            logger.error("Aucun chemin de données de référence fourni")
            return False

        # Convertir en chemin absolu si relatif
        if not Path(reference_path).is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent
            reference_path = project_root / reference_path

        # Vérifier si le fichier existe, sinon essayer de le télécharger depuis S3
        if not Path(reference_path).exists():
            logger.warning(f"Fichier de référence non trouvé: {reference_path}")

            if download_from_s3_if_missing:
                logger.info("Tentative de téléchargement depuis S3...")
                success = self._download_reference_from_s3(reference_path)
                if not success:
                    logger.error("Impossible de télécharger le fichier depuis S3")
                    return False
            else:
                logger.error("Fichier de référence non trouvé et téléchargement S3 désactivé")
                return False

        target_column = self.config.get('data', {}).get('target_column', 'Valeur')
        feature_columns = self.config.get('data', {}).get('feature_columns')

        self.reference_data = load_reference_data(
            reference_path=reference_path,
            target_column=target_column,
            feature_columns=feature_columns
        )

        if self.reference_data is None:
            logger.error("Impossible de charger les données de référence")
            return False

        logger.info(f"Données de référence chargées: {len(self.reference_data)} enregistrements")
        return True

    def _download_reference_from_s3(self, local_path: str) -> bool:
        """
        Télécharge le dernier fichier train.parquet depuis S3.

        Args:
            local_path: Chemin local de destination

        Returns:
            True si succès, False sinon
        """
        try:
            # Charger la configuration S3
            global_config = load_config('config.yaml')
            s3_config = global_config.get('s3', {})

            bucket = s3_config.get('bucket', 'data-store')

            # Chercher dans le préfixe consumption/trained pour les fichiers train
            prefix = "consumption/trained"

            logger.info(f"Recherche sur S3: bucket={bucket}, prefix={prefix}")

            # Initialiser le handler S3
            s3_handler = S3Handler(bucket=bucket)

            if not s3_handler.s3_enabled:
                logger.warning("S3 non disponible (credentials manquants)")
                return False

            # Lister les fichiers train.parquet
            files = s3_handler.list_files(prefix=prefix)
            train_files = [f for f in files if 'train' in f and f.endswith('.parquet')]

            if not train_files:
                logger.warning(f"Aucun fichier train.parquet trouvé dans s3://{bucket}/{prefix}/")
                return False

            # Trouver le plus récent
            train_files_sorted = sorted(train_files, reverse=True)
            latest_file = train_files_sorted[0]

            logger.info(f"Fichier le plus récent sur S3: {latest_file}")

            # Télécharger le fichier
            local_path_obj = Path(local_path)
            local_path_obj.parent.mkdir(parents=True, exist_ok=True)

            result = s3_handler.download_file(
                s3_key=latest_file,
                local_path=str(local_path),
                overwrite=True
            )

            if result["status"] == "success":
                logger.info(f"Fichier téléchargé depuis S3: {local_path}")
                return True
            else:
                logger.error(f"Erreur lors du téléchargement: {result.get('reason')}")
                return False

        except Exception as e:
            logger.error(f"Erreur lors du téléchargement depuis S3: {e}")
            return False

    def step_2_load_current_data(self, current_data_path: Optional[str] = None,
                                 limit: int = 1000,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> bool:
        """
        Étape 2: Chargement des données courantes (production).

        Args:
            current_data_path: Chemin vers le fichier de données courantes (optionnel)
            limit: Nombre maximum d'enregistrements depuis la BD
            start_date: Date de début pour filtrer les données (optionnel)
            end_date: Date de fin pour filtrer les données (optionnel)

        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 2: CHARGEMENT DES DONNÉES COURANTES ===")

        # Priorité: fichier fourni -> base de données
        if current_data_path:
            # Charger depuis un fichier
            if not Path(current_data_path).is_absolute():
                project_root = Path(__file__).parent.parent.parent.parent
                current_data_path = project_root / current_data_path

            try:
                self.current_data = pd.read_parquet(current_data_path)
                logger.info(f"Données courantes chargées depuis fichier: {len(self.current_data)} enregistrements")
                return True
            except Exception as e:
                logger.error(f"Impossible de charger les données courantes depuis fichier: {e}")
                return False

        # Charger depuis la base de données
        if self.db_uri:
            if self.db_handler is None:
                self.db_handler = DatabaseHandler(db_uri=self.db_uri)

            if not self.db_handler.verify_connection():
                logger.error("Impossible de se connecter à la base de données")
                return False

            self.current_data = load_production_data(
                db_handler=self.db_handler,
                limit=limit,
                start_date=start_date,
                end_date=end_date
            )

            if self.current_data is None:
                logger.error("Impossible de charger les données de production")
                return False

            logger.info(f"Données courantes chargées depuis BD: {len(self.current_data)} enregistrements")
            return True
        else:
            logger.error("Aucun fichier ou URI de base de données fourni pour les données courantes")
            return False

    def step_3_detect_drift(self) -> bool:
        """
        Étape 3: Détection de drift (data drift + concept drift).

        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 3: DÉTECTION DE DRIFT ===")

        if self.reference_data is None or self.current_data is None:
            logger.error("Données de référence ou courantes manquantes")
            return False

        # Vérifier le nombre minimum d'échantillons
        drift_config = self.config.get('drift_detection', {})
        min_samples = drift_config.get('min_samples_for_detection', 96)

        if len(self.current_data) < min_samples:
            logger.warning(f"Pas assez d'échantillons pour détecter le drift ({len(self.current_data)} < {min_samples})")
            return False

        # Configuration de la détection
        detection_config = {
            "data_drift_threshold": drift_config.get('data_drift_threshold', 0.1),
            "concept_drift_threshold": drift_config.get('concept_drift_threshold', 0.15),
            "feature_drift_threshold": drift_config.get('feature_drift_threshold', 0.2),
            "feature_columns": self.config.get('data', {}).get('feature_columns'),
            "target_column": self.config.get('data', {}).get('target_column', 'Valeur')
        }

        # Exécuter la détection
        self.drift_results = run_drift_detection(
            reference_data=self.reference_data,
            current_data=self.current_data,
            config=detection_config
        )

        if self.drift_results is None:
            logger.error("Erreur lors de la détection de drift")
            return False

        # Logger les résultats
        data_drift_detected = self.drift_results.get('data_drift', {}).get('drift_detected', False)
        concept_drift_detected = self.drift_results.get('concept_drift', {}).get('drift_detected', False)
        overall_drift_detected = self.drift_results.get('overall_drift_detected', False)

        logger.info(f"Data drift détecté: {data_drift_detected}")
        logger.info(f"Concept drift détecté: {concept_drift_detected}")
        logger.info(f"Drift global détecté: {overall_drift_detected}")

        if overall_drift_detected:
            logger.warning("⚠️ DRIFT DÉTECTÉ - Action requise")

        return True

    def step_4_generate_evidently_report(self, output_path: Optional[str] = None, save_to_workspace: bool = False, save_to_s3: bool = False) -> bool:
        """
        Étape 4: Génération du rapport Evidently.

        Args:
            output_path: Chemin pour sauvegarder le rapport HTML (optionnel)
            save_to_workspace: Sauvegarder le rapport dans le workspace Evidently UI local
            save_to_s3: Sauvegarder le rapport sur S3

        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 4: GÉNÉRATION DU RAPPORT EVIDENTLY ===")

        if self.reference_data is None or self.current_data is None:
            logger.error("Données de référence ou courantes manquantes")
            return False

        # Générer le rapport
        report, report_dict = generate_evidently_report(
            reference_data=self.reference_data,
            current_data=self.current_data,
            output_path=output_path,
            report_name=f"drift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        if report is None:
            logger.error("Impossible de générer le rapport Evidently")
            return False

        self.evidently_report = report
        logger.info("Rapport Evidently généré avec succès")

        # Sauvegarder dans le workspace Evidently UI local si demandé
        if save_to_workspace and self.evidently_config.get('save_to_workspace', False):
            try:
                from ml.utils.monitoring.drift_detector import save_evidently_report_to_workspace

                # Préparer les métadonnées
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "config_name": self.config.get('name', 'unknown')
                }

                # Tags
                tags = ["drift_detection"]
                if self.drift_results and self.drift_results.get('overall_drift_detected', False):
                    tags.append("drift_detected")

                success = save_evidently_report_to_workspace(
                    report=report,
                    project_name="energy_consumption",
                    workspace_path=self.evidently_config.get('workspace_path', './evidently_workspace'),
                    metadata=metadata,
                    tags=tags
                )

                if success:
                    logger.info("Rapport sauvegardé dans le workspace Evidently UI")
                else:
                    logger.warning("Échec de la sauvegarde dans le workspace Evidently UI")

            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde dans le workspace Evidently UI: {e}")

        # Sauvegarder sur S3 si demandé
        if save_to_s3 and self.evidently_config.get('save_to_s3', False):
            try:
                from ml.utils.monitoring.drift_detector import save_evidently_report_to_s3

                # Préparer les métadonnées
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "config_name": self.config.get('name', 'unknown')
                }

                success = save_evidently_report_to_s3(
                    report=report,
                    s3_bucket=self.evidently_config.get('s3_bucket', 'evidently-reports'),
                    s3_prefix=self.evidently_config.get('s3_prefix', 'evidently_reports'),
                    metadata=metadata
                )

                if success:
                    logger.info("Rapport sauvegardé sur S3")
                else:
                    logger.warning("Échec de la sauvegarde sur S3")

            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde sur S3: {e}")

        return True

    def step_5_store_metrics(self, run_id: Optional[str] = None) -> bool:
        """
        Étape 5: Stockage des métriques de drift.

        Args:
            run_id: ID de la run MLflow (optionnel)

        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 5: STOCKAGE DES MÉTRIQUES ===")

        if self.drift_results is None:
            logger.error("Aucun résultat de drift à stocker")
            return False

        # Stocker dans MLflow
        if self.evidently_report is not None:
            success = save_evidently_report_to_mlflow(
                report=self.evidently_report,
                report_dict=self.drift_results,
                run_id=run_id
            )
            if success:
                logger.info("Métriques stockées dans MLflow")
            else:
                logger.warning("Impossible de stocker les métriques dans MLflow")
        else:
            logger.warning("Rapport Evidently non disponible pour le stockage MLflow")

        return True

    def step_6_send_notifications(self) -> bool:
        """
        Étape 6: Envoi des notifications si drift détecté.

        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 6: ENVOI DES NOTIFICATIONS ===")

        if self.drift_results is None:
            logger.error("Aucun résultat de drift disponible")
            return False

        # Vérifier si le drift est détecté
        overall_drift_detected = self.drift_results.get('overall_drift_detected', False)

        if not overall_drift_detected:
            logger.info("Pas de drift détecté, pas de notification nécessaire")
            return True

        # Vérifier si les notifications sont activées
        email_config = self.config.get('email', {})
        if not email_config.get('enabled', False):
            logger.info("Notifications email désactivées")
            return True

        # Importer et utiliser le notifier
        try:
            from ml.utils.notifications.email_notifier import EmailNotifier

            notifier = EmailNotifier()
            success = notifier.notify_drift_detected(self.drift_results)

            if success:
                logger.info("Notification email envoyée avec succès")
            else:
                logger.warning("Impossible d'envoyer la notification email")

            return success
        except ImportError:
            logger.warning("EmailNotifier non disponible")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la notification: {e}")
            return False

    def run_full_pipeline(self,
                          reference_path: Optional[str] = None,
                          current_data_path: Optional[str] = None,
                          current_data_limit: int = 1000,
                          generate_report: bool = True,
                          report_output_path: Optional[str] = None,
                          store_metrics: bool = True,
                          send_notifications: bool = True,
                          mlflow_run_id: Optional[str] = None,
                          download_from_s3: bool = True,
                          save_to_workspace: bool = False,
                          save_to_s3: bool = False,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Exécute le pipeline complet de détection de drift.

        Args:
            reference_path: Chemin vers les données de référence
            current_data_path: Chemin vers les données courantes (optionnel)
            current_data_limit: Limite d'enregistrements depuis la BD
            generate_report: Générer le rapport Evidently
            report_output_path: Chemin pour sauvegarder le rapport
            store_metrics: Stocker les métriques
            send_notifications: Envoyer les notifications
            mlflow_run_id: ID de la run MLflow
            download_from_s3: Télécharger depuis S3 si le fichier de référence n'existe pas
            save_to_workspace: Sauvegarder le rapport dans le workspace Evidently UI local
            save_to_s3: Sauvegarder le rapport sur S3
            start_date: Date de début pour filtrer les données de production (optionnel)
            end_date: Date de fin pour filtrer les données de production (optionnel)

        Returns:
            Dict avec les résultats du pipeline
        """
        logger.info("=== DÉBUT DU PIPELINE DE DÉTECTION DE DRIFT ===")

        results = {
            "success": False,
            "steps_completed": [],
            "drift_results": None,
            "error": None
        }

        try:
            # Étape 1: Chargement données référence
            if not self.step_1_load_reference_data(reference_path, download_from_s3):
                results["error"] = "Échec du chargement des données de référence"
                return results
            results["steps_completed"].append("load_reference_data")

            # Étape 2: Chargement données courantes
            if not self.step_2_load_current_data(current_data_path, current_data_limit, start_date, end_date):
                results["error"] = "Échec du chargement des données courantes"
                return results
            results["steps_completed"].append("load_current_data")

            # Étape 3: Détection de drift
            if not self.step_3_detect_drift():
                results["error"] = "Échec de la détection de drift"
                return results
            results["steps_completed"].append("detect_drift")
            results["drift_results"] = self.drift_results

            # Étape 4: Génération rapport Evidently
            if generate_report:
                if not self.step_4_generate_evidently_report(report_output_path, save_to_workspace, save_to_s3):
                    logger.warning("Échec de la génération du rapport Evidently")
                else:
                    results["steps_completed"].append("generate_evidently_report")

            # Étape 5: Stockage des métriques
            if store_metrics:
                if not self.step_5_store_metrics(mlflow_run_id):
                    logger.warning("Échec du stockage des métriques")
                else:
                    results["steps_completed"].append("store_metrics")

            # Étape 6: Notifications
            if send_notifications:
                if not self.step_6_send_notifications():
                    logger.warning("Échec de l'envoi des notifications")
                else:
                    results["steps_completed"].append("send_notifications")

            results["success"] = True
            logger.info("=== PIPELINE TERMINÉ AVEC SUCCÈS ===")

        except Exception as e:
            logger.error(f"Erreur lors de l'exécution du pipeline: {e}")
            import traceback
            traceback.print_exc()
            results["error"] = str(e)

        return results

    def get_drift_results(self) -> Optional[Dict[str, Any]]:
        """
        Retourne les résultats de la détection de drift.

        Returns:
            Dict avec les résultats ou None
        """
        return self.drift_results

    def is_drift_detected(self) -> bool:
        """
        Vérifie si un drift a été détecté.

        Returns:
            True si drift détecté, False sinon
        """
        if self.drift_results is None:
            return False
        return self.drift_results.get('overall_drift_detected', False)
