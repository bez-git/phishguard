#!/usr/bin/env bash
set -euxo pipefail

# Try to install git-lfs via apt; if not available, fall back to portable tarball.
if command -v apt-get >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends git-lfs
  git lfs version
else
  # Portable fallback (similar to what you had)
  LFS_VER="3.5.1"
  URL="https://github.com/git-lfs/git-lfs/releases/download/v${LFS_VER}/git-lfs-linux-amd64-v${LFS_VER}.tar.gz"
  curl -fsSL "$URL" -o /tmp/gitlfs.tgz

  python - <<'PY'
import tarfile, os
os.makedirs('/tmp/git-lfs', exist_ok=True)
with tarfile.open('/tmp/gitlfs.tgz','r:gz') as t:
    t.extractall('/tmp/git-lfs')
PY

  LFS_DIR="$(dirname "$(find /tmp/git-lfs -type f -name git-lfs -print -quit)")"
  export PATH="$LFS_DIR:$PATH"
  git-lfs version || true
fi

# Ensure filters/hooks are set up for this environment
git lfs install

# Force-fetch all LFS objects (include/exclude empty strings == fetch everything)
git lfs pull --exclude="" --include=""

# Python deps
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "Build complete."
