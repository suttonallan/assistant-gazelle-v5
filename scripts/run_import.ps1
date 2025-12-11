# Script PowerShell pour lancer l'import avec debug
# Usage: .\run_import.ps1

$ErrorActionPreference = "Continue"

Write-Host "🚀 Lancement du script d'import..." -ForegroundColor Cyan
Write-Host ""

# Aller dans le bon répertoire
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectPath = Split-Path -Parent $scriptPath
Set-Location $projectPath

Write-Host "📁 Répertoire: $projectPath" -ForegroundColor Gray
Write-Host ""

# Vérifier que Python est disponible
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python trouvé: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python non trouvé! Installez Python d'abord." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🔄 Exécution du script d'import..." -ForegroundColor Yellow
Write-Host ""

# Lancer le script avec unbuffered et redirection des erreurs
python -u scripts/import_gazelle_product_display.py 2>&1

Write-Host ""
Write-Host "✅ Script terminé!" -ForegroundColor Green
