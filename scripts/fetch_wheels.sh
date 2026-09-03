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
$PIP download --dest "$DEST" "PySide6>=6.6" "opencv-python>=4.8" "piper-tts>=1.2"
echo "Done — $(ls "$DEST"/*.whl 2>/dev/null | wc -l) wheel(s):"
ls -lh "$DEST"/*.whl 2>/dev/null | awk '{print $9, $5}'
# Fetch bundled Piper voice (en_US-lessac-medium, General American, ~42MB)
VOICE_DIR="$ROOT/src/hallpass/voices"
mkdir -p "$VOICE_DIR"
if [ ! -f "$VOICE_DIR/en_US-lessac-medium.onnx" ]; then
  echo "Fetching Piper voice en_US-lessac-medium (42MB)..."
  curl -L -o "$VOICE_DIR/en_US-lessac-medium.onnx" "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" || wget -O "$VOICE_DIR/en_US-lessac-medium.onnx" "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" || echo "Voice download failed — run manually or check network"
fi
if [ ! -f "$VOICE_DIR/en_US-lessac-medium.onnx.json" ]; then
  curl -L -o "$VOICE_DIR/en_US-lessac-medium.onnx.json" "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" || wget -O "$VOICE_DIR/en_US-lessac-medium.onnx.json" "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" || echo "Voice json download failed"
fi
ls -lh "$VOICE_DIR"/en_US-lessac-medium.* 2>/dev/null | awk '{print $9, $5}' || echo "No voice files yet (will use fallback espeak-ng -v en-us)"
echo "Now re-run ./scripts/build_deb.sh to bundle wheels + voice into the .deb for offline install"
