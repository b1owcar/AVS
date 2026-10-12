# Read-only environment diagnosis. Does not install packages or download weights.
Write-Host "== LAVS environment check (read-only) =="
Write-Host "Timestamp: $(Get-Date -Format o)"
Write-Host "NOTE: Results describe THIS machine. Re-run on the target PC."

Write-Host "`n-- OS --"
[System.Environment]::OSVersion.VersionString
$env:PROCESSOR_ARCHITECTURE

Write-Host "`n-- Python --"
Get-Command python -ErrorAction SilentlyContinue | ForEach-Object { $_.Source }
python --version

Write-Host "`n-- Node / npm --"
Get-Command node -ErrorAction SilentlyContinue | ForEach-Object { $_.Source }
node --version
npm --version

Write-Host "`n-- FFmpeg --"
Get-Command ffmpeg -ErrorAction SilentlyContinue | ForEach-Object { $_.Source }
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) { ffmpeg -version | Select-Object -First 1 }

Write-Host "`n-- Memory / disk --"
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory
Get-PSDrive -PSProvider FileSystem | Format-Table Name, Used, Free

Write-Host "`n-- NVIDIA --"
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
  nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv
} else {
  Write-Host "nvidia-smi: MISSING"
}

Write-Host "`n-- PyTorch CUDA (optional) --"
python -c "import torch; print(torch.__version__, torch.cuda.is_available())" 2>$null
if (-not $?) { Write-Host "torch probe: NOT RUN / unavailable" }

Write-Host "`nDone. Use PASS / SIMULATED / NOT RUN / PENDING TARGET HARDWARE / FAILED labels."
