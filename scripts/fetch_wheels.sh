#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/wheelhouse"
mkdir -p "$DEST"
echo "Fetching offline wheels for PySide6 + opencv-python into $DEST"
echo "Run this ON the Debian Surface (or any linux amd64 with same Python) for correct manylinux wheels"
if command -v pip3 >/dev/null 2>&1; then
  PIP=pip3
else
  PIP=pip
fi
$PIP download --dest "$DEST" "PySide6>=6.6" "opencv-python>=4.8"
echo "Done — $(ls "$DEST"/*.whl 2>/dev/null | wc -l) wheel(s):"
ls -lh "$DEST"/*.whl 2>/dev/null | awk '{print $9, $5}'
echo "Now re-run ./scripts/build_deb.sh to bundle them into the .deb for offline install"
