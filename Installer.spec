splash = "Splash.png"
target = {
    "name": "VRCUtil-Installer",
    "file": "install.py",
    "icon": "VRCUtil.ico"
}
file = [
    ('.venv/Lib/site-packages/customtkinter/assets', 'customtkinter/assets'),
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
    excludes=[
        'multiprocessing',
        'distutils',
        'asyncio',
        'email',
        'http',
    ],
    noarchive=False,
)

img = Splash(
    splash,
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
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
    img,
    img.binaries,
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
