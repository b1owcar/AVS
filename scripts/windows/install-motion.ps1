#Requires -Version 5.1
<#
.SYNOPSIS
  Create isolated env-motion for Phase 5 stage-2 transfer (weights still user-supplied).
#>
param([string]$InstallRoot = "D:\avs")

$ErrorActionPreference = "Stop"
Write-Host "== Install motion env → $InstallRoot\envs\motion =="
Write-Host "This does NOT download transfer model weights."

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python not found" }

$EnvDir = Join-Path $InstallRoot "envs\motion"
New-Item -ItemType Directory -Force -Path $EnvDir | Out-Null
$repo = Join-Path $PSScriptRoot "..\..\envs\motion"
Copy-Item (Join-Path $repo "requirements.txt") (Join-Path $EnvDir "requirements.txt") -Force
Copy-Item (Join-Path $repo "worker_transfer.py") (Join-Path $EnvDir "worker_transfer.py") -Force

Set-Location $EnvDir
if (-not (Test-Path ".venv")) { python -m venv .venv }
$py = Join-Path $EnvDir ".venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt

$weights = Join-Path $InstallRoot "data\models\motion-transfer"
New-Item -ItemType Directory -Force -Path $weights | Out-Null
Set-Content -Path (Join-Path $weights "README.txt") -Value @(
  "Place a chosen Stage-2 motion-transfer weight pack here.",
  "Until worker_transfer.py is extended for that pack, transfer tasks will fail honestly.",
  "Skeleton compose preview is NOT motion transfer."
) -Encoding UTF8

$envFile = Join-Path $InstallRoot ".env"
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
Set-EnvKey $envFile "LAVS_MOTION_PYTHON" $py
Write-Host "Done. LAVS_MOTION_PYTHON=$py"
Write-Host "Add weights under $weights then extend envs/motion/worker_transfer.py"
