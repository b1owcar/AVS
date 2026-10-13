#Requires -Version 5.1
<#
.SYNOPSIS
  Start warm SDXL HTTP worker (keeps Diffusers pipeline loaded).
#>
param(
  [string]$InstallRoot = "D:\avs",
  [string]$HostAddr = "127.0.0.1",
  [int]$Port = 18767
)

$ErrorActionPreference = "Stop"

$py = Join-Path $InstallRoot "envs\image\.venv\Scripts\python.exe"
$script = Join-Path $InstallRoot "envs\image\worker_http.py"
$model = Join-Path $InstallRoot "data\models\sdxl-base-1.0"

if (-not (Test-Path $py)) { throw "Missing $py — run install-sdxl.ps1 first" }
if (-not (Test-Path $script)) {
  $alt = Join-Path $PSScriptRoot "..\..\envs\image\worker_http.py"
  if (Test-Path $alt) { $script = $alt } else { throw "Missing worker_http.py" }
}
if (-not (Test-Path $model)) { throw "Missing SDXL weights at $model — run install-sdxl.ps1 -DownloadWeights" }

# Ensure install tree has a copy of the worker
$destScript = Join-Path $InstallRoot "envs\image\worker_http.py"
if ($script -ne $destScript) {
  New-Item -ItemType Directory -Force -Path (Split-Path $destScript) | Out-Null
  Copy-Item $script $destScript -Force
  $script = $destScript
}

$url = "http://${HostAddr}:${Port}"
$envFile = Join-Path $InstallRoot ".env"
if (Test-Path $envFile) {
  $lines = Get-Content $envFile
  $found = $false
  $out = foreach ($line in $lines) {
    if ($line -match '^\s*LAVS_SDXL_WORKER_URL\s*=') {
      $found = $true
      "LAVS_SDXL_WORKER_URL=$url"
    } else { $line }
  }
  if (-not $found) { $out += "LAVS_SDXL_WORKER_URL=$url" }
  Set-Content -Path $envFile -Value $out -Encoding UTF8
}

Write-Host "Warm SDXL worker → $url (model=$model)"
& $py $script --host $HostAddr --port $Port --model-path $model
