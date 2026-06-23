"""
Processeur de données SFTP pour récupérer les valeurs réelles et mettre à jour la base de données.

Ce module intègre le connector SFTP avec le DatabaseHandler pour:
1. Télécharger des fichiers depuis un serveur SFTP
2. Extraire les valeurs réelles de consommation
3. Mettre à jour la base de données avec ces valeurs
4. Archiver les fichiers traités sur le serveur SFTP

Exemple d'utilisation :
    from ml.connectors.sftp.sftp_data_processor import SFTPDataProcessor
    from ml.pipelines.database_handler import DatabaseHandler

    processor = SFTPDataProcessor(
        sftp_host="sftp.example.com",
        sftp_username="user",
        ppk_key_path="/path/to/key.ppk",
        passphrase="passphrase",
        db_uri="postgresql://user:pass@host/db"
    )

    # Traiter tous les fichiers CSV
    results = processor.process_directory(
        remote_directory="/data/incoming",
        archive_directory="/data/archived",
        file_pattern="*.csv"
    )
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Union
import logging
from datetime import datetime

from .sftp_connector import SFTPConnector
from ml.pipelines.database_handler import DatabaseHandler
from ml.utils.notifications.email_notifier import EmailNotifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SFTPDataProcessor:
    """
    Classe pour traiter les données SFTP et mettre à jour la base de données avec les valeurs réelles.
    """

    def __init__(
        self,
        sftp_host: str,
        sftp_username: str,
        ssh_private_key_b64: Optional[str] = None,
        ssh_private_key_content: Optional[str] = None,
        db_uri: str = None,
        passphrase: Optional[str] = None,
        sftp_port: int = 22,
        sftp_timeout: int = 30,
        email_notifier: Optional[EmailNotifier] = None
    ):
        """
        Initialise le processeur de données SFTP.

        Args:
            sftp_host: Adresse du serveur SFTP
            sftp_username: Nom d'utilisateur SFTP
            ssh_private_key_b64: Clé privée SSH encodée en base64 depuis le secret
            ssh_private_key_content: Contenu de la clé SSH (format OpenSSH) depuis secret
            db_uri: URI de connexion PostgreSQL
            passphrase: Passphrase pour la clé SSH (optionnel)
            sftp_port: Port SFTP (défaut: 22)
            sftp_timeout: Timeout SFTP en secondes (défaut: 30)
            email_notifier: Notificateur email (optionnel)
        """
        self.sftp_connector = SFTPConnector(
            host=sftp_host,
            username=sftp_username,
            ssh_private_key_b64=ssh_private_key_b64,
            ssh_private_key_content=ssh_private_key_content,
            passphrase=passphrase,
            port=sftp_port,
            timeout=sftp_timeout
        )
        self.db_handler = DatabaseHandler(db_uri)
        self.email_notifier = email_notifier

        logger.info("Processeur de données SFTP initialisé")

    def setup(self) -> bool:
        """
        Configure le processeur (connexion SFTP + base de données).

        Returns:
            True si succès, False sinon
        """
        try:
            # Vérifier la connexion SFTP
            with self.sftp_connector:
                logger.info("Connexion SFTP vérifiée")

            # Vérifier la connexion base de données
            if not self.db_handler.verify_connection():
                logger.error("Impossible de se connecter à la base de données")
                return False

            # Créer les tables si nécessaire
            if not self.db_handler.create_tables():
                logger.error("Impossible de créer les tables")
                return False

            # Ajouter la colonne actual_value si nécessaire
            if not self.db_handler.add_actual_value_column():
                logger.error("Impossible d'ajouter la colonne actual_value")
                return False

            logger.info("Configuration terminée avec succès")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de la configuration: {e}")
            return False

    def parse_actual_values_file(self, file_path: Union[str, Path]) -> pd.DataFrame:
        """
        Parse un fichier contenant les valeurs réelles.

        Le fichier doit contenir au minimum:
        - Horodate: timestamp de la mesure
        - Valeur: valeur réelle de consommation

        Args:
            file_path: Chemin vers le fichier (local ou distant)

        Returns:
            DataFrame avec Horodate et Valeur
        """
        try:
            # Essayer de lire comme CSV
            df = pd.read_csv(
                file_path,
                sep=";",
                parse_dates=["Horodate"],
                dayfirst=True,
                encoding="utf-8"
            )

            # Vérifier les colonnes requises
            required_columns = ["Horodate", "Valeur"]
            missing = [col for col in required_columns if col not in df.columns]

            if missing:
                logger.error(f"Colonnes manquantes dans {file_path}: {missing}")
                return None

            # Nettoyer les données
            df = df[["Horodate", "Valeur"]].copy()
            df["Valeur"] = pd.to_numeric(df["Valeur"], errors="coerce")
            df = df.dropna(subset=["Valeur"])

            logger.info(f"Fichier parsé: {file_path} ({len(df)} enregistrements)")
            return df

        except Exception as e:
            logger.error(f"Erreur lors du parsing de {file_path}: {e}")
            return None

    def match_predictions_with_actuals(
        self,
        actual_df: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, List]:
        """
        Fait correspondre les valeurs réelles avec les prédictions dans la base de données.

        Args:
            actual_df: DataFrame avec Horodate et Valeur
            start_date: Date de début pour la recherche de prédictions (optionnel)
            end_date: Date de fin pour la recherche de prédictions (optionnel)

        Returns:
            Dictionnaire avec prediction_ids et actual_values
        """
        if actual_df is None or actual_df.empty:
            logger.warning("Aucune donnée réelle à matcher")
            return {"prediction_ids": [], "actual_values": []}

        # Déterminer la plage de dates
        if start_date is None:
            start_date = actual_df["Horodate"].min()
        if end_date is None:
            end_date = actual_df["Horodate"].max()

        # Récupérer les prédictions pour cette plage
        predictions_df = self.db_handler.get_predictions_by_date(start_date, end_date)

        if predictions_df is None or predictions_df.empty:
            logger.warning(f"Aucune prédiction trouvée entre {start_date} et {end_date}")
            return {"prediction_ids": [], "actual_values": []}

        # Faire correspondre les horodates (arrondir à 30 minutes)
        actual_df["target_timestamp"] = actual_df["Horodate"].dt.floor("30min")
        predictions_df["target_timestamp"] = pd.to_datetime(predictions_df["target_timestamp"])

        # Fusionner sur target_timestamp
        merged = pd.merge(
            predictions_df,
            actual_df[["target_timestamp", "Valeur"]],
            on="target_timestamp",
            how="inner"
        )

        if merged.empty:
            logger.warning("Aucune correspondance trouvée entre prédictions et valeurs réelles")
            return {"prediction_ids": [], "actual_values": []}

        logger.info(f"{len(merged)} correspondances trouvées")

        return {
            "prediction_ids": merged["prediction_id"].tolist(),
            "actual_values": merged["Valeur"].tolist()
        }

    def process_file(
        self,
        remote_file_path: str,
        archive_directory: str = "/archived",
        temp_local_dir: str = "/tmp/sftp_temp"
    ) -> Dict[str, any]:
        """
        Traite un fichier individuel depuis SFTP.

        Args:
            remote_file_path: Chemin du fichier distant
            archive_directory: Répertoire d'archive sur SFTP
            temp_local_dir: Répertoire temporaire local

        Returns:
            Dictionnaire avec le résultat du traitement
        """
        result = {
            "file": remote_file_path,
            "success": False,
            "records_processed": 0,
            "predictions_updated": 0,
            "archived": False,
            "error": None
        }

        temp_local_dir = Path(temp_local_dir)
        temp_local_dir.mkdir(parents=True, exist_ok=True)

        local_temp_path = temp_local_dir / Path(remote_file_path).name

        try:
            # 1. Notifier la réception du fichier
            if self.email_notifier:
                file_info = None
                with self.sftp_connector:
                    try:
                        file_info = self.sftp_connector.get_file_info(remote_file_path)
                    except BaseException:
                        pass

                if file_info:
                    self.email_notifier.notify_file_received(
                        filename=Path(remote_file_path).name,
                        file_size=file_info["size"],
                        remote_path=remote_file_path
                    )

            # 2. Télécharger le fichier
            with self.sftp_connector:
                self.sftp_connector.download_file(
                    remote_file_path,
                    local_temp_path,
                    overwrite=True
                )

            # 3. Parser le fichier
            actual_df = self.parse_actual_values_file(local_temp_path)

            if actual_df is None or actual_df.empty:
                result["error"] = "Impossible de parser le fichier ou fichier vide"
                # Notifier l'échec
                if self.email_notifier:
                    self.email_notifier.notify_file_processed(
                        filename=Path(remote_file_path).name,
                        records_processed=0,
                        predictions_updated=0,
                        success=False,
                        error_message=result["error"]
                    )
                return result

            result["records_processed"] = len(actual_df)

            # 4. Matcher avec les prédictions
            match_result = self.match_predictions_with_actuals(actual_df)

            if not match_result["prediction_ids"]:
                result["error"] = "Aucune correspondance trouvée avec les prédictions"
                # Notifier l'échec
                if self.email_notifier:
                    self.email_notifier.notify_file_processed(
                        filename=Path(remote_file_path).name,
                        records_processed=result["records_processed"],
                        predictions_updated=0,
                        success=False,
                        error_message=result["error"]
                    )
                return result

            # 5. Mettre à jour la base de données
            update_success = self.db_handler.update_actual_values(
                match_result["prediction_ids"],
                match_result["actual_values"]
            )

            if not update_success:
                result["error"] = "Erreur lors de la mise à jour de la base de données"
                # Notifier l'échec
                if self.email_notifier:
                    self.email_notifier.notify_file_processed(
                        filename=Path(remote_file_path).name,
                        records_processed=result["records_processed"],
                        predictions_updated=0,
                        success=False,
                        error_message=result["error"]
                    )
                return result

            result["predictions_updated"] = len(match_result["prediction_ids"])

            # 6. Archiver le fichier sur SFTP
            with self.sftp_connector:
                archive_success = self.sftp_connector.archive_file(
                    remote_file_path,
                    archive_directory
                )

            result["archived"] = archive_success
            result["success"] = True

            # Notifier le succès
            if self.email_notifier:
                self.email_notifier.notify_file_processed(
                    filename=Path(remote_file_path).name,
                    records_processed=result["records_processed"],
                    predictions_updated=result["predictions_updated"],
                    success=True
                )

            logger.info(f"Fichier traité avec succès: {remote_file_path}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Erreur lors du traitement de {remote_file_path}: {e}")
            # Notifier l'erreur
            if self.email_notifier:
                self.email_notifier.notify_file_processed(
                    filename=Path(remote_file_path).name,
                    records_processed=result.get("records_processed", 0),
                    predictions_updated=result.get("predictions_updated", 0),
                    success=False,
                    error_message=str(e)
                )

        finally:
            # Nettoyer le fichier temporaire
            if local_temp_path.exists():
                local_temp_path.unlink()

        return result

    def process_directory(
        self,
        remote_directory: str,
        archive_directory: str = "/archived",
        file_pattern: str = "*.csv",
        temp_local_dir: str = "/tmp/sftp_temp"
    ) -> List[Dict[str, any]]:
        """
        Traite tous les fichiers d'un répertoire SFTP.

        Args:
            remote_directory: Répertoire distant
            archive_directory: Répertoire d'archive sur SFTP
            file_pattern: Pattern de fichiers à traiter (ex: "*.csv")
            temp_local_dir: Répertoire temporaire local

        Returns:
            Liste des résultats de traitement pour chaque fichier
        """
        results = []

        try:
            # Lister les fichiers
            with self.sftp_connector:
                files = self.sftp_connector.list_files(
                    remote_directory,
                    pattern=file_pattern,
                    recursive=False
                )

            if not files:
                logger.info(f"Aucun fichier trouvé dans {remote_directory}")
                return results

            logger.info(f"{len(files)} fichiers à traiter dans {remote_directory}")

            # Traiter chaque fichier
            for file_info in files:
                if file_info["is_directory"]:
                    continue

                result = self.process_file(
                    file_info["path"],
                    archive_directory,
                    temp_local_dir
                )
                results.append(result)

            # Résumé
            successful = sum(1 for r in results if r["success"])
            failed = len(results) - successful
            total_updated = sum(r["predictions_updated"] for r in results)
            total_records = sum(r["records_processed"] for r in results)

            logger.info(f"Traitement terminé: {successful}/{len(results)} fichiers réussis, {total_updated} prédictions mises à jour")

            # Notifier la complétion du traitement par lots
            if self.email_notifier:
                self.email_notifier.notify_batch_completed(
                    total_files=len(results),
                    successful=successful,
                    failed=failed,
                    total_records=total_records,
                    total_updated=total_updated
                )

        except Exception as e:
            logger.error(f"Erreur lors du traitement du répertoire {remote_directory}: {e}")

        return results

    def get_processing_summary(self, results: List[Dict[str, any]]) -> Dict[str, any]:
        """
        Génère un résumé des résultats de traitement.

        Args:
            results: Liste des résultats de traitement

        Returns:
            Dictionnaire avec le résumé
        """
        total_files = len(results)
        successful = sum(1 for r in results if r["success"])
        failed = total_files - successful
        total_records = sum(r["records_processed"] for r in results)
        total_updated = sum(r["predictions_updated"] for r in results)
        archived = sum(1 for r in results if r["archived"])

        return {
            "total_files": total_files,
            "successful": successful,
            "failed": failed,
            "total_records_processed": total_records,
            "total_predictions_updated": total_updated,
            "files_archived": archived,
            "success_rate": successful / total_files if total_files > 0 else 0
        }
