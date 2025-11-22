name = "VRCUtil"

target = [
    {
        "name":"VRCUtil",
        "file":"VRCUtil.py",
        "icon":"VRCUtil.ico",
    },
    {
        "name":"ModuleInstaller",
        "file":"ModuleInstaller.py",
        "icon":"VRCUtil.ico",
    },
    {
        "name":"ServiceWorker",
        "file":"ServiceWorker.py",
        "icon":"VRCUtil.ico",
    }
]

file = [
    "manifest.vrmanifest",
    "manifest.vrmanifest",
    "Dashboard.xaml",
    "Settings.xaml",
    "VRCUtil.ico",
]

data = []
binary = [
    (".venv\Scripts\pip.exe",".")
]
module = []

collectAllModule = [
    "pip",
    "customtkinter",
    "pywebwinui3",
]

#============================================

import sys
import pathlib
import shutil
import threading
from PyInstaller.utils.hooks import collect_all
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

datas = []

def collect(moduleName):
    global data, binary, module
    collectData = collect_all(moduleName, include_py_files=False)
    data += collectData[0]
    binary += collectData[1]
    module += collectData[2]

def runThreadWorks(iterable, callback):
    threads:list[threading.Thread] = []
    for item in iterable:
        thread = threading.Thread(target=callback,args=(item,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

def buildExe(info:dict):
    global datas
    a = Analysis(
        [info.get("file")],
        pathex=[],
        binaries=binary,
        datas=data,
        hiddenimports=module,
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
        name=info.get("name"),
        icon=[info.get("icon")],
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
    datas+=[exe,a.binaries,a.datas]

collectAllModule += list(sys.stdlib_module_names)
collectAllModule.remove("antigravity")
collectAllModule.remove("this")

runThreadWorks(collectAllModule, collect)

runThreadWorks(target, buildExe)

result = COLLECT(
    *datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=name,
)

for path in file:
    sourcePath = pathlib.Path(SPECPATH)/path
    targetPath = pathlib.Path(DISTPATH)/name/path
    if sourcePath.is_dir():
        shutil.copytree(sourcePath, targetPath, dirs_exist_ok=True, copy_function=shutil.copy)
    else:
        shutil.copy(sourcePath, targetPath)