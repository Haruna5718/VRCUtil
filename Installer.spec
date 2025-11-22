target = {
    "name": "VRCUtil-Installer",
    "file": "install.py",
    "icon": "VRCUtil.ico"
}
file = [
    ('.venv/Lib/site-packages/customtkinter', 'customtkinter'),
    ('dist/VRCUtil', 'data'),
    ('VRCUtil.ico', '.')
]

a = Analysis(
    [target['file']],
    pathex=[],
    binaries=[],
    datas=file,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

exe = EXE(
    PYZ(a.pure),
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=target['name'],
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
    icon=[target['icon']],
)
