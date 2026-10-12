#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "== Local AI Vision Studio Linux setup =="
echo "Project root: $ROOT"
echo "This script installs MAIN BACKEND + FRONTEND deps only."
echo "It will NOT install PyTorch/CUDA/Diffusers or download model weights."

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found" >&2
  exit 1
fi

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt

(cd frontend && npm install)

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

mkdir -p data/{models,outputs,uploads,logs,db}
echo "Setup complete. Next: scripts/linux/start.sh"
echo "Before real inference on the target PC, run scripts/diagnose/check_environment.sh"
