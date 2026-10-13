#!/usr/bin/env bash
# Start ComfyUI (if present) + LAVS backend + frontend.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "ERROR: .venv missing. Run scripts/linux/setup.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

HOST="${LAVS_HOST:-127.0.0.1}"
PORT="${LAVS_PORT:-18765}"
FRONT_PORT="${LAVS_FRONTEND_PORT:-18766}"
COMFY_URL="${LAVS_COMFYUI_URL:-http://127.0.0.1:8188}"
SKIP_COMFY="${LAVS_SKIP_COMFY:-0}"

mkdir -p data/{models,outputs,uploads,logs,db}
export PYTHONPATH="$ROOT/backend:${PYTHONPATH:-}"

PIDS=()
cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo "== LAVS start-all (Linux) =="
echo "API http://${HOST}:${PORT}  UI http://127.0.0.1:${FRONT_PORT}"
echo "Browser refresh does NOT reload Python — restart this script after git pull."

if [[ "$SKIP_COMFY" != "1" ]]; then
  for c in \
    "$ROOT/engines/ComfyUI" \
    "$ROOT/ComfyUI" \
    "${LAVS_COMFYUI_DIR:-}"
  do
    [[ -n "$c" && -f "$c/main.py" ]] || continue
    echo "Starting ComfyUI from $c"
    (
      cd "$c"
      if [[ -x .venv/bin/python ]]; then
        .venv/bin/python main.py --listen 127.0.0.1 --port 8188
      else
        python3 main.py --listen 127.0.0.1 --port 8188
      fi
    ) &
    PIDS+=($!)
    sleep 2
    break
  done
fi

echo "Starting backend…"
uvicorn app.main:app --app-dir backend --host "$HOST" --port "$PORT" &
PIDS+=($!)
sleep 1

echo "Starting frontend…"
(cd frontend && npm run dev -- --host 127.0.0.1 --port "$FRONT_PORT") &
PIDS+=($!)

echo "Comfy expected at $COMFY_URL (if installed)"
echo "Open http://127.0.0.1:${FRONT_PORT}"
wait
