#Requires -Version 5.1
<#
.SYNOPSIS
  Start ComfyUI (portable or engines\ComfyUI) for LAVS Wan/SDXL workflows.
#>
param(
  [string]$InstallRoot = "D:\avs",
  [string]$Listen = "127.0.0.1",
  [int]$Port = 8188
)

$ErrorActionPreference = "Stop"

$candidates = @(
  (Join-Path $InstallRoot "engines\ComfyUI"),
  (Join-Path $InstallRoot "ComfyUI"),
  (Join-Path $InstallRoot "engines\ComfyUI_windows_portable\ComfyUI"),
  (Join-Path $InstallRoot "external\ComfyUI_windows_portable\ComfyUI"),
  (Join-Path $InstallRoot "external\ComfyUI")
)

$ComfyDir = $null
foreach ($c in $candidates) {
  if (Test-Path (Join-Path $c "main.py")) { $ComfyDir = $c; break }
}
if (-not $ComfyDir) {
  throw "ComfyUI not found under $InstallRoot. Run install-comfyui.ps1 or place portable build."
}

Write-Host "Starting ComfyUI from $ComfyDir on http://${Listen}:${Port}"

$py = Join-Path $ComfyDir ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  $portableCandidates = @(
    (Join-Path $InstallRoot "engines\ComfyUI_windows_portable\python_embeded\python.exe"),
    (Join-Path $InstallRoot "external\ComfyUI_windows_portable\python_embeded\python.exe"),
    (Join-Path (Split-Path $ComfyDir -Parent) "python_embeded\python.exe")
  )
  $py = $null
  foreach ($p in $portableCandidates) {
    if (Test-Path $p) { $py = $p; break }
  }
  if (-not $py) {
    throw "ComfyUI python not found (.venv or portable python_embeded)"
  }
}

Set-Location $ComfyDir
& $py main.py --listen $Listen --port $Port
