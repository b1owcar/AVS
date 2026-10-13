#!/usr/bin/env bash
# Create isolated env-motion for Phase 5 stage-2 transfer (weights still user-supplied).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALL_ROOT="${LAVS_INSTALL_ROOT:-$ROOT}"
ENV_DIR="$INSTALL_ROOT/envs/motion"

echo "== Install motion env → $ENV_DIR =="
echo "This does NOT download transfer model weights."

mkdir -p "$ENV_DIR"
cp -f "$ROOT/envs/motion/requirements.txt" "$ENV_DIR/"
cp -f "$ROOT/envs/motion/worker_transfer.py" "$ENV_DIR/"
cp -f "$ROOT/envs/motion/run_transfer.example.py" "$ENV_DIR/"
cp -f "$ROOT/envs/motion/backend.example.json" "$ENV_DIR/"

python3 -m venv "$ENV_DIR/.venv"
# shellcheck disable=SC1091
source "$ENV_DIR/.venv/bin/activate"
python -m pip install --upgrade pip
pip install -r "$ENV_DIR/requirements.txt"
# optional ComfyUI backend
pip install "httpx>=0.27,<1.0" || true

PY="$ENV_DIR/.venv/bin/python"
WEIGHTS="$INSTALL_ROOT/data/models/motion-transfer"
mkdir -p "$WEIGHTS"
cp -f "$ROOT/envs/motion/run_transfer.example.py" "$WEIGHTS/run_transfer.example.py"
cp -f "$ROOT/envs/motion/backend.example.json" "$WEIGHTS/backend.example.json"
cat > "$WEIGHTS/README.txt" <<EOF
Place a Stage-2 motion-transfer backend here:
  1) Copy run_transfer.example.py → run_transfer.py and implement run_transfer(), OR
  2) Add backend.json (see backend.example.json) for external_script / comfyui.
README alone does NOT make transfer "ready".
Skeleton compose preview is NOT motion transfer.
EOF

ENV_FILE="$INSTALL_ROOT/.env"
if [[ ! -f "$ENV_FILE" && -f "$INSTALL_ROOT/.env.example" ]]; then
  cp "$INSTALL_ROOT/.env.example" "$ENV_FILE"
fi
if [[ -f "$ENV_FILE" ]]; then
  if grep -q '^LAVS_MOTION_PYTHON=' "$ENV_FILE"; then
    sed -i "s|^LAVS_MOTION_PYTHON=.*|LAVS_MOTION_PYTHON=$PY|" "$ENV_FILE"
  else
    echo "LAVS_MOTION_PYTHON=$PY" >> "$ENV_FILE"
  fi
fi

echo "Done. LAVS_MOTION_PYTHON=$PY"
echo "Wire backend under $WEIGHTS then restart LAVS."
