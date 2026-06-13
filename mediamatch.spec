# PyInstaller spec file — works on all three platforms.
# The CI workflow invokes: pyinstaller mediamatch.spec
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# Single source of truth for the version embedded in the macOS app bundle.
# CI exports MEDIAMATCH_VERSION from the git tag; fall back to the Python
# package version when building locally without the env var set.
def _read_version():
    env = os.environ.get("MEDIAMATCH_VERSION", "").strip()
    if env:
        return env
    init = Path("src/mediamatch/__init__.py").read_text(encoding="utf-8")
    for line in init.splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "0.0.0"

APP_VERSION = _read_version()

# tmdbv3api data files (babelfish/guessit handled by hooks/hook-babelfish.py
# and hooks/hook-guessit.py which use collect_all + copy_metadata).
datas = [('assets', 'assets')]
datas += collect_data_files('tmdbv3api')
datas += copy_metadata('tmdbv3api')

hidden = [
    'mediamatch',
    'mediamatch.core',
    'mediamatch.ui',
    'mediamatch.utils',
    'tmdbv3api',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]

block_cipher = None

a = Analysis(
    ['src/mediamatch/main.py'],
    pathex=['.', 'src'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=['hooks/rthook-babelfish.py'],
    excludes=['tkinter', 'matplotlib', 'numpy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MediaMatch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico' if sys.platform == 'win32' else (
        'assets/icon.icns' if sys.platform == 'darwin' else 'assets/icon.png'
    ),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MediaMatch',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='MediaMatch.app',
        icon='assets/icon.icns',
        bundle_identifier='tech.montymail.mediamatch',
        info_plist={
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleVersion': APP_VERSION,
            'NSHighResolutionCapable': True,
        },
    )
