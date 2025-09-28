# -*- mode: python ; coding: utf-8 -*-

import os
import inspect

# Optional app icon and splash screen
# Place your files at:
#  - LaunchMedia/app.ico        (Windows .ico for the EXE icon)
#  - LaunchMedia/splash.png     (Splash image shown at startup)
ICON_PATH = 'LaunchMedia/app.ico'
SPLASH_PATH = 'LaunchMedia/splash.png'
icon_file = ICON_PATH if os.path.exists(ICON_PATH) else None
splash_file = SPLASH_PATH if os.path.exists(SPLASH_PATH) else None


a = Analysis(
    ['installer.py'],
    pathex=[],
    binaries=[],
    datas=[('LaunchMedia', 'LaunchMedia'), ('media', 'media'), ('JSON', 'JSON'), ('mission_export_template.html', '.'), ('Insignia.ttf', '.'), ('PrivacyPol.txt', '.'), ('ToS.txt', '.'), ('sector-placeholder.png', '.'), ('SuperEarth.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Build kwargs and conditionally include icon/splash
_exe_sig = inspect.signature(EXE)
_supports_splash = 'splash' in _exe_sig.parameters
exe_kwargs = dict(
    name='MLHD2-Launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
if icon_file:
    exe_kwargs['icon'] = icon_file
if _supports_splash and splash_file:
    exe_kwargs['splash'] = splash_file

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    **exe_kwargs,
)
