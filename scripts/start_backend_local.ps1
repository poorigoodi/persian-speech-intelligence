# Start FastAPI backend locally (SQLite, no Docker required)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$VenvPython = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtualenv not found at $VenvPython. Create it first."
}

# Refresh PATH so winget-installed tools (e.g. FFmpeg) are visible
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Warning "FFmpeg not found on PATH. Install with: winget install Gyan.FFmpeg"
}

Set-Location $Backend
$env:DATABASE_URL = "sqlite:///./storage/psi_local.db"
$env:STORAGE_DIR = Join-Path $Root "storage"
$env:UPLOAD_DIR = Join-Path $Root "storage\uploads"
$env:TEMP_DIR = Join-Path $Root "storage\temp"
$env:VECTOR_INDEX_DIR = Join-Path $Root "storage\vector_indexes"
$env:AUTH_ENABLED = "false"

New-Item -ItemType Directory -Force -Path $env:UPLOAD_DIR, $env:TEMP_DIR, $env:VECTOR_INDEX_DIR, (Join-Path $Backend "storage") | Out-Null

Write-Host "Starting API on http://localhost:8000 ..."
& $VenvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
