from vrcutil import __version__, MODULES_PATH, INSTALL_PATH, DATA_PATH, PACKAGES_PATH, IS_DEBUG, registry, steam
from vrcutil.file import SafeOpen, EasySetting, BufferedJsonSaver
import sys

lockFile = SafeOpen(INSTALL_PATH/"VRCUtil.lock", "w", wait=False)
if lockFile.file == None:
    sys.exit(1)

import threading
import json
import time
import logging
import urllib.request
import subprocess
import tempfile
import shutil
import importlib.util
import traceback
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait

from pywebwinui3.core import Status

from vrcutil.core import VRCUtil, Module, logger

logging.getLogger("asyncio").setLevel(logging.INFO)
logging.getLogger("PIL.Image").setLevel(logging.INFO)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)-8s | %(asctime)s | %(name)-30s | %(message)s",
    datefmt="%H:%M:%S"
)

from Logger import open_log_window

app = VRCUtil("VRCUtil","VRCUtil.ico")
LATEST_RELEASE_URL = "https://github.com/Haruna5718/VRCUtil/releases/latest"
_notified_update_version = None
AUTO_MODE = "auto" in sys.argv

def syncSteamVRAutostart(state: bool):
    manifest = INSTALL_PATH / "manifest.vrmanifest"
    if not manifest.exists() or not steam.hasSteamVR():
        return
    vr = steam.VR(manifest)
    if state and (not vr.installed or not vr.config.exists()):
        vr.install()

    if state:
        vr.setAutostart(True)
    elif vr.installed and vr.autostart:
        vr.setAutostart(False)

def syncSystemAutostart(state: bool):
    registry.Program.unsetAutostart("VRCUtil")
    registry.Program.unsetAutostartState("VRCUtil")

    shortcut = registry.Program.startupShortcutPath("VRCUtil")
    if state and not shortcut.exists():
        if IS_DEBUG:
            registry.Program.setStartupShortcut(
                "VRCUtil",
                sys.executable,
                subprocess.list2cmdline([str((INSTALL_PATH / "VRCUtil.py").resolve()), "auto"]),
                INSTALL_PATH / "VRCUtil.ico",
            )
        else:
            registry.Program.setStartupShortcut(
                "VRCUtil",
                INSTALL_PATH / "VRCUtil.exe",
                "auto",
            )

    if shortcut.exists():
        current = registry.Program.startupShortcutState("VRCUtil")
        if current != state:
            registry.Program.setStartupShortcutState("VRCUtil", state)

def syncAutostart():
    mode = str(app.values.get("settings_autoStart", "0"))

    try:
        syncSteamVRAutostart(mode == "1")
    except Exception:
        logger.error("Failed to sync SteamVR autostart\n%s", traceback.format_exc())

    try:
        syncSystemAutostart(mode == "3")
    except Exception:
        logger.error("Failed to sync system autostart\n%s", traceback.format_exc())


def notifyUpdate(latest_version: str):
    global _notified_update_version

    if latest_version == __version__ or latest_version == _notified_update_version:
        return

    _notified_update_version = latest_version
    app.notice(
        Status.Attention,
        "Update available",
        f"{latest_version} is available. Current version is {__version__}.",
        {
            "tag": "Button",
            "text": "Open Release",
            "attr": {
                "type": "link",
                "url": LATEST_RELEASE_URL,
            },
            "child": [],
        },
    )

@app.onValueChange("settings_checkUpdate")
def checkUpdate(*_):
    if app.values.get("settings_checkUpdate", False):
        try:
            app.values.set("vrcutil_latest", "fetching")
            with urllib.request.urlopen("https://api.github.com/repos/Haruna5718/VRCUtil/releases/latest", timeout=5) as resp:
                latest_version = json.load(resp)["tag_name"]
                app.values.set("vrcutil_latest", latest_version)
                if latest_version != __version__:
                    notifyUpdate(latest_version)
                return app.values.set("vrcutil_hasUpdate", '0' if latest_version != __version__ else '')
        except:
            pass
    app.values.set("vrcutil_latest", "unknown")


@app.onValueChange("settings_autoStart")
def updateAutostart(*_):
    syncAutostart()

@EasySetting.useData(DATA_PATH/"Setting.json")
def settingDataInit(setting:dict):
    settingSaver = BufferedJsonSaver(DATA_PATH/"Setting.json")
    setting.pop("system_window_min_width", None)
    setting.pop("system_window_min_height", None)
    settingValues = {
        "system_pin": False,
        "system_theme": "system",
        "system_window_width": 900,
        "system_window_height": 600,
        "settings_osc_address": "127.0.0.1",
        "settings_osc_send": 9000,
        "settings_osc_receive": 0,
        "settings_autoStart": "0",
        "settings_checkUpdate": False
    }
    for k,v in settingValues.items():
        app.values.set(k, setting.setdefault(k, v), False)

    def saveSettingValue(key, _, value):
        settingSaver.save(key, value)

    for key_pattern in (
        "system_theme",
        "system_pin",
        "system_window_width",
        "system_window_height",
        "settings_*",
    ):
        app.events.valueChange += (key_pattern, saveSettingValue)
    app.events.valueChange += ("settings_osc_address", initClient)
    app.events.valueChange += ("settings_osc_send", initClient)
    app.events.valueChange += ("settings_osc_address", initServer)
    app.events.valueChange += ("settings_osc_receive", initServer)

def initClient(*_):
    address = app.values.get("settings_osc_address")
    try:
        port = int(app.values.get("settings_osc_send"))
    except (TypeError, ValueError):
        return

    if address and (not app.osc.client or app.osc.client._port != port or app.osc.client._address != address):
        app.osc._initClient(address, port)

