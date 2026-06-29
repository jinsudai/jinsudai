"""
Handler S3 pour le stockage et la récupération de fichiers.

Fonctionnalités:
- Upload de fichiers vers S3
- Download de fichiers depuis S3
- Vérification de l'existence de fichiers
- Gestion des erreurs et fallback local
"""
import os
import boto3
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class S3Handler:
    """Handler pour les opérations S3 avec fallback local."""

    def __init__(
        self,
        bucket: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region: Optional[str] = None,
        endpoint_url: Optional[str] = None
    ):
        """
        Initialise le handler S3.

        Args:
            bucket: Nom du bucket S3 (défaut: depuis env AWS_BUCKET)
            aws_access_key_id: Clé d'accès AWS (défaut: depuis env AWS_ACCESS_KEY_ID)
            aws_secret_access_key: Clé secrète AWS (défaut: depuis env AWS_SECRET_ACCESS_KEY)
            region: Région AWS (défaut: depuis env AWS_REGION ou AWS_DEFAULT_REGION)
            endpoint_url: URL endpoint S3 (défaut: depuis env AWS_ENDPOINT_URL)
        """
        self.bucket = bucket or os.environ.get('AWS_BUCKET', 'jinsudai-consumption')
        self.aws_access_key_id = aws_access_key_id or os.environ.get('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = aws_secret_access_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
        self.region = region or os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION', 'eu-west-3')
        self.endpoint_url = endpoint_url or os.environ.get('AWS_ENDPOINT_URL')

        # Vérifier si les credentials sont disponibles
        self.s3_enabled = all([self.aws_access_key_id, self.aws_secret_access_key])

        if self.s3_enabled:
            try:
                s3_config = {}
                if self.endpoint_url:
                    s3_config['endpoint_url'] = self.endpoint_url

                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.region,
                    **s3_config
                )
                logger.info(f"✅ S3 handler initialisé: bucket={self.bucket}, region={self.region}")
            except Exception as e:
                logger.warning(f"⚠️ Erreur initialisation S3: {e}. Mode local activé.")
                self.s3_enabled = False
        else:
            logger.info("ℹ️ Credentials S3 non disponibles. Mode local activé.")

    def upload_file(
        self,
        local_path: str,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload un fichier vers S3.

        Args:
            local_path: Chemin du fichier local
            s3_key: Clé S3 (chemin dans le bucket)
            metadata: Métadonnées optionnelles

        Returns:
            dict: Résultat de l'opération (status, bucket, key, etc.)
        """
        if not self.s3_enabled:
            return {
                "status": "skipped",
                "reason": "S3 credentials not available",
                "local_path": local_path
            }

        try:
            local_path = Path(local_path)
            if not local_path.exists():
                return {
                    "status": "error",
                    "reason": f"Local file not found: {local_path}"
                }

            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata

            self.s3_client.upload_file(
                str(local_path),
                self.bucket,
                s3_key,
                ExtraArgs=extra_args
            )

            logger.info(f"✅ Fichier uploadé: {local_path} -> s3://{self.bucket}/{s3_key}")

            return {
                "status": "success",
                "bucket": self.bucket,
                "key": s3_key,
                "local_path": str(local_path),
                "s3_uri": f"s3://{self.bucket}/{s3_key}"
            }
        except Exception as e:
            logger.error(f"❌ Erreur upload S3: {e}")
            return {
                "status": "error",
                "reason": str(e),
                "local_path": local_path
            }

    def download_file(
        self,
        s3_key: str,
        local_path: str,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Download un fichier depuis S3.

        Args:
            s3_key: Clé S3
            local_path: Chemin local de destination
            overwrite: Écraser si le fichier existe déjà

        Returns:
            dict: Résultat de l'opération
        """
        if not self.s3_enabled:
            return {
                "status": "skipped",
                "reason": "S3 credentials not available"
            }

        try:
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)

            if local_path.exists() and not overwrite:
                return {
                    "status": "skipped",
                    "reason": "Local file already exists",
                    "local_path": str(local_path)
                }

            self.s3_client.download_file(
                self.bucket,
                s3_key,
                str(local_path)
            )

            logger.info(f"✅ Fichier téléchargé: s3://{self.bucket}/{s3_key} -> {local_path}")

            return {
                "status": "success",
                "bucket": self.bucket,
                "key": s3_key,
                "local_path": str(local_path),
                "s3_uri": f"s3://{self.bucket}/{s3_key}"
            }
        except Exception as e:
            logger.error(f"❌ Erreur download S3: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }

    def file_exists(self, s3_key: str) -> bool:
        """
        Vérifie si un fichier existe sur S3.

        Args:
            s3_key: Clé S3

        Returns:
            bool: True si le fichier existe
        """
        if not self.s3_enabled:
            return False

        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except Exception:
            return False

    def list_files(self, prefix: str = "") -> list:
        """
        Liste les fichiers avec un préfixe donné.

        Args:
            prefix: Préfixe S3

        Returns:
            list: Liste des clés S3
        """
        if not self.s3_enabled:
            return []

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )

            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
        except Exception as e:
            logger.error(f"❌ Erreur liste S3: {e}")
            return []

    def copy_file(self, source_key: str, dest_key: str) -> Dict[str, Any]:
        """
        Copie un fichier S3 vers un autre emplacement.

        Args:
            source_key: Clé S3 source
            dest_key: Clé S3 destination

        Returns:
            dict: Résultat de l'opération
        """
        if not self.s3_enabled:
            return {
                "status": "skipped",
                "reason": "S3 credentials not available"
            }

        try:
            copy_source = {
                'Bucket': self.bucket,
                'Key': source_key
            }

            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket,
                Key=dest_key
            )

            logger.info(f"✅ Fichier copié: s3://{self.bucket}/{source_key} -> s3://{self.bucket}/{dest_key}")

            return {
                "status": "success",
                "bucket": self.bucket,
                "source_key": source_key,
                "dest_key": dest_key
            }
        except Exception as e:
            logger.error(f"❌ Erreur copie S3: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }

    def delete_file(self, s3_key: str) -> Dict[str, Any]:
        """
        Supprime un fichier S3.

        Args:
            s3_key: Clé S3

        Returns:
            dict: Résultat de l'opération
        """
        if not self.s3_enabled:
            return {
                "status": "skipped",
                "reason": "S3 credentials not available"
            }

        try:
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=s3_key
            )

            logger.info(f"✅ Fichier supprimé: s3://{self.bucket}/{s3_key}")

            return {
                "status": "success",
                "bucket": self.bucket,
                "key": s3_key
            }
        except Exception as e:
            logger.error(f"❌ Erreur suppression S3: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }

    def download_latest_train_file(
        self,
        local_path: Optional[str] = None,
        prefix: str = "consumption",
        prioritize_dated: bool = True
    ) -> Dict[str, Any]:
        """
        Télécharge le dernier fichier train.parquet depuis S3 avec priorité aux fichiers datés.

        Args:
            local_path: Chemin local de destination (optionnel)
                       - Si None: utilise le nom original depuis S3 dans le répertoire courant
                       - Si pointe vers un répertoire: utilise le nom original depuis S3 dans ce répertoire
                       - Si pointe vers un fichier: utilise ce chemin complet
            prefix: Préfixe S3 pour la recherche (défaut: "consumption")
            prioritize_dated: Si True, priorise les fichiers avec format YYYY-MM-DD_to_YYYY-MM-DD_train.parquet

        Returns:
            dict: Résultat de l'opération (status, local_path, s3_key, etc.)
        """
        if not self.s3_enabled:
            return {
                "status": "skipped",
                "reason": "S3 credentials not available"
            }

        try:
            logger.info(f"Recherche sur S3: bucket={self.bucket}, prefix={prefix}")

            # Lister les fichiers train.parquet
            files = self.list_files(prefix=prefix)
            train_files = [f for f in files if 'train' in f and f.endswith('.parquet')]

            if not train_files:
                logger.warning(f"Aucun fichier train.parquet trouvé dans s3://{self.bucket}/{prefix}/")
                return {
                    "status": "error",
                    "reason": f"No train files found in s3://{self.bucket}/{prefix}/"
                }

            # Prioriser les fichiers avec le format date: YYYY-MM-DD_to_YYYY-MM-DD_train.parquet
            if prioritize_dated:
                dated_files = [f for f in train_files if '_to_' in f and '_train.parquet' in f]
                if dated_files:
                    train_files = dated_files
                    logger.info(f"Fichiers datés trouvés: {len(dated_files)}")

            # Trouver le plus récent (tri alphabétique inverse)
            train_files_sorted = sorted(train_files, reverse=True)
            latest_file = train_files_sorted[0]

            logger.info(f"Fichier le plus récent sur S3: {latest_file}")

            # Construire le chemin local
            if local_path is None:
                # Utiliser le nom original dans le répertoire courant
                filename = Path(latest_file).name
                local_path = str(Path.cwd() / filename)
            else:
                local_path_obj = Path(local_path)
                # Créer le répertoire parent s'il n'existe pas
                local_path_obj.mkdir(parents=True, exist_ok=True)
                # Vérifier si c'est un répertoire (existant ou terminé par / ou \)
                if local_path_obj.is_dir() or local_path.endswith('/') or local_path.endswith('\\'):
                    # Si c'est un répertoire, utiliser le nom original dans ce répertoire
                    filename = Path(latest_file).name
                    local_path = str(local_path_obj / filename)
                # Sinon, utiliser le chemin complet tel quel

            # Télécharger le fichier
            result = self.download_file(
                s3_key=latest_file,
                local_path=local_path,
                overwrite=True
            )

            return result

        except Exception as e:
            logger.error(f"Erreur lors du téléchargement depuis S3: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }

    def get_latest_prepared_end_date(self, prefix: str = "consumption/prepared") -> Optional[str]:
        """
        Récupère la date de fin du dernier fichier préparé depuis S3.

        Les fichiers sont nommés selon le format: YYYY-MM-DD_to_YYYY-MM-DD_train.parquet
        Cette méthode extrait la date de fin (après "_to_") du fichier le plus récent.

        Args:
            prefix: Préfixe S3 pour la recherche (défaut: "consumption/prepared")

        Returns:
            str: Date de fin au format YYYY-MM-DD, ou None si aucun fichier trouvé
        """
        if not self.s3_enabled:
            logger.warning("S3 non disponible, impossible de récupérer la date de fin")
            return None

        try:
            logger.info(f"Recherche du dernier fichier préparé dans s3://{self.bucket}/{prefix}/")

            # Lister les fichiers train.parquet
            files = self.list_files(prefix=prefix)
            train_files = [f for f in files if 'train' in f and f.endswith('.parquet')]

            if not train_files:
                logger.warning(f"Aucun fichier train.parquet trouvé dans s3://{self.bucket}/{prefix}/")
                return None

            # Filtrer les fichiers avec le format date: YYYY-MM-DD_to_YYYY-MM-DD_train.parquet
            dated_files = [f for f in train_files if '_to_' in f and '_train.parquet' in f]

            if not dated_files:
                logger.warning(f"Aucun fichier avec format de date trouvé dans s3://{self.bucket}/{prefix}/")
                return None

            # Trouver le plus récent (tri alphabétique inverse)
            dated_files_sorted = sorted(dated_files, reverse=True)
            latest_file = dated_files_sorted[0]

            logger.info(f"Fichier le plus récent: {latest_file}")

            # Extraire la date de fin du nom de fichier
            # Format: YYYY-MM-DD_to_YYYY-MM-DD_train.parquet
            filename = Path(latest_file).name
            match = re.match(r'\d{4}-\d{2}-\d{2}_to_(\d{4}-\d{2}-\d{2})_train\.parquet', filename)

            if match:
                end_date = match.group(1)
                logger.info(f"Date de fin extraite: {end_date}")
                return end_date
            else:
                logger.warning(f"Impossible d'extraire la date de fin du fichier: {filename}")
                return None

        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la date de fin: {e}")
            return None
