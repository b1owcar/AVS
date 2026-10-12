$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

Write-Host "== Local AI Vision Studio Windows setup =="
Write-Host "Project root: $Root"
Write-Host "Installs MAIN BACKEND + FRONTEND deps only."
Write-Host "Does NOT install PyTorch/CUDA/Diffusers or download model weights."

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "python not found on PATH"
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm not found on PATH"
}

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r backend\requirements.txt

Push-Location frontend
npm install
Pop-Location

if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host "Created .env from .env.example"
}

New-Item -ItemType Directory -Force -Path data\models, data\outputs, data\uploads, data\logs, data\db | Out-Null
Write-Host "Setup complete. Next: scripts\windows\start.ps1"
Write-Host "Before real inference, run scripts\diagnose\check_environment.ps1"
