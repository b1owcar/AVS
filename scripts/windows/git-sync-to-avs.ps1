#Requires -Version 5.1
<#
.SYNOPSIS
  Use git (not zip) to pull latest LAVS into a staging folder, then merge into D:\avs.

.EXAMPLE
  # After you click Create repo in Cursor and copy the HTTPS URL:
  powershell -ExecutionPolicy Bypass -File C:\Temp\git-sync-to-avs.ps1 `
    -GitUrl "https://github.com/<you>/<repo>.git"

  # If you already cloned to C:\Temp\lavs-fresh:
  powershell -ExecutionPolicy Bypass -File C:\Temp\lavs-fresh\scripts\windows\git-sync-to-avs.ps1 `
    -SourceDir C:\Temp\lavs-fresh -GitPull
#>
param(
  [string]$InstallRoot = "D:\avs",
  # Prefer SSH once GitHub has the full tree (after seed-from-bundle-to-github.ps1)
  [string]$GitUrl = "git@github.com:b1owcar/AVS.git",
  [string]$SourceDir = "C:\Temp\lavs-fresh",
  [string]$Branch = "main",
  [switch]$GitPull,
  [switch]$StartAfter,
  [switch]$NoDefaultUrl
)

$ErrorActionPreference = "Stop"

if ($NoDefaultUrl) { $GitUrl = "" }

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "git not found. Install Git for Windows, then reopen PowerShell."
}

# If this script already lives inside a checkout, prefer that as SourceDir
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "..\..\backend\app\main.py"))) {
  $embeddedRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
  if ((-not $GitUrl -or $NoDefaultUrl) -and -not $GitPull) {
    $SourceDir = $embeddedRoot
    Write-Host "Using checkout that contains this script: $SourceDir"
  }
}

if ($GitUrl) {
  $parent = Split-Path $SourceDir -Parent
  if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
  if (Test-Path (Join-Path $SourceDir ".git")) {
    Write-Host "Existing clone at $SourceDir - fetch/pull $Branch"
    Push-Location $SourceDir
    try {
      git remote set-url origin $GitUrl
      git fetch origin $Branch
      git checkout $Branch
      git pull origin $Branch
    } finally { Pop-Location }
  } else {
    if (Test-Path $SourceDir) {
      Write-Warning "$SourceDir exists without .git - moving aside"
      Rename-Item $SourceDir ($SourceDir + ".bak-" + (Get-Date -Format "yyyyMMddHHmmss"))
    }
    Write-Host "git clone --branch $Branch $GitUrl -> $SourceDir"
    git clone --branch $Branch --single-branch $GitUrl $SourceDir
  }
} elseif ($GitPull) {
  if (-not (Test-Path (Join-Path $SourceDir ".git"))) {
    throw "$SourceDir is not a git clone. Pass -GitUrl once to clone."
  }
  Push-Location $SourceDir
  try {
    git fetch origin $Branch
    git checkout $Branch
    git pull origin $Branch
  } finally { Pop-Location }
} elseif (-not (Test-Path (Join-Path $SourceDir "backend\app\main.py"))) {
  throw @"
Need one of:
  -GitUrl <repo-https-url>   (clone/pull into $SourceDir)
  -SourceDir <existing-clone> -GitPull
Create a durable repo in Cursor (Create repo), copy its HTTPS URL, then re-run with -GitUrl.
"@
}

$SourceDir = (Resolve-Path $SourceDir).Path
Write-Host "Staging tree: $SourceDir"
Write-Host "Target:       $InstallRoot"

$apply = Join-Path $SourceDir "scripts\windows\APPLY-TO-D-AVS.ps1"
if (Test-Path $apply) {
  & $apply -InstallRoot $InstallRoot
} else {
  # Fallback robocopy if APPLY missing (very old tree)
  if (-not (Test-Path $InstallRoot)) { New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null }
  $roboArgs = @(
    $SourceDir, $InstallRoot, "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:2", "/W:2",
    "/XD", ".venv", "node_modules", "dist", ".git", "agent-tools",
    "engines", "data", "outputs", "uploads", "logs", "db", "external"
  )
  $rc = Start-Process robocopy.exe -ArgumentList $roboArgs -Wait -PassThru -NoNewWindow
  if ($rc.ExitCode -ge 8) { throw "robocopy failed $($rc.ExitCode)" }
  New-Item -ItemType Directory -Force -Path (Join-Path $InstallRoot "scripts\windows") | Out-Null
  Copy-Item (Join-Path $SourceDir "scripts\windows\*") (Join-Path $InstallRoot "scripts\windows") -Force -ErrorAction SilentlyContinue
}

$startAll = Join-Path $InstallRoot "scripts\windows\start-all.ps1"
Write-Host ""
Write-Host "Git sync done. Verify:"
Write-Host "  Test-Path $startAll   -> $(Test-Path $startAll)"
Write-Host "Start:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$startAll`""
if ($StartAfter -and (Test-Path $startAll)) {
  & $startAll -InstallRoot $InstallRoot
}
