#!/usr/bin/env bash
set -euxo pipefail

# Download a portable git-lfs, extract to /tmp, and use it without installing system-wide
LFS_VER="3.5.1"
URL="https://github.com/git-lfs/git-lfs/releases/download/v${LFS_VER}/git-lfs-linux-amd64-v${LFS_VER}.tar.gz"
curl -sL "$URL" -o /tmp/gitlfs.tgz

python - <<'PY'
import tarfile, os
os.makedirs('/tmp/git-lfs', exist_ok=True)
with tarfile.open('/tmp/gitlfs.tgz','r:gz') as t:
    t.extractall('/tmp/git-lfs')
PY

# Put the portable binary on PATH for this build step only
export PATH="/tmp/git-lfs:$PATH"
/tmp/git-lfs/git-lfs version || true

# Pull LFS objects, then install Python deps
git lfs pull
pip install -r requirements.txt