_osc_server_timer: threading.Timer | None = None
_osc_server_timer_lock = threading.Lock()
def _scheduleServerInit():
    global _osc_server_timer

    with _osc_server_timer_lock:
        if _osc_server_timer is not None:
            _osc_server_timer.cancel()

        _osc_server_timer = threading.Timer(1.0, initServer, kwargs={"direct": True})
        _osc_server_timer.daemon = True
        _osc_server_timer.start()

def initServer(*_, direct=False):
    if not direct:
        _scheduleServerInit()
        return

    global _osc_server_timer
    with _osc_server_timer_lock:
        _osc_server_timer = None

    if not app.values.get("settings_osc_address"):
        return

    target_address = app.values["settings_osc_address"]
    try:
        target_port = int(app.values["settings_osc_receive"])
    except (TypeError, ValueError):
        return
    current_server = getattr(app.osc, "server", None)
    if current_server and current_server.server_address == (target_address, target_port):
            return

    app.osc._initServer(app.values["system_title"], target_address, target_port)
    app.values.set("vrcutil_osc_receive",app.osc.server.server_address[1])

def loadModule():
    modules = sorted(
        [i for i in MODULES_PATH.iterdir() if i.is_dir() and not i.name.startswith("_")],
        key=lambda path: path.name.lower(),
    )
    if not modules:
        return

    max_workers = min(len(modules), max(1, min(8, os.cpu_count() or 1)))
    with app.batch_ui_sync():
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            wait([executor.submit(moduleSetup, module) for module in modules])

def resolveModuleEntry(path: Path) -> Path | None:
    pyd_entries = sorted(path.glob("__init__*.pyd"))
    if pyd_entries:
        return pyd_entries[0]

    py_entry = path / "__init__.py"
    if py_entry.exists():
        return py_entry

    return None

def moduleSetup(path:Path):
    try:
        entry = resolveModuleEntry(path)
        if entry is None:
            raise ImportError(f"Failed to find module entry for {path.name}")
        Spec = importlib.util.spec_from_file_location(path.name, entry)
        if Spec is None or Spec.loader is None:
            raise ImportError(f"Failed to create module spec for {path.name}")
        module = importlib.util.module_from_spec(Spec)
        Spec.loader.exec_module(module)

        moduleClass:Module = getattr(module, path.name)(app)
        app.register_module(path.name, moduleClass)
    except Exception as e:
        logger.error(f"Failed to load module {path.name}\n{traceback.format_exc()}")
        app.notice(Status.Critical, f"Failed to load module {path.name}", str(e))

def bootstrapRuntime():
    PACKAGES_PATH.mkdir(parents=True, exist_ok=True)
    for path in (INSTALL_PATH/"Lib", INSTALL_PATH/"DLLs", PACKAGES_PATH):
        if path.exists():
            resolved = str(path)
            if resolved not in sys.path:
                sys.path.append(resolved)
    initClient()
    initServer(direct=True)
    loadModule()
    app.start_process_monitor()

GlobalTempDir = None

def CleanTempDir():
    if not GlobalTempDir:
        return
    subprocess.Popen(["cmd", "/c", f"timeout /T 5 >nul & rmdir /S /Q {GlobalTempDir}"], creationflags=subprocess.CREATE_NO_WINDOW)

def restartCommand():
    args = [arg for arg in sys.argv[1:] if arg != "auto"]
    if IS_DEBUG:
        return [sys.executable, str((INSTALL_PATH / "VRCUtil.py").resolve()), *args]
    return [str((INSTALL_PATH / "VRCUtil.exe").resolve()), *args]

@app.onValueChange("vrcutil_restart")
def restart(*_):
    CloseServices()
    subprocess.Popen(
        ["cmd", "/c", f"timeout /T 1 >nul & {subprocess.list2cmdline(restartCommand())}"],
        cwd=INSTALL_PATH,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    app.api.destroy()

@app.onValueChange("vrcutil_removeModule_*")
def removeModule(key, *_):
    global GlobalTempDir
    moduleName = key[21:]
    moduleClass = app.Modules[moduleName]
    with app.batch_ui_sync():
        if getattr(moduleClass,"__layout__",None):
            del app.values['system_pages'][moduleName]
        if getattr(moduleClass,"__widget__",None):
            app.remove_module_widget(moduleClass.__widget__)
        elif getattr(moduleClass,"__layout__",None):
            app._request_page_sync()
        app.unregister_module(moduleName)

    modulePath = MODULES_PATH/moduleName
    GlobalTempDir = GlobalTempDir or Path(tempfile.mkdtemp())
    shutil.move(str(modulePath), str(GlobalTempDir/modulePath.name))

    app.notice(Status.Attention, "Restart required", f"please restart for remove {moduleName} completly",{"tag":"Button","text":"Restart","attr":{"value":"vrcutil_restart"},"child":[]})

@app.onSetup()
def setLockfile():
    lockFile.seek(0)
    lockFile.truncate()
    lockFile.flush()

@app.onSetup()
def startBackgroundTasks():
    threading.Thread(target=checkUpdate, daemon=True).start()

@app.onExit()
def CloseServices():
    try:
        app.stop_process_monitor()
    except:
        pass
    try:
        app.osc.stop()
    except:
        pass
    try:
        lockFile.close()
    except:
        pass
    try:
        CleanTempDir()
    except:
        pass

@app.onValueChange("vrcutil_openLog")
def openlog(*_):
    open_log_window()

settingDataInit()
threading.Thread(target=bootstrapRuntime, daemon=True).start()

app.start(
    debug = "debug" in sys.argv,
    minimized = AUTO_MODE,
    onTop = app.values.get("system_pin", False),
    min_width=800,
    min_height=500,
)
