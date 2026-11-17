# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=collect_data_files('mediapipe') + [('assets', 'assets')],
    hiddenimports=[
        'mediapipe',
        'mediapipe.python.solutions',
        'mediapipe.python.solutions.face_mesh',
        'mediapipe.calculators',
        'mediapipe.framework',
        'mediapipe.modules',
        'pushbullet',
        'cv2',
        'numpy',
        'google.protobuf',
    ] + collect_submodules('mediapipe'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DoomscrollBlocker',
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
    icon='app.ico' if os.path.exists('app.ico') else None
)