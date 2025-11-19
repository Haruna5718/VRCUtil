def Win32Modules():
    import win32
    import win32api
    import win32con
    import win32com
    import win32com.client
    import win32event
    import win32file
    import win32gui
    import win32gui_struct
    import win32help
    import win32inet
    import win32job
    import win32net
    import win32netcon
    import win32pdh
    import win32pdhutil
    import win32pipe
    import win32process
    import win32profile
    import win32security
    import win32service
    import win32serviceutil
    import win32timezone
    import win32trace
    import win32traceutil
    import pythoncom
    import pywintypes
    
def AdditionalModules():
    import proxy_tools
    
import re
import sys
import json
import zipfile
import urllib.request
import importlib
import pathlib
from packaging.version import Version
from packaging.specifiers import SpecifierSet
import tempfile
import logging

from . import INSTALL_PATH, IS_DEBUG

logger = logging.getLogger("vrcutil.pip")

PACKAGE_PATH = INSTALL_PATH/".venv"/"Lib"/"site-packages" if IS_DEBUG else INSTALL_PATH/"_internal"

def _checkWheel(filename:str) -> bool:
    if not filename.endswith(".whl"):
        return False

    if filename.endswith("none-any.whl"):
        return True

    abis = [f"cp{sys.version_info.major}{sys.version_info.minor}", "abi3", "none"]

    if m := re.match(r"^[^-]+-[^-]+-(?P<pytag>[^-]+)-(?P<abi>[^-]+)-(?P<plat>[^.]+)\.whl$",filename):
        pytag = m.group("pytag")
        abi = m.group("abi")
        plat = m.group("plat")
    else:
        return False

    if pytag != abis[0] and not pytag.startswith("py"):
        return False

    if abi not in abis:
        return False

    if ("win_amd64" if sys.maxsize > 2**32 else "win32") not in plat:
        return False

    return True

def _parseSpec(name: str):
    name = name.strip()

    if "; extra" in name:
        return None, None

    if ";" in name:
        name = name.split(";", 1)[0].strip()

    m = re.match(
        r"^\s*(?P<name>[A-Za-z0-9_\-]+)"
        r"(?:\[(?P<extras>[^\]]+)\])?"
        r"\s*(?:\((?P<spec_paren>[^)]+)\))?"
        r"\s*(?P<spec_noparen>[<>=!~][^ ]+.*)?$",
        name
    )

    if not m:
        return None, None

    name = m.group("name").strip()

    if m.group("spec_paren"):
        return name, m.group("spec_paren").strip()

    if m.group("spec_noparen"):
        return name, m.group("spec_noparen").strip()

    return name, ""

def _loadList() -> dict:
    try:
        with open(PACKAGE_PATH/"package.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = _saveList({"pywin32":"win32", "proxy_tools":"proxy_tools", "packaging":"packaging", "importlib":"importlib"})
    return data

def _saveList(data) -> dict:
    with open(PACKAGE_PATH/"package.json", "w", encoding="utf-8") as f:
        json.dump(data,f,indent=4)
    return data

def _getImportName(name) -> str:
    for dist in list(PACKAGE_PATH.glob(f"{name.replace('-', '_')}*.dist-info")):
        tl = dist / "top_level.txt"
        if tl.exists():
            for mod in tl.read_text().splitlines():
                mod = mod.strip()
                if mod:
                    return mod
    return name

def import_module(name:str):
    try:
        return importlib.import_module(_getImportName(name))
    except ModuleNotFoundError:
        install_module(name)
        return importlib.import_module(_getImportName(name))

def check_module(name:str, install=None) -> bool:
    data = _loadList()
    return (name in data) or (install and install in data.values())

def install_module(name:str):
    try:
        name, spec = _parseSpec(name)

        if not name:
            return
        
        if check_module(name):
            return logger.info(f"Module already installed: {name}")
        
        logger.info(f"Installing Module: {name} {spec}")

        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json") as r:
            meta = json.load(r)

        if spec:
            version = str(max(
                [Version(v) for v in meta["releases"].keys()
                if Version(v) in SpecifierSet(spec)]
            ))
        else:
            version = meta["info"]["version"]

        releases = meta["releases"][version]

        target = [f for f in releases if _checkWheel(f["filename"])]

        if not target:
            logger.info(f"{name}: No compatible wheel found for this environment (skip)")
            return

        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp)/target[0]["filename"]
            urllib.request.urlretrieve(target[0]["url"], path)
            with zipfile.ZipFile(path, "r") as z:
                z.extractall(PACKAGE_PATH)
                _saveList({**_loadList(), name: _getImportName(name)})
                for archiveName in z.namelist():
                    if archiveName.endswith("METADATA") and ".dist-info/" in archiveName:
                        with z.open(archiveName) as f:
                            for line in f.read().decode("utf-8").splitlines():
                                if line.startswith("Requires-Dist:"):
                                    install_module(line[len("Requires-Dist:"):].strip())

        logger.info(f"{name} {version} installed")
    except Exception as e:
        logger.error(f"Failed to install module {name}: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)-8s | %(asctime)s | %(name)-30s | %(message)s",
        datefmt="%H:%M:%S"
    )

    import_module("PyWebWinUI3").MainWindow("test").start()

# pyinstaller test.py --name test_dynpip --onedir --console --exclude-module --noconfirm