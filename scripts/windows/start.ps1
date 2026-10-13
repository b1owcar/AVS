$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

Write-Host "Tip: prefer scripts\windows\start-all.ps1 to also launch ComfyUI."
Write-Host "After update-avs.ps1, stop this process and start again — browser refresh does not reload the API."

if (-not (Test-Path .venv)) {
  throw ".venv missing. Run scripts\windows\setup.ps1 first."
}

if (Test-Path .env) {
  Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $pair = $_.Split('=', 2)
    if ($pair.Length -eq 2) {
      [System.Environment]::SetEnvironmentVariable($pair[0].Trim(), $pair[1].Trim(), "Process")
    }
  }
}

$HostAddr = if ($env:LAVS_HOST) { $env:LAVS_HOST } else { "127.0.0.1" }
$Port = if ($env:LAVS_PORT) { $env:LAVS_PORT } else { "18765" }
$FrontPort = if ($env:LAVS_FRONTEND_PORT) { $env:LAVS_FRONTEND_PORT } else { "18766" }

New-Item -ItemType Directory -Force -Path data\models, data\outputs, data\uploads, data\logs, data\db | Out-Null

if ($HostAddr -eq "0.0.0.0") {
  Write-Warning "Binding beyond localhost exposes this workstation on the network."
}

$env:PYTHONPATH = Join-Path $Root "backend"
Write-Host "Starting backend on http://${HostAddr}:${Port}"
$backend = Start-Process -PassThru -NoNewWindow -FilePath .\.venv\Scripts\uvicorn.exe -ArgumentList @(
  "app.main:app", "--app-dir", "backend", "--host", $HostAddr, "--port", $Port
)

try {
  Write-Host "Starting frontend on http://127.0.0.1:${FrontPort}"
  Set-Location frontend
  npm run dev -- --host 127.0.0.1 --port $FrontPort
}
finally {
  if ($backend -and -not $backend.HasExited) {
    Stop-Process -Id $backend.Id -Force
  }
}
