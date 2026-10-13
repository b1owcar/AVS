#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALL_ROOT="${LAVS_INSTALL_ROOT:-$ROOT}"
ENV_DIR="$INSTALL_ROOT/envs/pose"
echo "== Install pose env → $ENV_DIR =="
mkdir -p "$ENV_DIR"
cp -f "$ROOT/envs/pose/requirements.txt" "$ENV_DIR/"
cp -f "$ROOT/envs/pose/worker_pose.py" "$ENV_DIR/"
python3 -m venv "$ENV_DIR/.venv"
# shellcheck disable=SC1091
source "$ENV_DIR/.venv/bin/activate"
pip install -U pip
pip install -r "$ENV_DIR/requirements.txt"
PY="$ENV_DIR/.venv/bin/python"
ENV_FILE="$INSTALL_ROOT/.env"
[[ -f "$ENV_FILE" ]] || cp "$INSTALL_ROOT/.env.example" "$ENV_FILE"
if grep -q '^LAVS_POSE_PYTHON=' "$ENV_FILE"; then
  sed -i "s|^LAVS_POSE_PYTHON=.*|LAVS_POSE_PYTHON=$PY|" "$ENV_FILE"
else
  echo "LAVS_POSE_PYTHON=$PY" >> "$ENV_FILE"
fi
echo "Done. LAVS_POSE_PYTHON=$PY"
