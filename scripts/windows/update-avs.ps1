#Requires -Version 5.1
<#
.SYNOPSIS
  Pull latest LAVS code into D:\avs without wiping data/engines/venvs.

  Cloud agents cannot write D:\avs. New files (e.g. start-all.ps1) only appear
  after you run this script (or git pull) on the office PC.

.EXAMPLE
  # If D:\avs is already a git clone of this repo:
  powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\update-avs.ps1 -GitPull

  # From a fresh zip/checkout:
  powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\update-avs.ps1 -SourceDir "C:\Temp\lavs-fresh"

  # Clone remote into a temp dir then robocopy:
  powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\update-avs.ps1 -GitUrl "https://..."
#>
param(
  [string]$InstallRoot = "D:\avs",
  [string]$SourceDir = "",
  [string]$GitUrl = "",
  [switch]$GitPull,
  [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $InstallRoot)) { throw "InstallRoot missing: $InstallRoot" }

$usedGitPull = $false

if ($GitPull) {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git required for -GitPull" }
  $gitDir = Join-Path $InstallRoot ".git"
  if (-not (Test-Path $gitDir)) {
    throw @"
$InstallRoot is not a git checkout (no .git). Options:
  1) Clone the repo elsewhere, then: -SourceDir <clone>
  2) Or: -GitUrl <remote-url>  (clones to TEMP then robocopies into $InstallRoot)
"@
  }
  Push-Location $InstallRoot
  try {
    Write-Host "git fetch + checkout $Branch in $InstallRoot"
    git fetch origin $Branch
    git checkout $Branch
    git pull origin $Branch
  } finally {
    Pop-Location
  }
  $usedGitPull = $true
  $SourceDir = $InstallRoot
}

if ($GitUrl -and -not $usedGitPull) {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git required for -GitUrl" }
  $tmp = Join-Path $env:TEMP ("lavs-update-" + [guid]::NewGuid().ToString("n"))
  Write-Host "git clone --depth 1 -b $Branch $GitUrl → $tmp"
  git clone --depth 1 --branch $Branch $GitUrl $tmp
  $SourceDir = $tmp
}

if (-not $SourceDir) {
  throw @"
Provide one of:
  -GitPull          (when $InstallRoot is already a git clone)
  -SourceDir PATH   (fresh checkout / zip extract)
  -GitUrl URL       (clone then robocopy into $InstallRoot)
Cloud agent commits do NOT land on D:\avs until you sync.
"@
}

$SourceDir = (Resolve-Path $SourceDir).Path

if (-not $usedGitPull) {
  Write-Host "Updating $InstallRoot from $SourceDir (preserving data, engines, envs, .venv)"

  $roboArgs = @(
    $SourceDir, $InstallRoot,
    "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:1", "/W:1",
    "/XD", ".venv", "node_modules", "dist", ".git", "agent-tools",
    "engines", "data", "outputs", "uploads", "logs", "db", "external"
  )
  # Also avoid wiping isolated envs under InstallRoot\envs\*\.venv by excluding .venv name globally
  $rc = Start-Process -FilePath "robocopy.exe" -ArgumentList $roboArgs -Wait -PassThru -NoNewWindow
  if ($rc.ExitCode -ge 8) { throw "robocopy failed: $($rc.ExitCode)" }
}

# Ensure worker scripts / new envs land under InstallRoot
function Copy-TreeNoVenv([string]$From, [string]$To) {
  if (-not (Test-Path $From)) { return }
  New-Item -ItemType Directory -Force -Path $To | Out-Null
  Get-ChildItem $From -Force | Where-Object { $_.Name -ne ".venv" } | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $To $_.Name) -Recurse -Force
  }
}

$repoImage = Join-Path $SourceDir "envs\image\worker_http.py"
$destImage = Join-Path $InstallRoot "envs\image\worker_http.py"
if (Test-Path $repoImage) {
  New-Item -ItemType Directory -Force -Path (Split-Path $destImage) | Out-Null
  Copy-Item $repoImage $destImage -Force
}
Copy-TreeNoVenv (Join-Path $SourceDir "envs\pose") (Join-Path $InstallRoot "envs\pose")
Copy-TreeNoVenv (Join-Path $SourceDir "envs\motion") (Join-Path $InstallRoot "envs\motion")
Copy-TreeNoVenv (Join-Path $SourceDir "envs\trellis") (Join-Path $InstallRoot "envs\trellis")

# Force-copy critical scripts even if robocopy skipped somehow
$scriptPairs = @(
  @("scripts\windows\start-all.ps1", "scripts\windows\start-all.ps1"),
  @("scripts\windows\start_comfyui.ps1", "scripts\windows\start_comfyui.ps1"),
  @("scripts\windows\start_sdxl_worker.ps1", "scripts\windows\start_sdxl_worker.ps1"),
  @("scripts\windows\install-pose.ps1", "scripts\windows\install-pose.ps1"),
  @("scripts\windows\install-motion.ps1", "scripts\windows\install-motion.ps1"),
  @("scripts\windows\update-avs.ps1", "scripts\windows\update-avs.ps1")
)
foreach ($pair in $scriptPairs) {
  $src = Join-Path $SourceDir $pair[0]
  $dst = Join-Path $InstallRoot $pair[1]
  if (Test-Path $src) {
    New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
    Copy-Item $src $dst -Force
  }
}

$startAll = Join-Path $InstallRoot "scripts\windows\start-all.ps1"
Write-Host ""
Write-Host "Sync done."
if (Test-Path $startAll) {
  Write-Host "OK: start-all.ps1 is now at $startAll"
} else {
  Write-Warning "start-all.ps1 still missing under $InstallRoot — SourceDir may be an old checkout."
}

Write-Host "If package.json / requirements changed:"
Write-Host "  cd $InstallRoot\frontend; npm install"
Write-Host "  & $InstallRoot\.venv\Scripts\pip.exe install -r $InstallRoot\backend\requirements.txt"
Write-Host "Restart everything:"
Write-Host "  powershell -ExecutionPolicy Bypass -File $startAll"
