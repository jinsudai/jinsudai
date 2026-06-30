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
- MonitoringPipeline : Orchestration complète du cycle de monitoring
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import requests

import numpy as np
import pandas as pd

from ml.utils.monitoring.drift_detector import (
    load_reference_data,
    run_drift_detection,
    generate_evidently_report
)
from ml.config import load_config
from ml.config.global_config import get_database_uri
from ml.utils.data.s3_handler import S3Handler
from ml.utils.models.models_mlflow import get_model_version_by_alias

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MonitoringPipeline:
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

        # Charger la configuration globale pour Evidently, S3 et Email
        project_root = Path(__file__).parent.parent.parent.parent
        global_config_path = project_root / 'config.yaml'
        global_config = load_config(config_path=str(global_config_path))
        self.evidently_config = global_config.get('evidently', {})
        self.s3_config = global_config.get('s3', {})
        self.email_config = global_config.get('email', {})

        self.reference_data = None
        self.current_data = None
        self.db_handler = None
        self.drift_results = None
        self.evidently_report = None

        logger.info(f"Pipeline de détection de drift initialisé avec config={config_name}")

    def step_1_health_check_api(self) -> bool:
        """
        Étape 1: Health check de l'API JinsudAPI.

        Returns:
            True si succès, False sinon
        """
        logger.info("")
        logger.info("=== ÉTAPE 1: HEALTH CHECK API ===")
        logger.info("Vérification de la disponibilité de l'API JinsudAPI...")

        model_info = self._get_model_info_from_api()

        if model_info:
            model_name = model_info.get('model_name', 'unknown')
            model_version = model_info.get('model_version', 'unknown')
            logger.info(f"  ✓ API fonctionnelle - Modèle: {model_name}, Version: {model_version}")
            return True
        else:
            logger.error("  ✗ Health check échoué - Impossible de récupérer les infos du modèle")

            # Envoyer une alerte email si le health check échoue
            if self.email_config and self.email_config.get('enabled', False):
                try:
                    from ml.utils.notifications.email_notifier import EmailNotifier
                    notifier = EmailNotifier(config=self.email_config)
                    notifier.notify_api_health_check_failed(
                        api_url=self.config.get('fastapi', {}).get('url', 'unknown'),
                        error="Impossible de récupérer les infos du modèle depuis l'API"
                    )
                    logger.info("  ✓ Alerte email envoyée")
                except Exception as e:
                    logger.warning(f"  ✗ Impossible d'envoyer l'alerte email: {e}")

            return False

    def step_2_load_reference_data(self, reference_path: Optional[str] = None,
                                   download_from_s3_if_missing: bool = True) -> bool:
        """
        Étape 2: Chargement des données de référence.

        Args:
            reference_path: Chemin vers le fichier de référence (optionnel)
            download_from_s3_if_missing: Télécharger depuis S3 si le fichier n'existe pas

        Returns:
            True si succès, False sinon
        """
        logger.info("")
        logger.info("=== ÉTAPE 2: CHARGEMENT DES DONNÉES DE RÉFÉRENCE ===")

        # Utiliser le chemin depuis la config si non fourni
        if reference_path is None:
            drift_config = self.config.get('drift_detection', {})
            reference_path = drift_config.get('reference_data_path')

        if reference_path is None:
            logger.error("  ✗ Chemin des données de référence non spécifié")
            return False

        logger.info(f"Chemin des données de référence: {reference_path}")

        # Convertir en chemin absolu si relatif
        if not Path(reference_path).is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent
            reference_path = project_root / reference_path

        # Vérifier si le fichier existe, sinon essayer de le télécharger depuis S3
        if not Path(reference_path).exists():
            logger.warning(f"  ✗ Fichier de référence non trouvé: {reference_path}")

            if download_from_s3_if_missing:
                logger.info("  → Tentative de téléchargement depuis S3...")
                # Utiliser le répertoire parent comme destination
                local_dir = Path(reference_path).parent
                downloaded_path = self._download_reference_from_s3(str(local_dir))
                if downloaded_path is None:
                    logger.error("  ✗ Impossible de télécharger le fichier depuis S3")
                    return False
                # Mettre à jour reference_path avec le chemin réel du fichier téléchargé
                reference_path = downloaded_path
                logger.info(f"  ✓ Fichier téléchargé: {reference_path}")
            else:
                logger.error("  ✗ Fichier de référence non trouvé et téléchargement S3 désactivé")
                return False

        target_column = self.config.get('data', {}).get('target_column', 'Valeur')
        feature_columns = self.config.get('data', {}).get('feature_columns')

        self.reference_data = load_reference_data(
            reference_path=reference_path,
            target_column=target_column,
            feature_columns=feature_columns
        )

        if self.reference_data is None:
            logger.error("  ✗ Impossible de charger les données de référence")
            return False

        logger.info(f"  ✓ Données de référence chargées: {len(self.reference_data)} enregistrements, {len(self.reference_data.columns)} colonnes")
        return True

    def _download_reference_from_s3(self, local_dir: str) -> Optional[str]:
        """
        Télécharge le dernier fichier train.parquet depuis S3 en conservant son nom original.

        Args:
            local_dir: Répertoire local de destination

        Returns:
            Chemin complet du fichier téléchargé si succès, None sinon
        """
        try:
            # Charger la configuration S3
            global_config = load_config('config.yaml')
            s3_config = global_config.get('s3', {})

            bucket = s3_config.get('bucket', 'data-store')

            # Chercher dans le préfixe consumption/reference pour les fichiers de référence
            prefix = "consumption/prepared"

            # Initialiser le handler S3
            s3_handler = S3Handler(bucket=bucket)

            # Télécharger avec le nom original depuis S3 dans le répertoire de destination
            result = s3_handler.download_latest_train_file(
                local_path=local_dir,
                prefix=prefix,
                prioritize_dated=True
            )

            if result["status"] != "success":
                logger.error(f"Erreur lors du téléchargement: {result.get('reason')}")
                return None

            logger.info(f"Fichier téléchargé depuis S3: {result.get('local_path')}")
            return result.get('local_path')

        except Exception as e:
            logger.error(f"Erreur lors du téléchargement depuis S3: {e}")
            return None

    def _get_model_info_from_api(self) -> Dict[str, Optional[str]]:
        """
        Récupère les informations du modèle depuis l'API via l'endpoint /health.

        Returns:
            Dict avec model_name et model_version, ou dict vide en cas d'échec
        """
        try:
            # Récupérer l'URL de l'API depuis la config
            project_root = Path(__file__).resolve().parents[3]
            config_path = project_root / 'config.yaml'
            global_config = load_config(config_path=str(config_path))

            api_url = global_config.get('fastapi', {}).get('url')
            if not api_url:
                logger.warning("URL de l'API FastAPI non configurée")
                return {}

            # Nettoyer l'URL
            api_url = api_url.rstrip('/')
            health_url = f"{api_url}/health"

            logger.info(f"Récupération des infos du modèle depuis l'API: {health_url}")
            response = requests.get(health_url, timeout=10)

            if response.status_code != 200:
                logger.warning(f"Erreur API health: {response.status_code} - {response.text}")
                return {}

            health_data = response.json()
            model_name = health_data.get('model_name')
            model_version = health_data.get('model_version')
            model_info = {
                'model_name': model_name,
                'model_version': model_version
            }
            logger.info(f"Infos du modèle récupérées depuis l'API - Nom: {model_name}, Version: {model_version}")
            return model_info

        except Exception as e:
            logger.warning(f"Impossible de récupérer les infos du modèle depuis l'API: {e}")
            return {}

    def _generate_reference_predictions(self, reference_data: pd.DataFrame) -> Optional[np.ndarray]:
        """
        Génère des prédictions sur reference_data via JinsudAPI.

        Args:
            reference_data: DataFrame de référence pour générer les prédictions

        Returns:
            Prédictions de référence ou None en cas d'échec
        """
        try:
            logger.info("Génération des prédictions de référence via JinsudAPI")

            # Récupérer l'URL de l'API depuis la config (fichier à la racine du projet)
            project_root = Path(__file__).resolve().parents[3]
            config_path = project_root / 'config.yaml'
            global_config = load_config(config_path=str(config_path))

            api_url = global_config.get('fastapi', {}).get('url')
            predict_endpoint = global_config.get('fastapi', {}).get('predict_endpoint', '/predict/batch')

            if not api_url:
                logger.warning("URL de l'API FastAPI non configurée")
                return None

            # Nettoyer l'URL pour éviter les doubles slashes
            api_url = api_url.rstrip('/')
            predict_endpoint = predict_endpoint.lstrip('/')

            full_url = f"{api_url}/{predict_endpoint}"
            logger.info(f"Appel de l'API: {full_url}")

            # Préparer les données pour l'API
            # L'API attend des champs spécifiques: Horodate, temperature_2m_mean, relative_humidity_mean, etc.
            requests_data = []

            for idx, row in reference_data.iterrows():
                # Mapping des colonnes vers le format attendu par l'API
                # Convertir les Timestamps en chaînes ISO
                horodate_value = row.get('Horodate', row.get('horodate', row.get('timestamp', datetime.now())))
                if hasattr(horodate_value, 'isoformat'):
                    horodate_value = horodate_value.isoformat()
                elif isinstance(horodate_value, str):
                    pass  # Déjà une chaîne
                else:
                    horodate_value = str(horodate_value)

                request_data = {
                    "Horodate": horodate_value,
                    "temperature_2m_mean": row.get('temperature_2m_mean', 0.0),
                    "relative_humidity_mean": row.get('relative_humidity_mean', 0.0),
                    "precipitation_sum": row.get('precipitation_sum', 0.0),
                    "is_vacances": row.get('is_vacances', row.get('is_vacation', 0)),
                    "jour_de_la_semaine": row.get('jour de la semaine', row.get('jour_de_la_semaine', 'Lundi')),
                    "jour_ferie": row.get('jour férié', row.get('jour_ferie', 0))
                }
                requests_data.append(request_data)

            # Appel de l'API
            response = requests.post(full_url, json=requests_data, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Erreur API: {response.status_code} - {response.text}")
                return None

            # Extraire les prédictions de la réponse
            predictions_data = response.json()
            reference_predictions = np.array([pred['prediction'] for pred in predictions_data])

            logger.info(f"{len(reference_predictions)} prédictions de référence générées via API")
            return reference_predictions

        except Exception as e:
            logger.warning(f"Impossible de générer les prédictions de référence via API: {e}")
            return None

    def _download_latest_train_from_s3(self) -> bool:
        """
        Télécharge le dernier fichier train.parquet depuis S3 (préfixe consumption/).

        Returns:
            True si succès, False sinon
        """
        try:
            # Charger la configuration S3
            global_config = load_config('config.yaml')
            s3_config = global_config.get('s3', {})

            bucket = s3_config.get('bucket', 'data-store')

            # Chercher dans le préfixe consumption/prepared pour les fichiers train générés
            prefix = "consumption/prepared"

            # Initialiser le handler S3
            s3_handler = S3Handler(bucket=bucket)

            # Télécharger le fichier dans un répertoire temporaire
            project_root = Path(__file__).parent.parent.parent.parent
            temp_dir = project_root / "data" / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            local_path = temp_dir / "current_train.parquet"

            # Utiliser la méthode partagée
            result = s3_handler.download_latest_train_file(
                local_path=str(local_path),
                prefix=prefix,
                prioritize_dated=True
            )

            if result["status"] == "success":
                self.current_data = pd.read_parquet(local_path)
                logger.info(f"Fichier téléchargé depuis S3: {local_path}")
                logger.info(f"Données courantes chargées: {len(self.current_data)} enregistrements")
                return True
            else:
                logger.error(f"Erreur lors du téléchargement: {result.get('reason')}")
                return False

        except Exception as e:
            logger.error(f"Erreur lors du téléchargement depuis S3: {e}")
            return False

    def step_3_load_current_data(self, current_data_path: Optional[str] = None,
                                 limit: int = 1000,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> bool:
        """
        Étape 3: Chargement des données courantes (production).

        Args:
            current_data_path: Chemin vers le fichier de données courantes (optionnel)
            limit: Nombre maximum d'enregistrements depuis la BD
            start_date: Date de début pour filtrer les données (optionnel)
            end_date: Date de fin pour filtrer les données (optionnel)

        Returns:
            True si succès, False sinon
        """
        logger.info("")
        logger.info("=== ÉTAPE 3: CHARGEMENT DES DONNÉES COURANTES ===")

        # Priorité: fichier fourni -> S3
        if current_data_path:
            logger.info(f"Chargement depuis fichier: {current_data_path}")
            # Charger depuis un fichier
            if not Path(current_data_path).is_absolute():
                project_root = Path(__file__).parent.parent.parent.parent
                current_data_path = project_root / current_data_path

            try:
                self.current_data = pd.read_parquet(current_data_path)
                logger.info(f"  ✓ Données courantes chargées: {len(self.current_data)} enregistrements, {len(self.current_data.columns)} colonnes")
                return True
            except Exception as e:
                logger.error(f"  ✗ Impossible de charger les données courantes depuis fichier: {e}")
                return False

        # Télécharger le dernier train.parquet depuis S3 (par défaut)
        logger.info("Téléchargement du dernier train.parquet depuis S3...")
        success = self._download_latest_train_from_s3()
        if success:
            logger.info(f"  ✓ Données courantes chargées: {len(self.current_data)} enregistrements, {len(self.current_data.columns)} colonnes")
            return True
        else:
            logger.error("  ✗ Impossible de télécharger depuis S3")
            return False

    def step_4_detect_drift(self) -> bool:
        """
        Étape 4: Détection de drift (data drift + concept drift).

        Returns:
            True si succès, False sinon
        """
        logger.info("")
        logger.info("=== ÉTAPE 4: DÉTECTION DE DRIFT ===")

        if self.reference_data is None or self.current_data is None:
            logger.error("Données de référence ou courantes manquantes")
            return False

        # Vérifier le nombre minimum d'échantillons
        drift_config = self.config.get('drift_detection', {})
        min_samples = drift_config.get('min_samples_for_detection', 96)

        logger.info(f"Données disponibles - Référence: {len(self.reference_data)} échantillons, Courant: {len(self.current_data)} échantillons")

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

        logger.info(f"Seuils de détection - Data drift: {detection_config['data_drift_threshold']}, Concept drift: {detection_config['concept_drift_threshold']}")

        # Générer les prédictions via l'API pour le concept drift
        reference_predictions = None
        current_predictions = None

        logger.info("Génération des prédictions via API pour concept drift...")
        # Générer les prédictions de référence via l'API
        if self.reference_data is not None:
            reference_predictions = self._generate_reference_predictions(self.reference_data)
            if reference_predictions is not None:
                logger.info(f"  ✓ Prédictions de référence générées: {len(reference_predictions)}")
            else:
                logger.warning("  ✗ Échec génération prédictions de référence")

        # Générer les prédictions courantes via l'API
        if self.current_data is not None:
            current_predictions = self._generate_reference_predictions(self.current_data)
            if current_predictions is not None:
                logger.info(f"  ✓ Prédictions courantes générées: {len(current_predictions)}")
            else:
                logger.warning("  ✗ Échec génération prédictions courantes")

        # Exécuter la détection
        logger.info("Exécution de la détection de drift...")
        self.drift_results = run_drift_detection(
            reference_data=self.reference_data,
            current_data=self.current_data,
            config=detection_config,
            reference_predictions=reference_predictions,
            current_predictions=current_predictions
        )

        if self.drift_results is None:
            logger.error("Erreur lors de la détection de drift")
            return False

        # Logger les résultats
        data_drift_detected = (self.drift_results.get('data_drift') or {}).get('drift_detected', False)
        concept_drift_detected = (self.drift_results.get('concept_drift') or {}).get('drift_detected', False)
        overall_drift_detected = self.drift_results.get('overall_drift_detected', False)

        # Avertir si la détection de concept drift n'a pas pu être effectuée
        if self.drift_results.get('concept_drift') is None:
            target_column = self.config.get('data', {}).get('target_column', 'Valeur')
            logger.warning(f"Concept drift non détecté: colonne cible '{target_column}' non trouvée dans les données")

        logger.info("=== RÉSULTATS DE DÉTECTION DE DRIFT ===")
        logger.info(f"  Data drift: {'DÉTECTÉ' if data_drift_detected else 'Non détecté'}")
        logger.info(f"  Concept drift: {'DÉTECTÉ' if concept_drift_detected else 'Non détecté'}")
        logger.info(f"  Drift global: {'DÉTECTÉ' if overall_drift_detected else 'Non détecté'}")

        if overall_drift_detected:
            logger.warning("⚠️ DRIFT DÉTECTÉ - Action requise")

        return True

    def step_5_generate_evidently_report(self, output_path: Optional[str] = None, save_to_workspace: bool = False, save_to_s3: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Étape 5: Génération du rapport Evidently.

        Args:
            output_path: Chemin pour sauvegarder le rapport HTML (optionnel)
            save_to_workspace: Sauvegarder le rapport dans le workspace Evidently UI local
            save_to_s3: Sauvegarder le rapport sur S3

        Returns:
            Tuple[bool, Optional[str]]: (succès, URL du rapport EvidentlyUI ou chemin local)
        """
        logger.info("")
        logger.info("=== ÉTAPE 5: GÉNÉRATION DU RAPPORT EVIDENTLY ===")

        if self.reference_data is None or self.current_data is None:
            logger.error("  ✗ Données de référence ou courantes manquantes")
            return False, None

        logger.info(f"Génération du rapport Evidently...")
        logger.info(f"  - Sauvegarde locale: {output_path if output_path else 'Non'}")
        logger.info(f"  - Sauvegarde workspace: {save_to_workspace}")
        logger.info(f"  - Sauvegarde S3: {save_to_s3}")

        # Générer le rapport
        report, report_dict = generate_evidently_report(
            reference_data=self.reference_data,
            current_data=self.current_data,
            output_path=output_path,
            report_name=f"drift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        if report is None:
            logger.error("  ✗ Impossible de générer le rapport Evidently")
            return False, None

        self.evidently_report = report
        logger.info("  ✓ Rapport Evidently généré avec succès")

        # Sauvegarder dans le workspace Evidently UI local si demandé
        evidently_report_url = None
        if save_to_workspace and self.evidently_config.get('save_to_workspace', False):
            logger.info("Sauvegarde dans le workspace Evidently UI...")
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

                success, evidently_report_url = save_evidently_report_to_workspace(
                    report=report,
                    reference_data=self.reference_data,
                    current_data=self.current_data,
                    project_name="energy_consumption",
                    ui_url=self.evidently_config.get('ui_url'),
                    project_id=self.evidently_config.get('project_id'),
                    workspace_path=self.evidently_config.get('workspace_path'),
                    metadata=metadata,
                    tags=tags
                )

                if success:
                    logger.info(f"  ✓ Rapport sauvegardé dans le workspace Evidently UI")
                    if evidently_report_url:
                        logger.info(f"  → URL du rapport: {evidently_report_url}")
                else:
                    logger.warning("  ✗ Échec de la sauvegarde dans le workspace Evidently UI")

            except Exception as e:
                logger.error(f"  ✗ Erreur lors de la sauvegarde dans le workspace Evidently UI: {e}")

        # Sauvegarder sur S3 si demandé
        if save_to_s3 and self.evidently_config.get('save_to_s3', False):
            logger.info("Sauvegarde sur S3...")
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
                    logger.info("  ✓ Rapport sauvegardé sur S3")
                else:
                    logger.warning("  ✗ Échec de la sauvegarde sur S3")

            except Exception as e:
                logger.error(f"  ✗ Erreur lors de la sauvegarde sur S3: {e}")

        return True, evidently_report_url

    def step_6_store_metrics(self, run_id: Optional[str] = None, evidently_report_url: Optional[str] = None) -> bool:
        """
        Étape 6: Stockage des métriques de drift.

        Args:
            run_id: ID de la run MLflow (optionnel)
            evidently_report_url: URL du rapport EvidentlyUI (optionnel)

        Returns:
            True si succès, False sinon
        """
        logger.info("")
        logger.info("=== ÉTAPE 6: STOCKAGE DES MÉTRIQUES ===")

        if self.drift_results is None:
            logger.warning("  ✗ Aucun résultat de drift à stocker")
            return False

        logger.info("Stockage des métriques de drift dans MLflow...")

        try:
            import mlflow
            from pathlib import Path
            import tempfile

            # Récupérer le run_id de la version en production via MLflow alias
            if not run_id:
                model_name = self.config.get('mlflow', {}).get('model_name')

                if model_name:
                    # Récupérer la version en production via l'alias "prod"
                    prod_model_version = get_model_version_by_alias(model_name, "prod")
                    if prod_model_version:
                        run_id = prod_model_version.run_id
                        logger.info(f"  → Utilisation du run_id de la version en production: {run_id}")
                    else:
                        logger.error("  ✗ Aucune version en production trouvée via alias 'prod'")
                        logger.error("  ✗ Impossible de stocker les métriques sans run_id")
                        return False
                else:
                    logger.error("  ✗ model_name non configuré dans la config")
                    logger.error("  ✗ Impossible de stocker les métriques sans run_id")
                    return False

            # Démarrer la run MLflow avec le run_id
            mlflow.start_run(run_id=run_id)

            # Logger les métriques de drift
            data_drift = self.drift_results.get('data_drift', {})
            concept_drift = self.drift_results.get('concept_drift', {})

            if data_drift:
                drift_detected = data_drift.get('drift_detected', False)
                mlflow.log_metric("data_drift_detected", int(drift_detected))
                logger.info(f"  ✓ Data drift: {drift_detected}")

            if concept_drift:
                drift_detected = concept_drift.get('drift_detected', False)
                mlflow.log_metric("concept_drift_detected", int(drift_detected))
                logger.info(f"  ✓ Concept drift: {drift_detected}")

            overall_drift = self.drift_results.get('overall_drift_detected', False)
            mlflow.log_metric("overall_drift_detected", int(overall_drift))
            logger.info(f"  ✓ Drift global: {overall_drift}")

            # Logger l'URL du rapport EvidentlyUI si disponible
            if evidently_report_url:
                mlflow.set_tag("evidently.drift_report_url", evidently_report_url)
                logger.info(f"  ✓ URL du rapport EvidentlyUI: {evidently_report_url}")
            else:
                # Si pas d'URL EvidentlyUI, générer et sauvegarder le rapport HTML dans MLflow
                logger.info("  → Pas d'URL EvidentlyUI, génération du rapport HTML pour MLflow...")
                if self.evidently_report is not None:
                    try:
                        # Créer un fichier temporaire pour le rapport HTML avec date dans le nom
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        report_filename = f"drift_report_{timestamp}.html"
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                            temp_path = f.name

                        # Sauvegarder le rapport HTML
                        self.evidently_report.save_html(temp_path)

                        # Logger comme artefact MLflow
                        mlflow.log_artifact(temp_path, artifact_path="evidently_reports")

                        # Nettoyer le fichier temporaire
                        Path(temp_path).unlink()

                        # Logger l'URL de l'artefact MLflow avec le nom du fichier
                        mlflow_tracking_uri = mlflow.get_tracking_uri()
                        active_run_id = mlflow.active_run().info.run_id
                        artifact_uri = f"{mlflow_tracking_uri}/artifacts/evidently_reports/{report_filename}"
                        mlflow.log_param("mlflow_artifact_url", artifact_uri)
                        mlflow.log_param("mlflow_artifact_filename", report_filename)
                        logger.info(f"  ✓ Rapport HTML sauvegardé dans MLflow artefacts")
                        logger.info(f"  → Nom du fichier: {report_filename}")
                        logger.info(f"  → URL de l'artefact: {artifact_uri}")
                        logger.info(f"  → Run ID: {active_run_id}")
                    except Exception as e:
                        logger.warning(f"  ✗ Impossible de sauvegarder le rapport HTML dans MLflow: {e}")

            mlflow.end_run()
            logger.info("  ✓ Métriques stockées avec succès")
            return True

        except Exception as e:
            logger.error(f"  ✗ Erreur lors du stockage des métriques: {e}")
            return False

    def step_7_send_notifications(self) -> bool:
        """
        Étape 7: Envoi des notifications si drift détecté.

        Returns:
            True si succès, False sinon
        """
        logger.info("")
        logger.info("=== ÉTAPE 7: ENVOI DES NOTIFICATIONS ===")

        if self.drift_results is None:
            logger.warning("  ✗ Aucun résultat de drift disponible")
            return False

        # Vérifier si le drift est détecté
        overall_drift_detected = self.drift_results.get('overall_drift_detected', False)

        if not overall_drift_detected:
            logger.info("  ✓ Aucun drift détecté, pas de notification nécessaire")
            return True

        logger.info("Drift détecté, envoi des notifications...")

        # Vérifier si les notifications sont activées
        email_config = self.config.get('email', {})
        if not email_config.get('enabled', False):
            logger.warning("  ✗ Notifications email désactivées")
            return True

        # Importer et utiliser le notifier
        try:
            from ml.utils.notifications.email_notifier import EmailNotifier

            # Récupérer les infos du modèle depuis l'API
            model_info = self._get_model_info_from_api()
            model_name = model_info.get('model_name')
            model_version = model_info.get('model_version')

            if not model_name:
                # Fallback vers la config locale
                model_name = self.config.get('mlflow', {}).get('model_name', 'unknown')

            logger.info(f"Envoi notification email - Modèle: {model_name}, Version: {model_version}")

            notifier = EmailNotifier(config=self.email_config)
            success = notifier.notify_drift_detected(
                drift_results=self.drift_results,
                model_name=model_name,
                model_version=model_version,
                run_id="monitoring_pipeline"
            )

            if success:
                logger.info("  ✓ Notification email envoyée avec succès")
            else:
                logger.warning("  ✗ Impossible d'envoyer la notification email")

            return success
        except ImportError:
            logger.warning("  ✗ EmailNotifier non disponible")
            return True
        except Exception as e:
            logger.error(f"  ✗ Erreur lors de l'envoi de la notification: {e}")
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
            # Étape 1: Health check API
            if not self.step_1_health_check_api():
                logger.warning("Health check API échoué, continuation du pipeline")
            results["steps_completed"].append("health_check_api")

            # Étape 2: Chargement données référence
            if not self.step_2_load_reference_data(reference_path, download_from_s3):
                results["error"] = "Échec du chargement des données de référence"
                return results
            results["steps_completed"].append("load_reference_data")

            # Étape 3: Chargement données courantes
            if not self.step_3_load_current_data(current_data_path, current_data_limit, start_date, end_date):
                results["error"] = "Échec du chargement des données courantes"
                return results
            results["steps_completed"].append("load_current_data")

            # Étape 4: Détection de drift
            if not self.step_4_detect_drift():
                results["error"] = "Échec de la détection de drift"
                return results
            results["steps_completed"].append("detect_drift")
            results["drift_results"] = self.drift_results

            # Étape 5: Génération rapport Evidently
            evidently_report_url = None
            if generate_report:
                success, evidently_report_url = self.step_5_generate_evidently_report(report_output_path, save_to_workspace, save_to_s3)
                if not success:
                    logger.warning("Échec de la génération du rapport Evidently")
                else:
                    results["steps_completed"].append("generate_evidently_report")
                    if evidently_report_url:
                        results["evidently_report_url"] = evidently_report_url

            # Étape 6: Stockage des métriques
            if store_metrics:
                if not self.step_6_store_metrics(mlflow_run_id, evidently_report_url):
                    logger.warning("Échec du stockage des métriques")
                else:
                    results["steps_completed"].append("store_metrics")

            # Étape 7: Notifications
            if send_notifications:
                if not self.step_7_send_notifications():
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
