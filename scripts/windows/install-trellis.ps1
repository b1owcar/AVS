#Requires -Version 5.1
<#
.SYNOPSIS
  Scaffold env-trellis on Windows. Official TRELLIS is Linux-first / >=16GB VRAM.
  This script does NOT claim Windows native success.
#>
param([string]$InstallRoot = "D:\avs")

$ErrorActionPreference = "Stop"
Write-Warning "TRELLIS official testing is Linux-focused with >=16GB VRAM. Windows install is EXPERIMENTAL and unverified."

$EnvDir = Join-Path $InstallRoot "envs\trellis"
New-Item -ItemType Directory -Force -Path $EnvDir | Out-Null
$repo = Join-Path $PSScriptRoot "..\..\envs\trellis"
Copy-Item (Join-Path $repo "requirements.txt") (Join-Path $EnvDir "requirements.txt") -Force
Copy-Item (Join-Path $repo "worker_image_to_3d.py") (Join-Path $EnvDir "worker_image_to_3d.py") -Force
Copy-Item (Join-Path $repo "trellis_runner.py") (Join-Path $EnvDir "trellis_runner.py") -Force
Copy-Item (Join-Path $repo "trellis_runner.example.py") (Join-Path $EnvDir "trellis_runner.example.py") -Force

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python not found" }
Set-Location $EnvDir
if (-not (Test-Path ".venv")) { python -m venv .venv }
$py = Join-Path $EnvDir ".venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt

Write-Host "Scaffold only. Next (manual, prefer WSL/Linux):"
Write-Host "  1) Follow https://github.com/microsoft/TRELLIS and install into this venv"
Write-Host "  2) trellis_runner.py is shipped — calls TrellisImageTo3DPipeline when importable"
Write-Host "  3) Set LAVS_TRELLIS_PYTHON=$py"
Write-Host "Do not mark TRELLIS as Windows-verified without local PASS."
