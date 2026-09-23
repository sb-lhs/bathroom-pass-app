#!/bin/bash
# One-command installer for hallpass-qt on Debian 12 (Surface Pro 1).
# No .deb download needed — builds the package from the tagged source on-device.
#
# Usage (on the Surface, one line):
#   curl -fsSL https://raw.githubusercontent.com/sb-lhs/bathroom-pass-app/v0.3.0/scripts/install_debian.sh | sudo bash -s -- 0.3.0
#
# Safe to re-run for upgrades: existing /etc/hallpass/config.json (admin
# password, thresholds, rosters) is never overwritten.
set -euo pipefail

VERSION="${1:-0.3.0}"
REPO="sb-lhs/bathroom-pass-app"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run with sudo." >&2
  exit 1
fi
export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y curl ca-certificates dpkg-dev

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
echo "Fetching hallpass-qt v$VERSION source…"
curl -fsSL "https://github.com/$REPO/archive/refs/tags/v$VERSION.tar.gz" -o "$work/src.tgz"
tar xzf "$work/src.tgz" -C "$work"
cd "$work/bathroom-pass-app-$VERSION"

echo "Building hallpass-qt_${VERSION}_amd64.deb…"
./scripts/build_deb.sh

echo "Installing (dependencies resolve from Debian repos)…"
apt-get install -y "./hallpass-qt_${VERSION}_amd64.deb"

echo
echo "Done. Launch with: hallpass-qt"
echo "First launch: Admin → set your admin password (first-run setup)."
