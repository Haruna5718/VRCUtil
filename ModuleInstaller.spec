# -*- mode: python ; coding: utf-8 -*-

name = "ModuleInstaller"
icon = "app.ico"
file = "ModuleInstaller.py"

a = Analysis(
    [file],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)

exe = EXE(
    PYZ(a.pure),
    a.scripts,
    [],
    exclude_binaries=True,
    name=name,
    icon=[icon],
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=name,
)
