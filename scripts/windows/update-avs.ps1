#Requires -Version 5.1
<#
.SYNOPSIS
  Pull latest LAVS code into D:\avs without wiping data/engines/venvs.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\update-avs.ps1 -SourceDir "C:\Temp\lavs-fresh"
#>
param(
  [string]$InstallRoot = "D:\avs",
  [string]$SourceDir = "",
  [string]$GitUrl = ""
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $InstallRoot)) { throw "InstallRoot missing: $InstallRoot" }

if ($GitUrl) {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git required for -GitUrl" }
  $tmp = Join-Path $env:TEMP ("lavs-update-" + [guid]::NewGuid().ToString("n"))
  git clone --depth 1 $GitUrl $tmp
  $SourceDir = $tmp
}

if (-not $SourceDir) {
  throw "Provide -SourceDir (fresh checkout/zip extract) or -GitUrl"
}

$SourceDir = (Resolve-Path $SourceDir).Path
Write-Host "Updating $InstallRoot from $SourceDir (preserving data, engines, envs, .venv)"

$roboArgs = @(
  $SourceDir, $InstallRoot,
  "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:1", "/W:1",
  "/XD", ".venv", "node_modules", "dist", ".git", "agent-tools",
  "engines", "data", "outputs", "uploads", "logs", "db"
)
# Also avoid wiping isolated envs under InstallRoot\envs\*\.venv by excluding .venv name globally
$rc = Start-Process -FilePath "robocopy.exe" -ArgumentList $roboArgs -Wait -PassThru -NoNewWindow
if ($rc.ExitCode -ge 8) { throw "robocopy failed: $($rc.ExitCode)" }

Write-Host "Sync done. Reinstall frontend deps if package.json changed:"
Write-Host "  cd $InstallRoot\frontend; npm install"
Write-Host "Refresh backend deps:"
Write-Host "  & $InstallRoot\.venv\Scripts\pip.exe install -r $InstallRoot\backend\requirements.txt"
Write-Host "Then restart: scripts\windows\start.ps1"
Write-Host "Optional Phase2: scripts\windows\install-phase2.ps1"
Write-Host "Optional Phase4 Wan: scripts\windows\start_comfyui.ps1"
Write-Host "Optional SDXL warm: scripts\windows\start_sdxl_worker.ps1"
Write-Host "Optional Phase5 pose: scripts\windows\install-pose.ps1"
# Ensure worker scripts land under envs even if only repo root was synced earlier
$repoImage = Join-Path $SourceDir "envs\image\worker_http.py"
$destImage = Join-Path $InstallRoot "envs\image\worker_http.py"
if (Test-Path $repoImage) {
  New-Item -ItemType Directory -Force -Path (Split-Path $destImage) | Out-Null
  Copy-Item $repoImage $destImage -Force
}
$repoPose = Join-Path $SourceDir "envs\pose"
$destPose = Join-Path $InstallRoot "envs\pose"
if (Test-Path $repoPose) {
  New-Item -ItemType Directory -Force -Path $destPose | Out-Null
  Copy-Item (Join-Path $repoPose "*") $destPose -Force -Exclude ".venv"
}
