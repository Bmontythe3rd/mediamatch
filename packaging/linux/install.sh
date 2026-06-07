#!/usr/bin/env bash
# Install MediaMatch from the extracted tar.gz to ~/.local
# Usage: bash install.sh

set -euo pipefail

INSTALL_DIR="$HOME/.local/lib/mediamatch"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing MediaMatch to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"

cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"

# Launcher wrapper
cat > "$BIN_DIR/mediamatch" << WRAPPER
#!/usr/bin/env bash
exec "$INSTALL_DIR/MediaMatch" "\$@"
WRAPPER
chmod +x "$BIN_DIR/mediamatch"

# Desktop entry
cat > "$DESKTOP_DIR/mediamatch.desktop" << DESKTOP
[Desktop Entry]
Name=MediaMatch
Comment=Rename media folders to Plex/Jellyfin naming conventions
Exec=$INSTALL_DIR/MediaMatch
Icon=$ICON_DIR/mediamatch.png
Type=Application
Categories=AudioVideo;
DESKTOP

# Icon
if [ -f "$SCRIPT_DIR/../assets/icon.png" ]; then
    cp "$SCRIPT_DIR/../assets/icon.png" "$ICON_DIR/mediamatch.png"
fi

echo ""
echo "Done! Run 'mediamatch' to launch (make sure ~/.local/bin is in your PATH)."
echo "Or run directly: $INSTALL_DIR/MediaMatch"
