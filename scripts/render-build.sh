#!/usr/bin/env bash
set -euxo pipefail

echo "=== Python & pip info (before installs) ==="
which python || true
python -V || true
which pip || true
pip -V || true

# --- Install a portable git-lfs (no apt-get needed) ---
LFS_VER="3.5.1"
URL="https://github.com/git-lfs/git-lfs/releases/download/v${LFS_VER}/git-lfs-linux-amd64-v${LFS_VER}.tar.gz"
curl -fsSL "$URL" -o /tmp/gitlfs.tgz

mkdir -p /tmp/git-lfs
tar -xzf /tmp/gitlfs.tgz -C /tmp/git-lfs
# find the unpacked binary and put it on PATH
LFS_DIR="$(dirname "$(find /tmp/git-lfs -type f -name git-lfs -print -quit)")"
export PATH="$LFS_DIR:$PATH"
git-lfs version

# Ensure filters/hooks are active and pull all LFS objects
git lfs install
git lfs pull --exclude="" --include=""
git lfs ls-files || true

# --- Python deps ---
python -m pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

echo "Build complete."
