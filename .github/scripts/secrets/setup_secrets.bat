@echo off
REM Setup GitHub Secrets - Batch Script for Windows
REM Usage: setup_secrets.bat ghp_token [config_file] [repo]

setlocal enabledelayedexpansion
chcp 65001 >nul

echo.
echo ============================================================
echo     GitHub Secrets Configuration Tool (Batch)
echo ============================================================
echo.

REM Paramètres
set TOKEN=%1
set CONFIG=%2
set REPO=%3

if "%CONFIG%"=="" set CONFIG=secrets.json
if "%REPO%"=="" set REPO=jinsudai/jinsudai

REM Afficher l'aide si pas de token
if "%TOKEN%"=="" (
    echo [ERR] Token GitHub requis
    echo.
    echo Usage: setup_secrets.bat ^<token^> [config_file] [repo]
    echo.
    echo Examples:
    echo   setup_secrets.bat ghp_xxx
    echo   setup_secrets.bat ghp_xxx "secrets.json" "jinsudai/jinsudai"
    echo.
    echo Obtenir un token: https://github.com/settings/tokens
    exit /b 1
)

echo [OK] Token trouve
echo.

REM Vérifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERR] Python n'est pas installe ou pas dans le PATH
    exit /b 1
)

echo [OK] Python trouve: 
python --version
echo.

REM Vérifier les dépendances
echo [*] Verification des dependances...
python -c "import requests; import nacl" 2>nul
if errorlevel 1 (
    echo [ERR] Dependances manquantes
    echo.
    echo Installation: pip install -r requirements-secrets.txt
    exit /b 1
)

echo [OK] Dependances OK
echo.

REM Executer le script Python
echo [*] Execution du script...
echo.

set GITHUB_TOKEN=%TOKEN%
python "%~dp0.\setup_secrets.py" --config "%CD%\%CONFIG%" --repo %REPO% --token %TOKEN%

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  [ERR] Erreur lors de la configuration
    echo ============================================================
    exit /b 1
) else (
    echo.
    echo ============================================================
    echo  [OK] Secrets configures avec succes!
    echo ============================================================
)

endlocal
