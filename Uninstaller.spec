
target = {
    "name":"Uninstall",
    "file":"Uninstaller.py",
    "icon":"VRCUtil.ico",
}
file = [
    ('.venv/Lib/site-packages/customtkinter/assets', 'customtkinter/assets'),
    ('VRCUtil.ico', '.')
]

#============================================

import pathlib
import shutil
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

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
)

exe = EXE(
    PYZ(
        a.pure,
        optimize=2,
        level=9,
    ),
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=target['name'],
    icon=[target['icon']],
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

distPath = pathlib.Path(DISTPATH)
sourcePath = distPath / f"{target['name']}.exe"
targetPath = distPath / "VRCUtil" / f"{target['name']}.exe"
targetPath.parent.mkdir(parents=True, exist_ok=True)
if targetPath.exists():
    targetPath.unlink()
shutil.move(str(sourcePath), str(targetPath))
