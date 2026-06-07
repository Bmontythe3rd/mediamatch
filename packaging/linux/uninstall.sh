#!/usr/bin/env bash
# Uninstall MediaMatch from Linux.
# Handles tar.gz installs, pip/source installs, AppImages, and config data.
# Usage:
#   bash uninstall.sh          # preview what will be removed (dry run)
#   bash uninstall.sh --yes    # actually remove everything

set -euo pipefail

YES=false
for arg in "$@"; do
    [[ "$arg" == "--yes" ]] && YES=true
done

RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[1;33m'
NC='\033[0m'

found=()
not_found=()

check() {
    local path="$1"
    # Skip duplicates
    for existing in "${found[@]+"${found[@]}"}"; do
        [[ "$existing" == "$path" ]] && return
    done
    if [ -e "$path" ]; then
        found+=("$path")
    else
        not_found+=("$path")
    fi
}

remove() {
    local path="$1"
    if [ -d "$path" ]; then
        rm -rf "$path"
    else
        rm -f "$path"
    fi
}

echo ""
echo "MediaMatch Uninstaller"
echo "======================"
echo ""

# ── tar.gz install paths ─────────────────────────────────────────────────────
check "$HOME/.local/lib/mediamatch"
check "$HOME/.local/bin/mediamatch"
check "$HOME/.local/share/applications/mediamatch.desktop"
check "$HOME/.local/share/icons/hicolor/256x256/apps/mediamatch.png"

# ── pip / source install (mediamatch-gui entry point) ────────────────────────
check "$HOME/.local/bin/mediamatch-gui"

# Locate pip-installed package in any Python version's site-packages
while IFS= read -r -d '' pkg; do
    check "$pkg"
done < <(find "$HOME/.local/lib" -maxdepth 3 \
    \( -name "mediamatch" -type d \
    -o -name "mediamatch-*.dist-info" -type d \
    -o -name "mediamatch*.egg-link" \) \
    -print0 2>/dev/null)

# ── AppImage files (common user locations) ───────────────────────────────────
while IFS= read -r -d '' appimg; do
    check "$appimg"
done < <(find "$HOME" \
    -maxdepth 4 \
    \( -path "$HOME/.cache" -o -path "$HOME/.local/share/flatpak" \) -prune \
    -o -name "MediaMatch*.AppImage" -print0 2>/dev/null)

# ── squashfs-root extracted AppImage ─────────────────────────────────────────
while IFS= read -r -d '' sqfs; do
    check "$sqfs"
done < <(find "$HOME" \
    -maxdepth 4 \
    -name "squashfs-root" -type d \
    -print0 2>/dev/null)

# ── Config / data ─────────────────────────────────────────────────────────────
check "$HOME/.config/MediaMatch"

# ─────────────────────────────────────────────────────────────────────────────

if [ ${#found[@]} -eq 0 ]; then
    echo -e "${GRN}Nothing to remove — MediaMatch does not appear to be installed.${NC}"
    echo ""
    exit 0
fi

echo -e "${YEL}The following items will be removed:${NC}"
for path in "${found[@]}"; do
    echo "  $path"
done
echo ""

if [ ${#not_found[@]} -gt 0 ]; then
    echo "Already absent (skipping):"
    for path in "${not_found[@]}"; do
        echo "  $path"
    done
    echo ""
fi

if [ "$YES" = false ]; then
    echo -e "${YEL}Dry run — nothing was deleted.${NC}"
    echo "Re-run with --yes to actually remove the items above:"
    echo "  bash uninstall.sh --yes"
    echo ""
    exit 0
fi

echo "Removing..."
for path in "${found[@]}"; do
    remove "$path"
    echo -e "  ${RED}removed${NC}  $path"
done

# Refresh desktop icon cache if the tool is available
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

echo ""
echo -e "${GRN}MediaMatch has been completely removed.${NC}"
echo ""
