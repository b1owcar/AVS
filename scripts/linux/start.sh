#!/usr/bin/env bash
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

mkdir -p data/{models,outputs,uploads,logs,db}

echo "Starting backend on http://${HOST}:${PORT}"
if [[ "$HOST" == "0.0.0.0" || "$HOST" == "::" ]]; then
  echo "WARNING: Binding beyond localhost exposes this workstation on the network."
fi

export PYTHONPATH="$ROOT/backend:${PYTHONPATH:-}"
uvicorn app.main:app --app-dir backend --host "$HOST" --port "$PORT" &
BACK_PID=$!

cleanup() {
  kill "$BACK_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 1
echo "Starting frontend on http://127.0.0.1:${FRONT_PORT}"
(cd frontend && npm run dev -- --host 127.0.0.1 --port "$FRONT_PORT")
