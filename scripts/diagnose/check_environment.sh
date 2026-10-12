#!/usr/bin/env bash
# Read-only environment diagnosis. Does not install packages or download weights.
set -euo pipefail

echo "== LAVS environment check (read-only) =="
echo "Timestamp: $(date -Is)"
echo "NOTE: Results describe THIS machine. Target PC checks must be re-run there."
echo

echo "-- OS --"
uname -a || true
echo

echo "-- Python --"
command -v python3 && python3 --version || echo "python3: MISSING"
echo

echo "-- Node / npm --"
command -v node && node --version || echo "node: MISSING"
command -v npm && npm --version || echo "npm: MISSING"
echo

echo "-- FFmpeg --"
command -v ffmpeg && ffmpeg -version | head -1 || echo "ffmpeg: MISSING"
echo

echo "-- Memory / disk --"
free -h 2>/dev/null || true
df -h . | tail -1
echo

echo "-- NVIDIA --"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv
else
  echo "nvidia-smi: MISSING (GPU probe degraded)"
fi
echo

echo "-- PyTorch CUDA (optional; may be absent in remote-dev) --"
python3 - <<'PY' || true
try:
    import torch
    print("torch", torch.__version__)
    print("cuda_available", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("device", torch.cuda.get_device_name(0))
        print("vram_total_mb", round(torch.cuda.get_device_properties(0).total_memory / 1024**2))
except Exception as e:
    print("torch probe: NOT RUN / unavailable:", e)
PY

echo
echo "-- ComfyUI URL reachability (default) --"
URL="${LAVS_COMFYUI_URL:-http://127.0.0.1:8188}"
if command -v curl >/dev/null 2>&1; then
  curl -sS -m 3 "$URL/system_stats" >/dev/null && echo "ComfyUI reachable at $URL" || echo "ComfyUI not reachable at $URL"
else
  echo "curl missing; skip"
fi

echo
echo "Done. Classification reminder:"
echo "  PASS / SIMULATED / NOT RUN / PENDING TARGET HARDWARE / FAILED"
