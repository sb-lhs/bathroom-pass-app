#!/bin/bash
# Surface Pro 1 — verify UVC cameras are ready for hallpass-qt
# Run on Debian as the kiosk user before launching the app

set -e
echo "=== 1. Verify Hardware Detection ==="
echo "USB bus:"
lsusb | grep -i -E "camera|video|omnivision" || echo "No camera string in lsusb — check lsusb alone:"
lsusb | head -20

echo ""
echo "Installing / checking v4l-utils..."
if ! command -v v4l2-ctl >/dev/null 2>&1; then
  sudo apt update && sudo apt install -y v4l-utils
fi

echo ""
echo "Video devices (expect /dev/video0 front + /dev/video1 rear on SP1):"
v4l2-ctl --list-devices || echo "v4l2-ctl failed — is uvcvideo loaded?"
ls -l /dev/video* 2>&1 || echo "No /dev/video* nodes"

echo ""
echo "=== 2. Ensure uvcvideo module ==="
lsmod | grep uvcvideo || echo "uvcvideo not loaded — loading..."
if ! lsmod | grep -q uvcvideo; then
  sudo modprobe uvcvideo || echo "modprobe failed"
  echo "uvcvideo" | sudo tee -a /etc/modules >/dev/null
  echo "Added uvcvideo to /etc/modules"
else
  echo "uvcvideo already loaded"
fi

echo ""
echo "=== 3. Permissions (video group) ==="
echo "Current user: $USER groups: $(groups)"
if groups | grep -q "\bvideo\b"; then
  echo "OK — user is in video group"
else
  echo "Adding $USER to video group..."
  sudo usermod -aG video $USER
  echo "Added. Run 'newgrp video' or reboot to apply."
fi
echo "Permissions on nodes:"
ls -l /dev/video* 2>&1 | head -10

echo ""
echo "=== 4. Test capture ==="
if ! command -v ffmpeg >/dev/null 2>&1; then
  sudo apt install -y ffmpeg
fi
echo "Capturing test_snapshot.jpg from /dev/video0 (front)..."
if ffmpeg -y -f v4l2 -i /dev/video0 -vframes 1 test_snapshot.jpg 2>&1 | tail -5; then
  if [ -f test_snapshot.jpg ]; then
    ls -lh test_snapshot.jpg
    echo "SUCCESS — camera ready. hallpass-qt will use index 0 (front) at 640x480 via V4L2."
  fi
else
  echo "ffmpeg capture failed — try /dev/video1:"
  ffmpeg -y -f v4l2 -i /dev/video1 -vframes 1 test_snapshot.jpg 2>&1 | tail -5 || echo "Both failed — check dmesg | grep uvc"
fi

echo ""
echo "Tip: hallpass-qt keeps VideoCapture(0, CAP_V4L2) open at 640x480 for <100ms silent shots."
