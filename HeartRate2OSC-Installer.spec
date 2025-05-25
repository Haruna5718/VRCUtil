# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ModuleInstaller.py'],
    pathex=[],
    binaries=[],
    datas=[('FrontEnd/dist/favicon.ico', '.'), ('build/HeartRate2OSC', 'data/HeartRate2OSC')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HeartRate2OSC-Installer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['FrontEnd\\dist\\favicon.ico'],
)
