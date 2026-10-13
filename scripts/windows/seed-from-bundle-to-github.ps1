#Requires -Version 5.1
<#
.SYNOPSIS
  Import cloud git bundle → push to your GitHub (SSH) → merge into D:\avs.

  Cloud agents cannot use your GitHub SSH key. Run this ON THE OFFICE PC.

.EXAMPLE
  # Put avs-main.bundle next to this script (or pass -BundlePath), then:
  powershell -ExecutionPolicy Bypass -File .\seed-from-bundle-to-github.ps1

  # Defaults target: git@github.com:b1owcar/AVS.git
#>
param(
  [string]$BundlePath = "",
  [string]$GitHubSsh = "git@github.com:b1owcar/AVS.git",
  [string]$StageDir = "C:\Temp\lavs-fresh",
  [string]$InstallRoot = "D:\avs",
  [string]$Branch = "main",
  [switch]$SkipPush,
  [switch]$SkipApply,
  [switch]$StartAfter
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "git not found. Install Git for Windows and reopen PowerShell."
}

if (-not $BundlePath) {
  $candidates = @(
    (Join-Path $PSScriptRoot "avs-main.bundle"),
    (Join-Path (Get-Location) "avs-main.bundle"),
    "C:\Temp\avs-main.bundle",
    (Join-Path $env:USERPROFILE "Downloads\avs-main.bundle")
  )
  foreach ($c in $candidates) {
    if (Test-Path $c) { $BundlePath = $c; break }
  }
}
if (-not $BundlePath -or -not (Test-Path $BundlePath)) {
  throw @"
avs-main.bundle not found.
Download it from the Cursor agent artifacts (avs-main.bundle), save to C:\Temp\avs-main.bundle,
then re-run this script.
"@
}
$BundlePath = (Resolve-Path $BundlePath).Path
Write-Host "Bundle: $BundlePath"
Write-Host "GitHub: $GitHubSsh"

if (Test-Path $StageDir) {
  $bak = "$StageDir.bak-$(Get-Date -Format yyyyMMddHHmmss)"
  Write-Warning "Moving existing $StageDir → $bak"
  Rename-Item $StageDir $bak
}

Write-Host "git clone from bundle → $StageDir"
git clone "$BundlePath" $StageDir
Push-Location $StageDir
try {
  git checkout $Branch
  git remote remove origin 2>$null
  git remote add origin $GitHubSsh
  if (-not $SkipPush) {
    Write-Host "Pushing to GitHub via SSH (may need --force because remote only has LICENSE)…"
    # Initial GitHub commit (LICENSE only) is unrelated history
    git push -u origin "${Branch}:$Branch" --force
  }
} finally {
  Pop-Location
}

if (-not $SkipApply) {
  $apply = Join-Path $StageDir "scripts\windows\APPLY-TO-D-AVS.ps1"
  $sync = Join-Path $StageDir "scripts\windows\git-sync-to-avs.ps1"
  if (Test-Path $apply) {
    & $apply -InstallRoot $InstallRoot
  } elseif (Test-Path $sync) {
    & $sync -SourceDir $StageDir -InstallRoot $InstallRoot
  } else {
    throw "APPLY/git-sync scripts missing inside bundle checkout — bundle may be incomplete."
  }
}

$startAll = Join-Path $InstallRoot "scripts\windows\start-all.ps1"
Write-Host ""
Write-Host "Done. GitHub + D:\\avs updated from cloud bundle."
Write-Host "Later updates (once GitHub has full tree):"
Write-Host "  git -C $StageDir pull origin $Branch"
Write-Host "  powershell -ExecutionPolicy Bypass -File $StageDir\scripts\windows\git-sync-to-avs.ps1 -SourceDir $StageDir"
Write-Host "Start: powershell -ExecutionPolicy Bypass -File `"$startAll`""
if ($StartAfter -and (Test-Path $startAll)) {
  & $startAll -InstallRoot $InstallRoot
}
