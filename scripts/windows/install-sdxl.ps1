#Requires -Version 5.1
<#
.SYNOPSIS
  Create isolated env-image and optionally download SDXL Diffusers weights under D:\avs.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\windows\install-sdxl.ps1 -DownloadWeights
#>
param(
  [string]$InstallRoot = "D:\avs",
  [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu124",
  [switch]$DownloadWeights
)

$ErrorActionPreference = "Stop"
Write-Host "== Install SDXL native env → $InstallRoot\envs\image =="
Write-Host "Hardware verification: skipped (office policy)."

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python not found" }

$EnvDir = Join-Path $InstallRoot "envs\image"
$Req = Join-Path $InstallRoot "envs\image\requirements.txt"
if (-not (Test-Path $Req)) {
  # fallback if script run from repo before copy
  $alt = Join-Path $PSScriptRoot "..\..\envs\image\requirements.txt"
  if (Test-Path $alt) {
    New-Item -ItemType Directory -Force -Path $EnvDir | Out-Null
    Copy-Item $alt $Req -Force
    Copy-Item (Join-Path $PSScriptRoot "..\..\envs\image\worker_txt2img.py") (Join-Path $EnvDir "worker_txt2img.py") -Force
  } else {
    throw "Missing $Req — deploy project to $InstallRoot first."
  }
}

New-Item -ItemType Directory -Force -Path $EnvDir | Out-Null
Set-Location $EnvDir
if (-not (Test-Path ".venv")) {
  python -m venv .venv
}
$py = Join-Path $EnvDir ".venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
Write-Host "Installing PyTorch from $TorchIndexUrl ..."
& $py -m pip install torch torchvision --index-url $TorchIndexUrl
& $py -m pip install -r requirements.txt

$modelDir = Join-Path $InstallRoot "data\models\sdxl-base-1.0"
New-Item -ItemType Directory -Force -Path (Join-Path $InstallRoot "data\models") | Out-Null

if ($DownloadWeights) {
  Write-Host "Downloading stabilityai/stable-diffusion-xl-base-1.0 (multi-GB)..."
  & $py -m pip install "huggingface_hub[cli]"
  & $py -c @"
from huggingface_hub import snapshot_download
p = snapshot_download(repo_id='stabilityai/stable-diffusion-xl-base-1.0', local_dir=r'$($modelDir.Replace('\','\\'))', local_dir_use_symlinks=False)
print('downloaded to', p)
"@
}

$envFile = Join-Path $InstallRoot ".env"
if (-not (Test-Path $envFile)) {
  $example = Join-Path $InstallRoot ".env.example"
  if (Test-Path $example) { Copy-Item $example $envFile }
}

function Set-EnvKey([string]$Path, [string]$Key, [string]$Value) {
  if (-not (Test-Path $Path)) { Set-Content -Path $Path -Value "$Key=$Value" -Encoding UTF8; return }
  $lines = Get-Content $Path
  $found = $false
  $out = foreach ($line in $lines) {
    if ($line -match "^\s*$([regex]::Escape($Key))\s*=") { $found = $true; "$Key=$Value" } else { $line }
  }
  if (-not $found) { $out += "$Key=$Value" }
  Set-Content -Path $Path -Value $out -Encoding UTF8
}

Set-EnvKey $envFile "LAVS_IMAGE_PYTHON" $py
Set-EnvKey $envFile "LAVS_MODEL_DIR" (Join-Path $InstallRoot "data\models")
Set-EnvKey $envFile "LAVS_ALLOW_MODEL_DOWNLOAD" "1"
Set-EnvKey $envFile "LAVS_RUN_MODE" "real"
Set-EnvKey $envFile "LAVS_SKIP_HARDWARE_VERIFICATION" "1"
Set-EnvKey $envFile "LAVS_INSTALL_ROOT" $InstallRoot

Write-Host ""
Write-Host "SDXL env ready: $py"
if (Test-Path $modelDir) {
  Write-Host "Weights path: $modelDir"
} else {
  Write-Host "Weights not downloaded yet. Re-run with -DownloadWeights"
}
Write-Host "Restart LAVS after this script so it picks up .env changes."
