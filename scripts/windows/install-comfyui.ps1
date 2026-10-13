#Requires -Version 5.1
<#
.SYNOPSIS
  Install ComfyUI under D:\avs\engines\ComfyUI (isolated from LAVS backend venv).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\windows\install-comfyui.ps1
  powershell -ExecutionPolicy Bypass -File .\scripts\windows\install-comfyui.ps1 -DownloadSdxlCheckpoint
#>
param(
  [string]$InstallRoot = "D:\avs",
  [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu124",
  [switch]$DownloadSdxlCheckpoint,
  [switch]$StartServer
)

$ErrorActionPreference = "Stop"
Write-Host "== Install ComfyUI → $InstallRoot\engines\ComfyUI =="
Write-Host "Hardware verification: skipped (office policy)."

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git not found" }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python not found" }

$EngineRoot = Join-Path $InstallRoot "engines"
$ComfyDir = Join-Path $EngineRoot "ComfyUI"
New-Item -ItemType Directory -Force -Path $EngineRoot | Out-Null

if (-not (Test-Path (Join-Path $ComfyDir "main.py"))) {
  Write-Host "Cloning ComfyUI..."
  git clone https://github.com/Comfy-Org/ComfyUI.git $ComfyDir
} else {
  Write-Host "ComfyUI already present: $ComfyDir"
}

Set-Location $ComfyDir
if (-not (Test-Path ".venv")) {
  python -m venv .venv
}
$py = Join-Path $ComfyDir ".venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
Write-Host "Installing PyTorch from $TorchIndexUrl ..."
& $py -m pip install torch torchvision torchaudio --index-url $TorchIndexUrl
& $py -m pip install -r requirements.txt

$ckptDir = Join-Path $ComfyDir "models\checkpoints"
New-Item -ItemType Directory -Force -Path $ckptDir | Out-Null

if ($DownloadSdxlCheckpoint) {
  Write-Host "Downloading SDXL base single-file checkpoint (large)..."
  & $py -m pip install "huggingface_hub[cli]"
  # Diffusers-style tree is for native path; for Comfy use community single-file when available.
  # Official repo is multi-folder; attempt hf download of common single-file mirror name into checkpoints.
  $dest = Join-Path $ckptDir "sd_xl_base_1.0.safetensors"
  if (-not (Test-Path $dest)) {
    Write-Host "Fetching stabilityai/stable-diffusion-xl-base-1.0 (may take a long time)..."
    & $py -c @"
from huggingface_hub import hf_hub_download
import shutil, os
# Prefer a safetensors single file if present in repo root variants; else download full snapshot note.
path = hf_hub_download(repo_id='stabilityai/stable-diffusion-xl-base-1.0', filename='sd_xl_base_1.0.safetensors')
shutil.copy2(path, r'$($dest.Replace('\','\\'))')
print('copied', path, '->', r'$($dest.Replace('\','\\'))')
"@
    if (-not (Test-Path $dest)) {
      Write-Warning "Single-file sd_xl_base_1.0.safetensors not found on Hub root. Place a Comfy-compatible SDXL .safetensors into: $ckptDir"
    }
  } else {
    Write-Host "Checkpoint already exists: $dest"
  }
}

# Patch LAVS .env
$envFile = Join-Path $InstallRoot ".env"
if (-not (Test-Path $envFile)) { Copy-Item (Join-Path $InstallRoot ".env.example") $envFile -ErrorAction SilentlyContinue }

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

Set-EnvKey $envFile "LAVS_COMFYUI_URL" "http://127.0.0.1:8188"
Set-EnvKey $envFile "LAVS_COMFYUI_DIR" $ComfyDir
Set-EnvKey $envFile "LAVS_COMFYUI_OUTPUT_DIR" (Join-Path $ComfyDir "output")
Set-EnvKey $envFile "LAVS_COMFYUI_CHECKPOINT" "sd_xl_base_1.0.safetensors"
Set-EnvKey $envFile "LAVS_ALLOW_MODEL_DOWNLOAD" "1"
Set-EnvKey $envFile "LAVS_SKIP_HARDWARE_VERIFICATION" "1"

Write-Host ""
Write-Host "ComfyUI install done."
Write-Host "Start ComfyUI:"
Write-Host "  & '$py' '$ComfyDir\main.py' --listen 127.0.0.1 --port 8188"
Write-Host "Then start LAVS: scripts\windows\start.ps1"

if ($StartServer) {
  & $py (Join-Path $ComfyDir "main.py") --listen 127.0.0.1 --port 8188
}
