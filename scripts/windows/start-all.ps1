#Requires -Version 5.1
<#
.SYNOPSIS
  Start ComfyUI + LAVS backend + frontend together (office D:\avs).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File D:\avs\scripts\windows\start-all.ps1
  powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-all.ps1 -WithSdxlWorker
#>
param(
  [string]$InstallRoot = "",
  [string]$ComfyListen = "127.0.0.1",
  [int]$ComfyPort = 8188,
  [string]$HostAddr = "",
  [int]$Port = 0,
  [int]$FrontPort = 0,
  [switch]$WithSdxlWorker,
  [switch]$SkipComfy,
  [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

# Resolve install root: explicit → script-relative repo → D:\avs
if (-not $InstallRoot) {
  $guess = Resolve-Path (Join-Path $PSScriptRoot "..\..") -ErrorAction SilentlyContinue
  if ($guess -and (Test-Path (Join-Path $guess "backend"))) {
    $InstallRoot = $guess.Path
  } else {
    $InstallRoot = "D:\avs"
  }
}
$InstallRoot = (Resolve-Path $InstallRoot).Path
Set-Location $InstallRoot

if (-not (Test-Path (Join-Path $InstallRoot ".venv\Scripts\uvicorn.exe"))) {
  throw ".venv missing under $InstallRoot. Run scripts\windows\setup.ps1 first."
}

# Load .env into this process (and child windows inherit via Start-Process -UseNewEnvironment:$false default)
if (Test-Path .env) {
  Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $pair = $_.Split('=', 2)
    if ($pair.Length -eq 2) {
      [System.Environment]::SetEnvironmentVariable($pair[0].Trim(), $pair[1].Trim(), "Process")
    }
  }
}

if (-not $HostAddr) { $HostAddr = if ($env:LAVS_HOST) { $env:LAVS_HOST } else { "127.0.0.1" } }
if ($Port -le 0) { $Port = if ($env:LAVS_PORT) { [int]$env:LAVS_PORT } else { 18765 } }
if ($FrontPort -le 0) { $FrontPort = if ($env:LAVS_FRONTEND_PORT) { [int]$env:LAVS_FRONTEND_PORT } else { 18766 } }

New-Item -ItemType Directory -Force -Path data\models, data\outputs, data\uploads, data\logs, data\db | Out-Null

Write-Host "== LAVS start-all =="
Write-Host "InstallRoot: $InstallRoot"
Write-Host "API:  http://${HostAddr}:${Port}"
Write-Host "UI:   http://127.0.0.1:${FrontPort}"
Write-Host "Note: Browser refresh does NOT reload Python. After update-avs.ps1, re-run this script."

$procs = @()

function Start-LavsWindow([string]$Title, [string]$Command) {
  $p = Start-Process -PassThru -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
    "`$Host.UI.RawUI.WindowTitle = '$Title'; Set-Location '$InstallRoot'; $Command"
  )
  Write-Host "  started: $Title (pid=$($p.Id))"
  return $p
}

# --- ComfyUI ---
if (-not $SkipComfy) {
  $comfyScript = Join-Path $InstallRoot "scripts\windows\start_comfyui.ps1"
  if (-not (Test-Path $comfyScript)) {
    Write-Warning "start_comfyui.ps1 missing — skip ComfyUI"
  } else {
    $procs += Start-LavsWindow "LAVS ComfyUI :$ComfyPort" (
      "& '$comfyScript' -InstallRoot '$InstallRoot' -Listen '$ComfyListen' -Port $ComfyPort"
    )
    Write-Host "Waiting briefly for ComfyUI…"
    Start-Sleep -Seconds 3
  }
} else {
  Write-Host "SkipComfy: not starting ComfyUI"
}

# --- Optional SDXL warm worker ---
if ($WithSdxlWorker) {
  $sdxlScript = Join-Path $InstallRoot "scripts\windows\start_sdxl_worker.ps1"
  if (Test-Path $sdxlScript) {
    $procs += Start-LavsWindow "LAVS SDXL worker" (
      "& '$sdxlScript' -InstallRoot '$InstallRoot'"
    )
  } else {
    Write-Warning "start_sdxl_worker.ps1 missing"
  }
}

# --- Backend ---
$env:PYTHONPATH = Join-Path $InstallRoot "backend"
$backendCmd = @"
`$env:PYTHONPATH = '$(Join-Path $InstallRoot 'backend')'
if (Test-Path .env) {
  Get-Content .env | ForEach-Object {
    if (`$_ -match '^\s*#' -or `$_ -match '^\s*`$') { return }
    `$pair = `$_.Split('=', 2)
    if (`$pair.Length -eq 2) {
      [System.Environment]::SetEnvironmentVariable(`$pair[0].Trim(), `$pair[1].Trim(), 'Process')
    }
  }
}
Write-Host 'Backend http://${HostAddr}:${Port} (Ctrl+C to stop)'
& '.\.venv\Scripts\uvicorn.exe' app.main:app --app-dir backend --host $HostAddr --port $Port
"@
$procs += Start-LavsWindow "LAVS API :$Port" $backendCmd

# --- Frontend ---
$frontCmd = @"
Set-Location '$(Join-Path $InstallRoot 'frontend')'
if (-not (Test-Path 'node_modules')) { npm install }
Write-Host 'Frontend http://127.0.0.1:${FrontPort}'
npm run dev -- --host 127.0.0.1 --port $FrontPort
"@
$procs += Start-LavsWindow "LAVS UI :$FrontPort" $frontCmd

Start-Sleep -Seconds 2
if (-not $NoBrowser) {
  try { Start-Process "http://127.0.0.1:${FrontPort}" } catch { }
}

Write-Host ""
Write-Host "All windows launched. Close each window (or Ctrl+C) to stop that service."
Write-Host "If Model Manager still shows unavailable: start ComfyUI + install weights; that is readiness, not a missing restart."
Write-Host "PIDs: $(($procs | ForEach-Object { $_.Id }) -join ', ')"
