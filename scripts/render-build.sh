#!/usr/bin/env bash
set -euxo pipefail

echo "=== Python & pip info (before installs) ==="
which python || true
python -V || true
which pip || true
pip -V || true

# Install Git LFS in Render build env
if ! command -v git-lfs >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends git-lfs
fi

git lfs install
# force a real fetch of all LFS artifacts (model files)
git lfs pull --exclude="" --include=""

# Install deps into Render’s venv (pip already points to it)
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Verify Flask is installed into this python ==="
python - <<'PY'
import sys
print("Python exe:", sys.executable)
import flask
print("Flask OK, version:", flask.__version__)
PY

echo "Build complete."
