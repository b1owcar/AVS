#Requires -Version 5.1
<#
.SYNOPSIS
  Apply THIS checkout (cloud sync package) onto D:\avs.

  Intended use after you unzip the cloud deploy zip to e.g. C:\Temp\lavs-fresh:
    powershell -ExecutionPolicy Bypass -File C:\Temp\lavs-fresh\scripts\windows\APPLY-TO-D-AVS.ps1

  Preserves D:\avs data, engines, external, .venv, envs\*\.venv, node_modules.
#>
param(
  [string]$InstallRoot = "D:\avs",
  [switch]$StartAfter,
  [switch]$SkipNpmPip
)

$ErrorActionPreference = "Stop"

# This script lives in <checkout>\scripts\windows → repo root is ../..
$SourceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Write-Host "== APPLY cloud checkout → $InstallRoot =="
Write-Host "Source: $SourceRoot"

if (-not (Test-Path (Join-Path $SourceRoot "backend\app\main.py"))) {
  throw "Source does not look like LAVS repo root: $SourceRoot"
}
if (-not (Test-Path $InstallRoot)) {
  Write-Warning "$InstallRoot missing — creating skeleton (you may still need setup.ps1 / venv)."
  New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
}

$roboArgs = @(
  $SourceRoot, $InstallRoot,
  "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:2", "/W:2",
  "/XD", ".venv", "node_modules", "dist", ".git", "agent-tools",
  "engines", "data", "outputs", "uploads", "logs", "db", "external",
  ".pytest_cache", "__pycache__"
)
$rc = Start-Process -FilePath "robocopy.exe" -ArgumentList $roboArgs -Wait -PassThru -NoNewWindow
if ($rc.ExitCode -ge 8) { throw "robocopy failed: $($rc.ExitCode)" }

# Force critical scripts (chicken-egg)
$win = Join-Path $InstallRoot "scripts\windows"
New-Item -ItemType Directory -Force -Path $win | Out-Null
Copy-Item (Join-Path $SourceRoot "scripts\windows\*") $win -Force

# Ensure isolated env worker files exist (do not wipe .venv)
function Copy-EnvTree([string]$Name) {
  $from = Join-Path $SourceRoot "envs\$Name"
  $to = Join-Path $InstallRoot "envs\$Name"
  if (-not (Test-Path $from)) { return }
  New-Item -ItemType Directory -Force -Path $to | Out-Null
  Get-ChildItem $from -Force | Where-Object { $_.Name -ne ".venv" } | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $to $_.Name) -Recurse -Force
  }
}
Copy-EnvTree "image"
Copy-EnvTree "pose"
Copy-EnvTree "motion"
Copy-EnvTree "trellis"

# config workflows
$wfFrom = Join-Path $SourceRoot "config\workflows"
$wfTo = Join-Path $InstallRoot "config\workflows"
if (Test-Path $wfFrom) {
  New-Item -ItemType Directory -Force -Path $wfTo | Out-Null
  Copy-Item (Join-Path $wfFrom "*") $wfTo -Force
}

if (-not (Test-Path (Join-Path $InstallRoot ".env")) -and (Test-Path (Join-Path $InstallRoot ".env.example"))) {
  Copy-Item (Join-Path $InstallRoot ".env.example") (Join-Path $InstallRoot ".env")
}

$startAll = Join-Path $win "start-all.ps1"
$okStart = Test-Path $startAll
Write-Host ""
Write-Host "Robocopy finished. start-all.ps1 present: $okStart"

if (-not $SkipNpmPip) {
  if (Test-Path (Join-Path $InstallRoot ".venv\Scripts\pip.exe")) {
    Write-Host "Refreshing backend deps…"
    & (Join-Path $InstallRoot ".venv\Scripts\pip.exe") install -r (Join-Path $InstallRoot "backend\requirements.txt")
  } else {
    Write-Warning "No $InstallRoot\.venv — run scripts\windows\setup.ps1 before start."
  }
  if (Test-Path (Join-Path $InstallRoot "frontend\package.json")) {
    Write-Host "Refreshing frontend deps…"
    Push-Location (Join-Path $InstallRoot "frontend")
    try { npm install } finally { Pop-Location }
  }
}

Write-Host ""
Write-Host "Deploy to local DONE."
Write-Host "Start: powershell -ExecutionPolicy Bypass -File `"$startAll`""
if ($StartAfter) {
  if (-not $okStart) { throw "start-all.ps1 missing after apply" }
  & $startAll -InstallRoot $InstallRoot
}
