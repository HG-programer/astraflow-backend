# AstraFlow Python Backend Launcher
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🚦 Starting AstraFlow AI & Backend Engine..." -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

$PythonExe = "D:\5.1\python\bin\python.exe"

if (-Not (Test-Path $PythonExe)) {
    Write-Host "Warning: Specific python path not found, using system python..." -ForegroundColor Yellow
    $PythonExe = "python"
}

& $PythonExe -m astraflow_backend.app
