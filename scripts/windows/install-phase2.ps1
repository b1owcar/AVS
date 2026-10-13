#Requires -Version 5.1
<#
.SYNOPSIS
  Phase 2/3 office installer: ComfyUI + SDXL native env (+ optional weight downloads).

.EXAMPLE
  cd D:\avs
  powershell -ExecutionPolicy Bypass -File .\scripts\windows\install-phase2.ps1 -DownloadWeights
#>
param(
  [string]$InstallRoot = "D:\avs",
  [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu124",
  [switch]$DownloadWeights,
  [switch]$SkipComfyUI,
  [switch]$SkipSdxlNative
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot

Write-Host "==== LAVS Phase 2/3 install ($InstallRoot) ===="
Write-Host "Skips hardware verification per office policy."
Write-Host "Torch index: $TorchIndexUrl"
Write-Host "If pip/torch fails on RTX 50-series, retry with e.g. -TorchIndexUrl https://download.pytorch.org/whl/cu128"

if (-not $SkipComfyUI) {
  $comfyArgs = @{
    InstallRoot = $InstallRoot
    TorchIndexUrl = $TorchIndexUrl
  }
  if ($DownloadWeights) { $comfyArgs.DownloadSdxlCheckpoint = $true }
  & (Join-Path $ScriptDir "install-comfyui.ps1") @comfyArgs
}

if (-not $SkipSdxlNative) {
  $sdxlArgs = @{
    InstallRoot = $InstallRoot
    TorchIndexUrl = $TorchIndexUrl
  }
  if ($DownloadWeights) { $sdxlArgs.DownloadWeights = $true }
  & (Join-Path $ScriptDir "install-sdxl.ps1") @sdxlArgs
}

Write-Host ""
Write-Host "==== Next steps ===="
Write-Host "1. Start ComfyUI (separate terminal):"
Write-Host "   & '$InstallRoot\engines\ComfyUI\.venv\Scripts\python.exe' '$InstallRoot\engines\ComfyUI\main.py' --listen 127.0.0.1 --port 8188"
Write-Host "2. Start LAVS:"
Write-Host "   powershell -ExecutionPolicy Bypass -File $InstallRoot\scripts\windows\start.ps1"
Write-Host "3. Open http://127.0.0.1:18766 → Image Studio"
Write-Host "   Models: mock-demo | sdxl-base-1.0 (native) | sdxl-comfyui"
