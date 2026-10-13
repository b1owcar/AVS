#!/usr/bin/env bash
# Scaffold env-trellis on Linux (preferred platform per upstream).
# Does NOT auto-clone microsoft/TRELLIS or download multi-GB weights.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALL_ROOT="${LAVS_INSTALL_ROOT:-$ROOT}"
ENV_DIR="$INSTALL_ROOT/envs/trellis"

echo "== Install TRELLIS env scaffold → $ENV_DIR =="
echo "Official: Linux + stated >=16GB VRAM. This script only scaffolds isolation."

mkdir -p "$ENV_DIR"
cp -f "$ROOT/envs/trellis/requirements.txt" "$ENV_DIR/"
cp -f "$ROOT/envs/trellis/worker_image_to_3d.py" "$ENV_DIR/"
cp -f "$ROOT/envs/trellis/trellis_runner.example.py" "$ENV_DIR/"

python3 -m venv "$ENV_DIR/.venv"
# shellcheck disable=SC1091
source "$ENV_DIR/.venv/bin/activate"
python -m pip install --upgrade pip
pip install -r "$ENV_DIR/requirements.txt"

PY="$ENV_DIR/.venv/bin/python"
ENV_FILE="$INSTALL_ROOT/.env"
if [[ ! -f "$ENV_FILE" && -f "$INSTALL_ROOT/.env.example" ]]; then
  cp "$INSTALL_ROOT/.env.example" "$ENV_FILE"
fi
if [[ -f "$ENV_FILE" ]]; then
  if grep -q '^LAVS_TRELLIS_PYTHON=' "$ENV_FILE"; then
    sed -i "s|^LAVS_TRELLIS_PYTHON=.*|LAVS_TRELLIS_PYTHON=$PY|" "$ENV_FILE"
  else
    echo "LAVS_TRELLIS_PYTHON=$PY" >> "$ENV_FILE"
  fi
fi

cat > "$ENV_DIR/NEXT_STEPS.txt" <<EOF
1. Clone microsoft/TRELLIS and install per upstream README into this venv.
2. Copy trellis_runner.example.py → trellis_runner.py and implement run_image_to_3d.
3. Confirm GPU VRAM (>=16GB stated upstream) before claiming support.
4. Restart LAVS; 3D Studio image-to-3d should flip ready when import works.
EOF

echo "Scaffold done. LAVS_TRELLIS_PYTHON=$PY"
echo "See $ENV_DIR/NEXT_STEPS.txt"
