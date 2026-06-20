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
            bucket: Nom du bucket S3 (défaut: depuis env AWS_S3_CONSUMPTION_BUCKET)
            aws_access_key_id: Clé d'accès AWS (défaut: depuis env AWS_ACCESS_KEY_ID)
            aws_secret_access_key: Clé secrète AWS (défaut: depuis env AWS_SECRET_ACCESS_KEY)
            region: Région AWS (défaut: depuis env AWS_REGION ou AWS_DEFAULT_REGION)
            endpoint_url: URL endpoint S3 (défaut: depuis env AWS_ENDPOINT_URL)
        """
        self.bucket = bucket or os.environ.get('AWS_S3_CONSUMPTION_BUCKET', 'jinsudai-consumption')
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
