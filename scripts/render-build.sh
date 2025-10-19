#!/usr/bin/env bash
set -euxo pipefail

# Install Git LFS (Render build image has apt-get)
if ! command -v git-lfs >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends git-lfs
fi

# Make sure LFS filters are active and pull actual binary blobs
git lfs install
git lfs pull --exclude="" --include=""   # force full LFS fetch

# Python deps
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "Build complete."
