"""
Connector SFTP pour récupérer des fichiers depuis un serveur SFTP avec authentification par clé SSH et passphrase.

Ce module permet de se connecter à un serveur SFTP en utilisant une clé privée au format OpenSSH
protégée par une passphrase, et de récupérer des fichiers depuis un répertoire spécifié.

Exemple d'utilisation :
    from ml.connectors.sftp.sftp_connector import SFTPConnector
    
    connector = SFTPConnector(
        host="sftp.example.com",
        port=22,
        username="user",
        ssh_private_key_b64="<BASE64_ENCODED_OPENSSH_KEY>",
        passphrase="your_passphrase"
    )
    
    # Lister les fichiers
    files = connector.list_files("/remote/directory")
    
    # Télécharger un fichier
    connector.download_file("/remote/directory/file.csv", "/local/path/file.csv")
    
    # Télécharger tous les fichiers d'un répertoire
    connector.download_directory("/remote/directory", "/local/path")
"""

import base64
import paramiko
import stat
from pathlib import Path
from typing import List, Optional, Union
import logging
from io import StringIO, BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SFTPConnector:
    """
    Classe pour se connecter à un serveur SFTP avec authentification par clé SSH et passphrase.
    """

    def __init__(
        self,
        host: str,
        username: str,
        ssh_private_key_b64: Optional[str] = None,
        ssh_private_key_content: Optional[str] = None,
        passphrase: Optional[str] = None,
        port: int = 22,
        timeout: int = 30
    ):
        """
        Initialise le connecteur SFTP.

        Args:
            host: Adresse du serveur SFTP
            username: Nom d'utilisateur
            ssh_private_key_b64: Clé privée SSH encodée en base64 depuis le secret
            ssh_private_key_content: Contenu de la clé privée SSH (format OpenSSH) depuis secret
            passphrase: Passphrase pour déverrouiller la clé (optionnel)
            port: Port SFTP (défaut: 22)
            timeout: Timeout de connexion en secondes (défaut: 30)
        """
        self.host = host
        self.username = username
        self.ssh_private_key_content = self._decode_ssh_private_key(
            ssh_private_key_b64=ssh_private_key_b64,
            ssh_private_key_content=ssh_private_key_content
        )
        self.passphrase = passphrase
        self.port = port
        self.timeout = timeout
        self.ssh_client = None
        self.sftp_client = None

        source = "ssh_private_key_b64" if ssh_private_key_b64 else "ssh_private_key_content"
        logger.info(f"Clé SSH chargée depuis {source}")

    def _decode_ssh_private_key(
        self,
        ssh_private_key_b64: Optional[str],
        ssh_private_key_content: Optional[str]
    ) -> Optional[str]:
        if ssh_private_key_b64:
            key_b64 = ssh_private_key_b64.strip()
            if not key_b64:
                return ssh_private_key_content

            try:
                decoded = base64.b64decode(key_b64, validate=True)
            except Exception:
                cleaned = "".join(key_b64.split())
                decoded = base64.b64decode(cleaned)

            try:
                return decoded.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ValueError("La clé privée SSH encodée en base64 ne contient pas un texte UTF-8 valide") from e

        return ssh_private_key_content

    def connect(self) -> None:
        """
        Établit la connexion SFTP avec authentification par clé SSH.
        """
        try:
            # Créer le client SSH
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Charger la clé privée SSH directement depuis la chaîne de caractères
            key_content = self.ssh_private_key_content
            if key_content is None:
                raise ValueError("ssh_private_key_content est requis")

            # Décode les séquences d'échappement si la clé est fournie avec des \n littéraux
            if '\\n' in key_content or '\\r' in key_content:
                try:
                    key_content = key_content.encode('utf-8').decode('unicode_escape')
                except Exception:
                    pass

            key_content = key_content.replace('\r\n', '\n').replace('\r', '\n')
            key_content = key_content.strip()

            # Supprime l'encapsulation éventuelle avec des guillemets
            if key_content.startswith('"') and key_content.endswith('"'):
                key_content = key_content[1:-1].strip()
            if key_content.startswith("'") and key_content.endswith("'"):
                key_content = key_content[1:-1].strip()

            # Normalisation des lignes pour éviter les espaces ou indentations indésirables
            lines = [line.strip() for line in key_content.splitlines() if line.strip()]
            key_content = '\n'.join(lines) + '\n'

            private_key = None

            password = self.passphrase
            if isinstance(password, bytes):
                try:
                    password = password.decode('utf-8')
                except Exception:
                    pass

            try:
                with StringIO(key_content) as key_file:
                    private_key = paramiko.PKey.from_private_key(key_file, password=password)
                logger.info("Clé chargée avec succès via PKey.from_private_key")
            except Exception as e:
                logger.info(f"Échec via PKey.from_private_key: {e}")
                private_key = None

            if private_key is None:
                temp_path = None
                try:
                    import tempfile
                    import os
                    with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as temp_file:
                        temp_file.write(key_content.encode('utf-8'))
                        temp_file.flush()
                        temp_path = temp_file.name

                    key_types = [
                        ('RSA', paramiko.RSAKey),
                        ('ECDSA', paramiko.ECDSAKey),
                        ('Ed25519', getattr(paramiko, 'Ed25519Key', None)),
                        ('DSS', getattr(paramiko, 'DSSKey', None))
                    ]
                    for key_name, key_cls in key_types:
                        if key_cls is None:
                            continue
                        try:
                            private_key = key_cls.from_private_key_file(temp_path, password=password)
                            logger.info(f"Clé chargée avec succès via {key_name}Key.from_private_key_file")
                            break
                        except Exception as e:
                            logger.info(f"Échec via {key_name}Key.from_private_key_file: {e}")
                finally:
                    if temp_path:
                        try:
                            os.unlink(temp_path)
                        except Exception:
                            pass

            if private_key is None:
                logger.error(f"Contenu de la clé (premiers 100 caractères): {key_content[:100]}")
                raise ValueError("Impossible de charger la clé SSH avec aucun des formats supportés (RSA, ECDSA, Ed25519, DSS)")

            # Se connecter
            self.ssh_client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                pkey=private_key,
                timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False
            )

            # Ouvrir le client SFTP
            self.sftp_client = self.ssh_client.open_sftp()

            logger.info(f"Connexion SFTP réussie à {self.host}:{self.port} pour l'utilisateur {self.username}")

        except paramiko.AuthenticationException as e:
            logger.error(f"Erreur d'authentification SFTP: {e}")
            raise
        except paramiko.SSHException as e:
            logger.error(f"Erreur SSH: {e}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la connexion SFTP: {e}")
            raise

    def disconnect(self) -> None:
        """
        Ferme la connexion SFTP.
        """
        if self.sftp_client:
            self.sftp_client.close()
            self.sftp_client = None

        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None

        logger.info("Connexion SFTP fermée")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def _ensure_connected(self) -> None:
        """Vérifie que la connexion est établie."""
        if self.sftp_client is None:
            self.connect()

    def list_files(
        self,
        remote_path: str,
        pattern: Optional[str] = None,
        recursive: bool = False
    ) -> List[dict]:
        """
        Liste les fichiers dans un répertoire distant.

        Args:
            remote_path: Chemin du répertoire distant
            pattern: Filtre de nom de fichier (ex: "*.csv")
            recursive: Si True, liste les fichiers de manière récursive

        Returns:
            Liste de dictionnaires avec les informations sur les fichiers:
            - filename: nom du fichier
            - path: chemin complet
            - size: taille en octets
            - is_directory: booléen
        """
        self._ensure_connected()

        files = []

        def _list_directory(path: str):
            try:
                for item in self.sftp_client.listdir_attr(path):
                    item_path = f"{path}/{item.filename}" if path != "/" else f"/{item.filename}"

                    if stat.S_ISDIR(item.st_mode):
                        if recursive:
                            _list_directory(item_path)
                        if pattern is None:
                            files.append({
                                "filename": item.filename,
                                "path": item_path,
                                "size": item.st_size,
                                "is_directory": True
                            })
                    else:
                        if pattern is None or Path(item.filename).match(pattern):
                            files.append({
                                "filename": item.filename,
                                "path": item_path,
                                "size": item.st_size,
                                "is_directory": False
                            })
            except IOError as e:
                logger.error(f"Erreur lors de l'accès à {path}: {e}")
                raise

        _list_directory(remote_path)

        logger.info(f"{len(files)} fichiers trouvés dans {remote_path}")
        return files

    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path],
        overwrite: bool = False
    ) -> Path:
        """
        Télécharge un fichier depuis le serveur SFTP.

        Args:
            remote_path: Chemin du fichier distant
            local_path: Chemin local de destination
            overwrite: Si False, ne télécharge pas si le fichier existe déjà

        Returns:
            Chemin du fichier téléchargé
        """
        self._ensure_connected()

        local_path = Path(local_path)

        if local_path.exists() and not overwrite:
            logger.info(f"Le fichier existe déjà: {local_path}")
            return local_path

        # Créer le répertoire local si nécessaire
        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.sftp_client.get(remote_path, str(local_path))
            logger.info(f"Fichier téléchargé: {remote_path} -> {local_path}")
            return local_path
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement de {remote_path}: {e}")
            raise

    def download_file_to_memory(
        self,
        remote_path: str
    ) -> BytesIO:
        """
        Télécharge un fichier en mémoire.

        Args:
            remote_path: Chemin du fichier distant

        Returns:
            BytesIO contenant le contenu du fichier
        """
        self._ensure_connected()

        try:
            with self.sftp_client.file(remote_path, 'rb') as remote_file:
                content = remote_file.read()

            logger.info(f"Fichier téléchargé en mémoire: {remote_path}")
            return BytesIO(content)
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement en mémoire de {remote_path}: {e}")
            raise

    def download_directory(
        self,
        remote_path: str,
        local_path: Union[str, Path],
        pattern: Optional[str] = None,
        overwrite: bool = False,
        preserve_structure: bool = True
    ) -> List[Path]:
        """
        Télécharge tous les fichiers d'un répertoire distant.

        Args:
            remote_path: Chemin du répertoire distant
            local_path: Chemin local de destination
            pattern: Filtre de nom de fichier (ex: "*.csv")
            overwrite: Si False, ne télécharge pas les fichiers existants
            preserve_structure: Si True, préserve la structure des répertoires

        Returns:
            Liste des chemins des fichiers téléchargés
        """
        self._ensure_connected()

        local_path = Path(local_path)
        local_path.mkdir(parents=True, exist_ok=True)

        files = self.list_files(remote_path, pattern=pattern, recursive=True)
        downloaded_files = []

        for file_info in files:
            if file_info["is_directory"]:
                continue

            if preserve_structure:
                # Conserver la structure des répertoires
                relative_path = Path(file_info["path"]).relative_to(remote_path)
                target_path = local_path / relative_path
            else:
                # Tout télécharger dans le même répertoire
                target_path = local_path / file_info["filename"]

            try:
                downloaded = self.download_file(
                    file_info["path"],
                    target_path,
                    overwrite=overwrite
                )
                downloaded_files.append(downloaded)
            except Exception as e:
                logger.error(f"Erreur lors du téléchargement de {file_info['path']}: {e}")
                continue

        logger.info(f"{len(downloaded_files)} fichiers téléchargés dans {local_path}")
        return downloaded_files

    def file_exists(self, remote_path: str) -> bool:
        """
        Vérifie si un fichier existe sur le serveur SFTP.

        Args:
            remote_path: Chemin du fichier distant

        Returns:
            True si le fichier existe, False sinon
        """
        self._ensure_connected()

        try:
            self.sftp_client.stat(remote_path)
            return True
        except IOError:
            return False

    def get_file_info(self, remote_path: str) -> dict:
        """
        Récupère les informations sur un fichier distant.

        Args:
            remote_path: Chemin du fichier distant

        Returns:
            Dictionnaire avec les informations du fichier:
            - size: taille en octets
            - modified: date de dernière modification
            - is_directory: booléen
        """
        self._ensure_connected()

        try:
            stat = self.sftp_client.stat(remote_path)
            return {
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "is_directory": stat.S_ISDIR(stat.st_mode)
            }
        except IOError as e:
            logger.error(f"Erreur lors de la récupération des infos de {remote_path}: {e}")
            raise

    def move_file(self, source_path: str, destination_path: str) -> bool:
        """
        Déplace un fichier sur le serveur SFTP.

        Args:
            source_path: Chemin source du fichier
            destination_path: Chemin de destination

        Returns:
            True si succès, False sinon
        """
        self._ensure_connected()

        try:
            # Créer le répertoire de destination si nécessaire
            dest_dir = str(Path(destination_path).parent)
            try:
                self.sftp_client.mkdir(dest_dir)
            except IOError:
                # Le répertoire existe peut-être déjà
                pass

            # Renommer/déplacer le fichier
            self.sftp_client.rename(source_path, destination_path)
            logger.info(f"Fichier déplacé: {source_path} -> {destination_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors du déplacement de {source_path} vers {destination_path}: {e}")
            return False

    def archive_file(self, source_path: str, archive_dir: str = "/archived") -> bool:
        """
        Archive un fichier en le déplaçant vers un répertoire d'archive.

        Args:
            source_path: Chemin du fichier à archiver
            archive_dir: Répertoire d'archive (défaut: /archived)

        Returns:
            True si succès, False sinon
        """
        filename = Path(source_path).name
        destination_path = f"{archive_dir}/{filename}"
        return self.move_file(source_path, destination_path)

    def upload_file(self, local_path: Union[str, Path], remote_path: str) -> bool:
        """
        Upload un fichier vers le serveur SFTP.

        Args:
            local_path: Chemin local du fichier
            remote_path: Chemin distant de destination

        Returns:
            True si succès, False sinon
        """
        self._ensure_connected()

        local_path = Path(local_path)

        if not local_path.exists():
            logger.error(f"Fichier local introuvable: {local_path}")
            return False

        try:
            # Créer le répertoire distant si nécessaire
            remote_dir = str(Path(remote_path).parent)
            try:
                self.sftp_client.mkdir(remote_dir)
            except IOError:
                # Le répertoire existe peut-être déjà
                pass

            self.sftp_client.put(str(local_path), remote_path)
            logger.info(f"Fichier uploadé: {local_path} -> {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'upload de {local_path} vers {remote_path}: {e}")
            return False
