"""
Connector SFTP pour récupérer des fichiers depuis un serveur SFTP avec authentification par clé PPK.
"""

from .sftp_connector import SFTPConnector
from .sftp_data_processor import SFTPDataProcessor

__all__ = ["SFTPConnector", "SFTPDataProcessor"]
