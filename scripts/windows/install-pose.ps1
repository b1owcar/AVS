#Requires -Version 5.1
<#
.SYNOPSIS
  Create isolated env-pose (MediaPipe) for Phase 5 pose extract.
#>
param(
  [string]$InstallRoot = "D:\avs"
)

$ErrorActionPreference = "Stop"
Write-Host "== Install pose env → $InstallRoot\envs\pose =="
Write-Host "Hardware verification: skipped (office policy)."

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python not found" }

$EnvDir = Join-Path $InstallRoot "envs\pose"
$Req = Join-Path $InstallRoot "envs\pose\requirements.txt"
$Worker = Join-Path $InstallRoot "envs\pose\worker_pose.py"

if (-not (Test-Path $Req)) {
  $altReq = Join-Path $PSScriptRoot "..\..\envs\pose\requirements.txt"
  $altWorker = Join-Path $PSScriptRoot "..\..\envs\pose\worker_pose.py"
  if (-not (Test-Path $altReq)) { throw "Missing pose requirements" }
  New-Item -ItemType Directory -Force -Path $EnvDir | Out-Null
  Copy-Item $altReq $Req -Force
  Copy-Item $altWorker $Worker -Force
}

New-Item -ItemType Directory -Force -Path $EnvDir | Out-Null
# Refresh worker from repo copy if present
$repoWorker = Join-Path $PSScriptRoot "..\..\envs\pose\worker_pose.py"
if (Test-Path $repoWorker) { Copy-Item $repoWorker $Worker -Force }
$repoReq = Join-Path $PSScriptRoot "..\..\envs\pose\requirements.txt"
if (Test-Path $repoReq) { Copy-Item $repoReq $Req -Force }

Set-Location $EnvDir
if (-not (Test-Path ".venv")) {
  python -m venv .venv
}
$py = Join-Path $EnvDir ".venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt

$envFile = Join-Path $InstallRoot ".env"
if (-not (Test-Path $envFile)) {
  Copy-Item (Join-Path $InstallRoot ".env.example") $envFile -ErrorAction SilentlyContinue
}

function Set-EnvKey([string]$Path, [string]$Key, [string]$Value) {
  if (-not (Test-Path $Path)) { Set-Content -Path $Path -Value "$Key=$Value" -Encoding UTF8; return }
  $lines = Get-Content $Path
  $found = $false
  $out = foreach ($line in $lines) {
    if ($line -match "^\s*$Key\s*=") { $found = $true; "$Key=$Value" } else { $line }
  }
  if (-not $found) { $out += "$Key=$Value" }
  Set-Content -Path $Path -Value $out -Encoding UTF8
}

Set-EnvKey $envFile "LAVS_POSE_PYTHON" $py
Write-Host "Done. Set LAVS_POSE_PYTHON=$py"
Write-Host "Restart LAVS (start.ps1) then use Motion Studio → Pose extract."
