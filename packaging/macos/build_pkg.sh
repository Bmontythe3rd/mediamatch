#!/usr/bin/env bash
# Build a macOS .pkg installer from the PyInstaller output.
# Run from the repo root after: pyinstaller mediamatch.spec

set -euo pipefail

# Version is supplied by CI via MEDIAMATCH_VERSION; fall back to the
# Python package version when invoked manually.
if [ -n "${MEDIAMATCH_VERSION:-}" ]; then
    VERSION="$MEDIAMATCH_VERSION"
else
    VERSION="$(grep -E '^__version__' src/mediamatch/__init__.py \
        | sed -E 's/.*"([^"]+)".*/\1/')"
fi
APP="dist/MediaMatch.app"
PKG_DIR="dist/pkg_root/Applications"
COMPONENT_PKG="dist/MediaMatch_component.pkg"
OUTPUT_PKG="dist/MediaMatch-${VERSION}.pkg"
IDENTIFIER="tech.montymail.mediamatch"

mkdir -p "$PKG_DIR"
cp -R "$APP" "$PKG_DIR/"

pkgbuild \
    --root "dist/pkg_root" \
    --identifier "$IDENTIFIER" \
    --version "$VERSION" \
    --install-location "/" \
    "$COMPONENT_PKG"

productbuild \
    --distribution "packaging/macos/distribution.xml" \
    --resources "packaging/macos/resources" \
    --package-path "dist" \
    "$OUTPUT_PKG"

echo "Built: $OUTPUT_PKG"
