#Requires -Version 5.1
<#
.SYNOPSIS
  Deploy Local AI Vision Studio into D:\avs on this Windows PC.

.DESCRIPTION
  Run this script ON the office Windows machine (not in the cloud agent).
  Default install root: D:\avs

  Modes:
    - FromRepo (default): copy from -SourceDir, or clone -GitUrl into D:\avs
    - Does NOT download model weights
    - Does NOT run GPU hardware verification (per office deploy request)

.EXAMPLE
  # After copying the project zip / folder next to this script's repo:
  powershell -ExecutionPolicy Bypass -File .\scripts\windows\deploy-to-d-avs.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\windows\deploy-to-d-avs.ps1 -SourceDir "C:\Users\me\Downloads\lavs"
#>
param(
  [string]$InstallRoot = "D:\avs",
  [string]$SourceDir = "",
  [string]$GitUrl = "",
  [switch]$SkipNpmInstall,
  [switch]$StartAfterDeploy
)

$ErrorActionPreference = "Stop"

Write-Host "== Local AI Vision Studio → $InstallRoot =="
Write-Host "Hardware verification: SKIPPED (office deploy request)."
Write-Host "Model weight download: NOT performed."

if (-not (Test-Path "D:\")) {
  throw "Drive D: not found. Create D:\avs on the office PC and re-run."
}

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

function Assert-Command([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name not found on PATH. Install it before deploying."
  }
}

Assert-Command "python"
Assert-Command "npm"

# Resolve source: explicit SourceDir, else current repo root if this script lives in a checkout
$RepoFromScript = $null
try {
  $RepoFromScript = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
} catch {
  $RepoFromScript = $null
}

if (-not $SourceDir) {
  if ($RepoFromScript -and (Test-Path (Join-Path $RepoFromScript "backend\app\main.py"))) {
    $SourceDir = $RepoFromScript
  }
}

if ($GitUrl) {
  Assert-Command "git"
  Write-Host "Cloning $GitUrl → $InstallRoot"
  if ((Get-ChildItem -Force $InstallRoot | Measure-Object).Count -gt 0) {
    throw "$InstallRoot is not empty. Empty it or omit -GitUrl and use -SourceDir copy mode."
  }
  git clone $GitUrl $InstallRoot
} elseif ($SourceDir) {
  $SourceDir = (Resolve-Path $SourceDir).Path
  if (-not (Test-Path (Join-Path $SourceDir "backend\app\main.py"))) {
    throw "SourceDir does not look like LAVS project: $SourceDir"
  }
  $installFull = [System.IO.Path]::GetFullPath($InstallRoot)
  if ($SourceDir.TrimEnd('\') -ieq $installFull.TrimEnd('\')) {
    Write-Host "Source already is $InstallRoot — skip file sync, continue with venv/deps."
  } else {
  Write-Host "Syncing project files: $SourceDir → $InstallRoot"
  # Robocopy: copy code, skip heavy/runtime dirs (names match any depth)
  $roboArgs = @(
    $SourceDir, $InstallRoot,
    "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:1", "/W:1",
    "/XD", ".venv", "node_modules", "dist", ".git", "agent-tools",
    "outputs", "uploads", "logs", "db"
  )
  $rc = Start-Process -FilePath "robocopy.exe" -ArgumentList $roboArgs -Wait -PassThru -NoNewWindow
  # robocopy exit codes 0-7 are success
  if ($rc.ExitCode -ge 8) {
    throw "robocopy failed with exit code $($rc.ExitCode)"
  }
  } # end else sync
} else {
  throw "Provide -SourceDir (path to project) or -GitUrl, or run this script from inside the project tree."
}

Set-Location $InstallRoot

if (-not (Test-Path "backend\app\main.py")) {
  throw "Deploy incomplete: backend\app\main.py missing under $InstallRoot"
}

Write-Host "Creating Python venv…"
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r backend\requirements.txt

if (-not $SkipNpmInstall) {
  Write-Host "Installing frontend dependencies…"
  Push-Location frontend
  npm install
  Pop-Location
}

New-Item -ItemType Directory -Force -Path data\models, data\outputs, data\uploads, data\logs, data\db | Out-Null

$envPath = Join-Path $InstallRoot ".env"
if (-not (Test-Path $envPath)) {
  Copy-Item (Join-Path $InstallRoot ".env.example") $envPath
}

# Force office defaults into .env (idempotent key upsert)
function Set-EnvKey([string]$Path, [string]$Key, [string]$Value) {
  $lines = @()
  if (Test-Path $Path) { $lines = Get-Content $Path }
  $found = $false
  $out = foreach ($line in $lines) {
    if ($line -match "^\s*$([regex]::Escape($Key))\s*=") {
      $found = $true
      "$Key=$Value"
    } else {
      $line
    }
  }
  if (-not $found) { $out += "$Key=$Value" }
  Set-Content -Path $Path -Value $out -Encoding UTF8
}

Set-EnvKey $envPath "LAVS_HOST" "127.0.0.1"
Set-EnvKey $envPath "LAVS_PORT" "18765"
Set-EnvKey $envPath "LAVS_RUN_MODE" "simulation"
Set-EnvKey $envPath "LAVS_DATA_DIR" "./data"
Set-EnvKey $envPath "LAVS_MODEL_DIR" "./data/models"
Set-EnvKey $envPath "LAVS_OUTPUT_DIR" "./data/outputs"
Set-EnvKey $envPath "LAVS_UPLOAD_DIR" "./data/uploads"
Set-EnvKey $envPath "LAVS_LOG_DIR" "./data/logs"
Set-EnvKey $envPath "LAVS_DB_PATH" "./data/db/lavs.sqlite3"
Set-EnvKey $envPath "LAVS_INSTALL_ROOT" $InstallRoot
Set-EnvKey $envPath "LAVS_SKIP_HARDWARE_VERIFICATION" "1"

# Marker file: office install complete, HW verify skipped by user request
$marker = @"
install_root=$InstallRoot
deployed_at=$(Get-Date -Format o)
hardware_verification=skipped_by_user_request
run_mode=simulation
"@
Set-Content -Path (Join-Path $InstallRoot "data\DEPLOYED_OFFICE.txt") -Value $marker -Encoding UTF8

Write-Host ""
Write-Host "Deploy complete."
Write-Host "  Root: $InstallRoot"
Write-Host "  API:  http://127.0.0.1:18765"
Write-Host "  UI:   http://127.0.0.1:18766"
Write-Host "  HW verification: skipped"
Write-Host ""
Write-Host "Start with:"
Write-Host "  powershell -ExecutionPolicy Bypass -File $InstallRoot\scripts\windows\start.ps1"

if ($StartAfterDeploy) {
  & (Join-Path $InstallRoot "scripts\windows\start.ps1")
}
