# SFTP Connector

Connector SFTP pour récupérer des fichiers depuis un serveur SFTP avec authentification par clé PPK et passphrase.

## Fonctionnalités

- Connexion SFTP sécurisée avec authentification par clé PPK (PuTTY Private Key)
- Support de passphrase pour les clés protégées
- Liste des fichiers dans un répertoire distant
- Téléchargement de fichiers individuels
- Téléchargement de répertoires complets
- Filtre par pattern de nom de fichier
- Support du téléchargement récursif
- Téléchargement en mémoire pour les fichiers volumineux
- Vérification d'existence de fichiers
- Récupération des métadonnées de fichiers

## Installation

Le connector utilise la bibliothèque `paramiko` qui est déjà incluse dans les dépendances du projet.

## Configuration

Avant d'utiliser le connector, assurez-vous d'avoir:
- Un fichier de clé privée PPK (format PuTTY)
- La passphrase associée si la clé est protégée
- Les informations de connexion au serveur SFTP (hôte, port, utilisateur)

## Utilisation

### Import

```python
from ml.connectors.sftp.sftp_connector import SFTPConnector
```

### Initialisation

```python
connector = SFTPConnector(
    host="sftp.example.com",
    port=22,
    username="votre_utilisateur",
    ppk_key_path="/chemin/vers/cle.ppk",
    passphrase="votre_passphrase"  # Optionnel si la clé n'est pas protégée
)
```

### Utilisation avec context manager (recommandé)

```python
with SFTPConnector(
    host="sftp.example.com",
    username="user",
    ppk_key_path="/path/to/key.ppk",
    passphrase="passphrase"
) as connector:
    # Les opérations sont ici
    files = connector.list_files("/remote/directory")
```

### Lister les fichiers

```python
# Lister tous les fichiers
files = connector.list_files("/remote/directory")

# Lister avec filtre pattern
csv_files = connector.list_files("/remote/directory", pattern="*.csv")

# Lister de manière récursive
all_files = connector.list_files("/remote/directory", recursive=True)
```

### Télécharger un fichier

```python
# Télécharger un fichier spécifique
local_file = connector.download_file(
    remote_path="/remote/directory/data.csv",
    local_path="/local/path/data.csv"
)

# Télécharger sans écraser si le fichier existe déjà
local_file = connector.download_file(
    remote_path="/remote/directory/data.csv",
    local_path="/local/path/data.csv",
    overwrite=False
)
```

### Télécharger un fichier en mémoire

```python
# Utile pour les fichiers volumineux ou pour éviter les I/O disque
content = connector.download_file_to_memory("/remote/directory/data.csv")
data = content.read()
```

### Télécharger un répertoire complet

```python
# Télécharger tous les fichiers d'un répertoire
downloaded_files = connector.download_directory(
    remote_path="/remote/directory",
    local_path="/local/path"
)

# Télécharger avec filtre pattern
csv_files = connector.download_directory(
    remote_path="/remote/directory",
    local_path="/local/path",
    pattern="*.csv"
)

# Télécharger sans préserver la structure des répertoires
flat_files = connector.download_directory(
    remote_path="/remote/directory",
    local_path="/local/path",
    preserve_structure=False
)
```

### Vérifier l'existence d'un fichier

```python
exists = connector.file_exists("/remote/directory/data.csv")
```

### Récupérer les informations d'un fichier

```python
info = connector.get_file_info("/remote/directory/data.csv")
print(f"Taille: {info['size']} octets")
print(f"Modifié: {info['modified']}")
print(f"Répertoire: {info['is_directory']}")
```

## Exemple complet

```python
from ml.connectors.sftp.sftp_connector import SFTPConnector
from pathlib import Path

# Configuration
SFTP_HOST = "sftp.example.com"
SFTP_PORT = 22
SFTP_USER = "data_user"
PPK_KEY_PATH = "/home/user/.ssh/sftp_key.ppk"
PASSPHRASE = "your_secure_passphrase"

# Répertoires
REMOTE_DIR = "/data/exports"
LOCAL_DIR = "/data/imports"

# Télécharger tous les fichiers CSV
with SFTPConnector(
    host=SFTP_HOST,
    port=SFTP_PORT,
    username=SFTP_USER,
    ppk_key_path=PPK_KEY_PATH,
    passphrase=PASSPHRASE
) as connector:
    
    # Lister les fichiers disponibles
    files = connector.list_files(REMOTE_DIR, pattern="*.csv")
    print(f"Fichiers trouvés: {len(files)}")
    
    for file_info in files:
        print(f"- {file_info['filename']} ({file_info['size']} octets)")
    
    # Télécharger tous les fichiers CSV
    downloaded = connector.download_directory(
        remote_path=REMOTE_DIR,
        local_path=LOCAL_DIR,
        pattern="*.csv",
        overwrite=True
    )
    
    print(f"Fichiers téléchargés: {len(downloaded)}")
```

## Gestion des erreurs

Le connector lève des exceptions en cas d'erreur:
- `FileNotFoundError`: Si le fichier de clé PPK n'existe pas
- `paramiko.AuthenticationException`: En cas d'échec d'authentification
- `paramiko.SSHException`: En cas d'erreur SSH
- `IOError`: En cas d'erreur d'accès aux fichiers distants

Il est recommandé d'utiliser des blocs try/except pour gérer ces erreurs:

```python
try:
    with SFTPConnector(...) as connector:
        files = connector.list_files("/remote/dir")
except FileNotFoundError as e:
    print(f"Clé PPK introuvable: {e}")
except paramiko.AuthenticationException as e:
    print(f"Erreur d'authentification: {e}")
except Exception as e:
    print(f"Erreur inattendue: {e}")
```

## Sécurité

- Ne stockez jamais les passphrases en clair dans le code
- Utilisez des variables d'environnement ou des fichiers de configuration sécurisés
- Limitez les permissions sur les fichiers de clés PPK
- Utilisez des clés avec passphrase pour une sécurité accrue

## Dépendances

- `paramiko>=3.0.0`: Bibliothèque SSH/SFTP pour Python
