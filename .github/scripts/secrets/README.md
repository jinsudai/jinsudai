# 🔐 Répertoire des Secrets

Ce répertoire contient tous les fichiers et scripts nécessaires pour gérer les **secrets GitHub Actions**.

## 📂 Fichiers

- **`secrets.example.json`** - Template avec tous les secrets disponibles (versionné)
- **`secrets.json`** - Votre fichier de configurations réelles (⚠️ NE PAS versionner!)
- **`setup_secrets.py`** - Script Python principal pour configurer les secrets
- **`setup_secrets.ps1`** - Helper PowerShell pour Windows
- **`setup_secrets.bat`** - Helper Batch pour Windows
- **`requirements-secrets.txt`** - Dépendances Python (requests, pynacl)

## 🚀 Quick Start

### 1️⃣ Configuration initiale

```powershell
# Copier le template
Copy-Item "secrets.example.json" "secrets.json"

# Éditer le fichier avec vos vraies valeurs
# (remplacez les x par les vraies clés)
```

### 2️⃣ Installer les dépendances

```powershell
pip install -r requirements-secrets.txt
```

### 3️⃣ Configurer les secrets

#### Option A: Python (Recommandé)
```powershell
$env:GITHUB_TOKEN = "ghp_votre_token"
python setup_secrets.py --config secrets.json --repo SustCoop/MLOps
```

#### Option B: PowerShell
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup_secrets.ps1 -Token "ghp_votre_token"
```

#### Option C: Batch
```cmd
.\setup_secrets.bat ghp_votre_token
```

## 📚 Variables d'environnement (secrets.json)

| Variable | Description | Exemple |
|----------|------------|---------|
| `HF_TOKEN` | Token Hugging Face | `hf_xxxx...` |
| `AWS_ACCESS_KEY_ID` | Clé d'accès AWS | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | Secret AWS | `wJalrXUt...` |
| `AWS_DEFAULT_REGION` | Région AWS | `eu-west-1` |
| `MLFLOW_POSTGRESQL_URI` | URI PostgreSQL MLFlow | `postgresql://user:pass@host/db` |
| `AIRFLOW_POSTGRES_CONN_ID` | URI PostgreSQL Airflow | `postgresql://user:pass@host/db` |
| `JUPYTER_TOKEN` | Token Jupyter | `xxxx...` |
| `N8N_DB_POSTGRES_URI` | URI PostgreSQL n8n | `postgresql://user:pass@host/db` |

## ⚠️ Sécurité

- **`secrets.json` est dans `.gitignore`** - Ne versionnez JAMAIS vos vrais secrets!
- **GitHub chiffre les secrets** - Personne d'autre que GitHub ne peut les lire
- **Utilisez des tokens limités** - Limitez les droits de vos GitHub Personal Access Tokens
- **Token scope recommandé** : `repo` et `workflow`

## 🔐 Obtenir un GitHub Token

1. Allez sur https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Donnez-lui un nom explicite (ex: "MLOps Secrets")
4. Cochez les scopes:
   - ✅ `repo` (full control)
   - ✅ `workflow` (update workflow)
5. Click **"Generate token"** et copier le token

## ✅ Vérification

### Lister les secrets configurés
```powershell
python setup_secrets.py --config secrets.json --repo SustCoop/MLOps --list
```

### Mode test (sans appliquer les changements)
```powershell
python setup_secrets.py --config secrets.json --repo SustCoop/MLOps --dry-run
```

## 🐛 Troubleshooting

### ❌ "Python not found"
- Installez Python depuis https://python.org
- Vérifiez qu'il est dans le PATH: `python --version`

### ❌ "Dépendances manquantes"
```powershell
pip install -r requirements-secrets.txt
```

### ❌ "Token invalid"
- Vérifiez que your token n'a pas expiré
- Régénérez-en un nouveau si nécessaire

### ❌ Problèmes d'encodage
- Utilisez PowerShell 5.1+ ou CMD
- Créez les fichiers en UTF-8 explicitement

---

**Dernière mise à jour** : 2026-03-09
