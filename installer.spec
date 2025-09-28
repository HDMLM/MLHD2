# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.building.datastruct import Tree
import os
import inspect

block_cipher = None


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
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Bundle project resource folders
a.datas += Tree('LaunchMedia', prefix='LaunchMedia')
# If you need JSON at runtime, uncomment the next line:
# a.datas += Tree('JSON', prefix='JSON')

# Bundle individual files used at runtime (uncomment as needed)
# a.datas += [
#     ('mission_export_template.html', '.', 'DATA'),
#     ('Insignia.ttf', '.', 'DATA'),  # we already ship this inside LaunchMedia/ by default
# ]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    console=False,  # windowed
    disable_windowed_traceback=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
if icon_file:
    exe_kwargs['icon'] = icon_file
if _supports_splash and splash_file:
    exe_kwargs['splash'] = splash_file
version_file_path = 'file_version_info.txt'
if os.path.exists(version_file_path):
    exe_kwargs['version'] = version_file_path

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    **exe_kwargs,
)
