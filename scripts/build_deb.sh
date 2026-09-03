#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Read version from pyproject.toml (single source of truth)
VERSION="$(grep -E '^version = ' "$ROOT/pyproject.toml" | sed -E 's/version = \"([^\"]+)\"/\1/')"
if [ -z "$VERSION" ]; then VERSION="0.2.0"; fi
PKG="$ROOT/hallpass-qt_${VERSION}_amd64"
rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN"
mkdir -p "$PKG/usr/bin"
mkdir -p "$PKG/usr/lib/hallpass"
mkdir -p "$PKG/usr/share/applications"
mkdir -p "$PKG/usr/share/hallpass/sounds"
mkdir -p "$PKG/etc/hallpass"
mkdir -p "$PKG/var/lib/hallpass/photos"

cp "$ROOT/DEBIAN/control" "$PKG/DEBIAN/control"
# Ensure Version in control matches pyproject at build time
if grep -q "^Version:" "$PKG/DEBIAN/control"; then
  sed -i "s/^Version:.*/Version: $VERSION/" "$PKG/DEBIAN/control"
fi
cp "$ROOT/DEBIAN/postinst" "$PKG/DEBIAN/postinst"
chmod 0755 "$PKG/DEBIAN/postinst"

# App code
cp -r "$ROOT/src/hallpass" "$PKG/usr/lib/hallpass/"
cp "$ROOT/src/main.py" "$PKG/usr/lib/hallpass/main.py"
cp "$ROOT/default_schedules.json" "$PKG/usr/share/hallpass/default_schedules.json"
cp "$ROOT/config.default.json" "$PKG/usr/share/hallpass/config.default.json"
cp "$ROOT/default_rosters.json" "$PKG/usr/share/hallpass/default_rosters.json"
cp "$ROOT/hallpass-qt.desktop" "$PKG/usr/share/applications/hallpass-qt.desktop"
# Sounds
if ls "$ROOT/sounds"/*.wav 1>/dev/null 2>&1; then cp "$ROOT/sounds"/*.wav "$PKG/usr/share/hallpass/sounds/"; else touch "$PKG/usr/share/hallpass/sounds/classic_chime.wav"; touch "$PKG/usr/share/hallpass/sounds/digital_alarm.wav"; touch "$PKG/usr/share/hallpass/sounds/subtle_bell.wav"; fi
if ls "$ROOT/sounds"/*.ogg 1>/dev/null 2>&1; then cp "$ROOT/sounds"/*.ogg "$PKG/usr/share/hallpass/sounds/"; fi

# Launcher
cat > "$PKG/usr/bin/hallpass-qt" <<'EOF'
#!/bin/bash
exec python3 /usr/lib/hallpass/main.py "$@"
EOF
chmod 0755 "$PKG/usr/bin/hallpass-qt"

# Build
dpkg-deb --build "$PKG"
echo "Built $PKG.deb"
ls -lh "$PKG.deb"
