# Setup GitHub Secrets - PowerShell Helper Script
# 
# Usage:
#   .\setup_secrets.ps1 -Token "ghp_xxx"
#   .\setup_secrets.ps1 -Token "ghp_xxx" -Config "secrets.json"
#   .\setup_secrets.ps1 -Token "ghp_xxx" -DryRun
#   .\setup_secrets.ps1 -List

param(
    [string]$Token,
    [string]$Config = "secrets.json",
    [string]$Repo = "SustCoop/MLOps",
    [switch]$DryRun,
    [switch]$List,
    [switch]$Install
)

# Couleurs
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Blue = "Cyan"

Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor $Blue
Write-Host "║     GitHub Secrets Configuration Tool                  ║" -ForegroundColor $Blue
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor $Blue
Write-Host ""

# Fonction pour afficher l'aide
function Show-Help {
    Write-Host @"
Usage: .\setup_secrets.ps1 [OPTIONS]

OPTIONS:
  -Token <string>       Token GitHub (format: ghp_xxx)
                        Si non fourni, utilise GITHUB_TOKEN
  
  -Config <string>      Chemin du fichier secrets.json
                        Défaut: "secrets.json"
  
  -Repo <string>        Dépôt GitHub (format: owner/repo)
                        Défaut: "SustCoop/MLOps"
  
  -DryRun              Affiche les secrets sans les configurer
  
  -List                Liste les secrets existants
  
  -Install             Installe les dépendances Python

EXAMPLES:
  # Configuration basique
  .\setup_secrets.ps1 -Token "ghp_xxx"

  # Test (dry-run)
  .\setup_secrets.ps1 -Token "ghp_xxx" -DryRun

  # Lister les secrets
  .\setup_secrets.ps1 -Token "ghp_xxx" -List

  # Installer les dépendances
  .\setup_secrets.ps1 -Install

"@
}

# Fonction pour installer les dépendances
function Install-Dependencies {
    Write-Host "📦 Installation des dépendances Python..." -ForegroundColor $Blue
    
    try {
        pip install -q -r "requirements-secrets.txt"
        Write-Host "✅ Dépendances installées avec succès" -ForegroundColor $Green
        return $true
    }
    catch {
        Write-Host "❌ Erreur lors de l'installation des dépendances" -ForegroundColor $Red
        Write-Host "   Essayez: pip install -r requirements-secrets.txt" -ForegroundColor $Yellow
        return $false
    }
}

# Fonction pour vérifier Python
function Test-Python {
    try {
        $version = python --version 2>&1
        Write-Host "✅ Python trouvé: $version" -ForegroundColor $Green
        return $true
    }
    catch {
        Write-Host "❌ Python n'est pas installé ou pas dans le PATH" -ForegroundColor $Red
        return $false
    }
}

# Fonction pour vérifier les dépendances
function Test-Dependencies {
    Write-Host "🔍 Vérification des dépendances..." -ForegroundColor $Blue
    
    try {
        python -c "import requests; import nacl" 2>$null
        Write-Host "✅ Dépendances OK (requests, pynacl)" -ForegroundColor $Green
        return $true
    }
    catch {
        Write-Host "❌ Dépendances manquantes" -ForegroundColor $Red
        Write-Host "   Exécutez: .\setup_secrets.ps1 -Install" -ForegroundColor $Yellow
        return $false
    }
}

# Fonction principale
function Main {
    # Afficher l'aide si -h ou pas de paramètres utiles
    if ($args -contains "-h" -or $args -contains "--help") {
        Show-Help
        return
    }

    # Option: Installation des dépendances
    if ($Install) {
        Install-Dependencies
        return
    }

    # Vérifier Python
    if (-not (Test-Python)) {
        Write-Host "⚠️  Installez Python depuis https://python.org" -ForegroundColor $Yellow
        exit 1
    }

    # Vérifier les dépendances
    if (-not (Test-Dependencies)) {
        Write-Host "💡 Astuce: .\setup_secrets.ps1 -Install" -ForegroundColor $Yellow
        exit 1
    }

    Write-Host ""

    # Obtenir le token
    if (-not $Token) {
        $Token = $env:GITHUB_TOKEN
    }

    if (-not $Token) {
        Write-Host "❌ Erreur: Token GitHub non fourni" -ForegroundColor $Red
        Write-Host ""
        Write-Host "Options:" -ForegroundColor $Yellow
        Write-Host "  1. Passez en paramètre: -Token 'ghp_xxx'" -ForegroundColor $Yellow
        Write-Host "  2. Définissez la variable: `$env:GITHUB_TOKEN = 'ghp_xxx'" -ForegroundColor $Yellow
        Write-Host ""
        Write-Host "Générer un token: https://github.com/settings/tokens" -ForegroundColor $Yellow
        exit 1
    }

    Write-Host "✅ Token GitHub trouvé" -ForegroundColor $Green

    # Option: Lister les secrets
    if ($List) {
        Write-Host "📋 Listing des secrets existants..." -ForegroundColor $Blue
        Write-Host ""
        & python "setup_secrets.py" `
            --repo $Repo `
            --token $Token `
            --list
        return
    }

    # Vérifier le fichier de configuration
    if (-not (Test-Path $Config)) {
        Write-Host "❌ Erreur: Fichier '$Config' non trouvé" -ForegroundColor $Red
        Write-Host ""
        Write-Host "Créez le fichier de secrets:" -ForegroundColor $Yellow
        Write-Host "  1. Copiez: Copy-Item 'secrets.example.json' 'secrets.json'" -ForegroundColor $Yellow
        Write-Host "  2. Éditez et remplissez les valeurs" -ForegroundColor $Yellow
        exit 1
    }

    Write-Host "✅ Fichier de secrets trouvé: $Config" -ForegroundColor $Green
    Write-Host ""

    # Construire les arguments
    $scriptArgs = @(
        "--config", $Config,
        "--repo", $Repo,
        "--token", $Token
    )

    if ($DryRun) {
        Write-Host "🧪 Mode DRY-RUN (test sans modifications)" -ForegroundColor $Yellow
        Write-Host ""
        $scriptArgs += "--dry-run"
    }

    # Exécuter le script Python
    Write-Host "▶️  Exécution du script..." -ForegroundColor $Blue
    Write-Host ""
    
    & python "setup_secrets.py" @scriptArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor $Green
        Write-Host "║  ✅ Secrets configurés avec succès!                    ║" -ForegroundColor $Green
        Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor $Green
        exit 0
    }
    else {
        Write-Host ""
        Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor $Red
        Write-Host "║  ❌ Erreur lors de la configuration                    ║" -ForegroundColor $Red
        Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor $Red
        exit 1
    }
}

# Lancer
Main
