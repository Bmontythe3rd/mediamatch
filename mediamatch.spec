# PyInstaller spec file — works on all three platforms.
# The CI workflow invokes: pyinstaller mediamatch.spec
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/mediamatch/main.py'],
    pathex=['.', 'src'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'mediamatch',
        'mediamatch.core',
        'mediamatch.ui',
        'mediamatch.utils',
        'guessit',
        'tmdbv3api',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
        },
    )
