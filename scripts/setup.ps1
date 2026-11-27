# SEO Intelligence Engine — Windows PowerShell Setup Script
# Run from the project root: .\scripts\setup.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  SEO Intelligence Engine — Local Setup  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# ── Prerequisite checks ──────────────────────────────────────────────────────
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

$allOk = $true

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    $pyVer = python --version 2>&1
    Write-Host "  [OK] $pyVer" -ForegroundColor Green
} else {
    Write-Host "  [MISSING] Python — install from https://python.org (3.11+)" -ForegroundColor Red
    $allOk = $false
}

$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    $nodeVer = node --version
    Write-Host "  [OK] Node.js $nodeVer" -ForegroundColor Green
} else {
    Write-Host "  [MISSING] Node.js — install from https://nodejs.org (LTS)" -ForegroundColor Red
    $allOk = $false
}

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
    $dockerVer = docker --version 2>&1
    Write-Host "  [OK] $dockerVer" -ForegroundColor Green
} else {
    Write-Host "  [MISSING] Docker Desktop — install from https://docker.com" -ForegroundColor Red
    $allOk = $false
}

$composeCheck = docker compose version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Docker Compose available" -ForegroundColor Green
} else {
    Write-Host "  [MISSING] Docker Compose plugin not found" -ForegroundColor Red
    $allOk = $false
}

if (-not $allOk) {
    Write-Host ""
    Write-Host "Install missing dependencies and re-run this script." -ForegroundColor Red
    exit 1
}

# ── Environment file ─────────────────────────────────────────────────────────
Write-Host ""
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env created from .env.example" -ForegroundColor Green
    Write-Host ""
    Write-Host "ACTION REQUIRED: Open .env and set DEEPSEEK_API_KEY before first use." -ForegroundColor Yellow
    Write-Host "  Also change SECRET_KEY to a unique 64-character random string." -ForegroundColor Yellow
} else {
    Write-Host ".env already exists — skipping." -ForegroundColor Green
}

# ── Build and start ───────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Building and starting Docker services (this may take 3-5 minutes on first run)..." -ForegroundColor Yellow
Write-Host ""

docker compose up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Docker startup failed." -ForegroundColor Red
    Write-Host "Troubleshoot with: docker compose logs --tail=50" -ForegroundColor Yellow
    exit 1
}

# ── Wait for backend ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Waiting for backend to become ready..." -ForegroundColor Yellow
$retries = 24
$ready = $false
for ($i = 0; $i -lt $retries; $i++) {
    Start-Sleep -Seconds 5
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 3 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Write-Host "  ...still waiting ($([int](($i+1)*5))s)" -ForegroundColor Gray
}

if (-not $ready) {
    Write-Host "Backend did not start in time. Check: docker compose logs backend" -ForegroundColor Red
    exit 1
}

# ── Create initial admin user ─────────────────────────────────────────────────
Write-Host ""
Write-Host "Creating initial admin user..." -ForegroundColor Yellow
docker compose exec backend python /app/../scripts/init_db.py 2>&1 | Write-Host

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend   : http://localhost:5173" -ForegroundColor Cyan
Write-Host "  Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs   : http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Default login: admin@seo.local / Admin@SEO123" -ForegroundColor Yellow
Write-Host "  IMPORTANT: Change your password after first login." -ForegroundColor Yellow
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Gray
Write-Host "  docker compose logs -f backend     # Stream backend logs" -ForegroundColor Gray
Write-Host "  docker compose logs -f celery_worker  # Stream worker logs" -ForegroundColor Gray
Write-Host "  docker compose down                # Stop all services" -ForegroundColor Gray
Write-Host "  docker compose down -v             # Stop AND delete database volumes" -ForegroundColor Gray
