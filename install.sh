#!/usr/bin/env bash
# Add Clean Slate to your application menu. Re-run after moving the folder.
set -euo pipefail
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"

mkdir -p "$APPS" "$ICONS"
install -m 644 "$HERE/clean_slate/assets/icon.svg" "$ICONS/clean-slate.svg"
chmod +x "$HERE/run.sh"

cat > "$APPS/clean-slate.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Clean Slate
Comment=Track the habits you want to quit
Exec=$HERE/run.sh
Icon=clean-slate
Terminal=false
Categories=Utility;
StartupWMClass=clean-slate
EOF

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" >/dev/null 2>&1 || true

echo "Installed Clean Slate to $APPS/clean-slate.desktop"
echo "Launch it from your application menu, or run: $HERE/run.sh"
