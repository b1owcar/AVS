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
Copy-Item (Join-Path $repo "run_transfer.example.py") (Join-Path $EnvDir "run_transfer.example.py") -Force
Copy-Item (Join-Path $repo "backend.example.json") (Join-Path $EnvDir "backend.example.json") -Force

Set-Location $EnvDir
if (-not (Test-Path ".venv")) { python -m venv .venv }
$py = Join-Path $EnvDir ".venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
& $py -m pip install "httpx>=0.27,<1.0"

$weights = Join-Path $InstallRoot "data\models\motion-transfer"
New-Item -ItemType Directory -Force -Path $weights | Out-Null
Copy-Item (Join-Path $repo "run_transfer.example.py") (Join-Path $weights "run_transfer.example.py") -Force
Copy-Item (Join-Path $repo "backend.example.json") (Join-Path $weights "backend.example.json") -Force
Set-Content -Path (Join-Path $weights "README.txt") -Value @(
  "Wire a Stage-2 backend here:",
  "  1) Copy run_transfer.example.py to run_transfer.py and implement run_transfer(), OR",
  "  2) Add backend.json (see backend.example.json) for external_script / comfyui.",
  "README alone does NOT mark transfer ready.",
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
Write-Host "Wire backend under $weights (run_transfer.py or backend.json), then restart LAVS."
