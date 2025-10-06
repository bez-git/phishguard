#!/usr/bin/env bash
set -euxo pipefail

# Download portable git-lfs and unpack
LFS_VER="3.5.1"
URL="https://github.com/git-lfs/git-lfs/releases/download/v${LFS_VER}/git-lfs-linux-amd64-v${LFS_VER}.tar.gz"
curl -fsSL "$URL" -o /tmp/gitlfs.tgz

python - <<'PY'
import tarfile, os
os.makedirs('/tmp/git-lfs', exist_ok=True)
with tarfile.open('/tmp/gitlfs.tgz','r:gz') as t:
    t.extractall('/tmp/git-lfs')
PY

# Locate unpacked git-lfs and put it on PATH
LFS_DIR="$(dirname "$(find /tmp/git-lfs -type f -name git-lfs -print -quit)")"
export PATH="$LFS_DIR:$PATH"
git-lfs version || true

# Pull LFS objects, then install Python deps
git lfs pull
pip install -r requirements.txt