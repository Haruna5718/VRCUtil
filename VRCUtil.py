from vrcutil import __version__, MODULES_PATH, INSTALL_PATH, DATA_PATH
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
import importlib.util
import traceback
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

app = VRCUtil("VRCUtil","./VRCUtil.ico")
_osc_server_timer: threading.Timer | None = None
_osc_server_timer_lock = threading.Lock()
_MODULE_LOAD_WORKERS = 4

@app.onValueChange("settings_checkUpdate")
def checkUpdate(*_):
    if app.values.get("settings_checkUpdate", False):
        try:
            app.values.set("vrcutil_latest", "fetching")
            with urllib.request.urlopen("https://api.github.com/repos/Haruna5718/VRCUtil/releases/latest", timeout=5) as resp:
                latest_version = json.load(resp)["tag_name"]
                app.values.set("vrcutil_latest", latest_version)
                return app.values.set("vrcutil_hasUpdate", '0' if latest_version != __version__ else '')
        except:
            pass
    app.values.set("vrcutil_latest", "unknown")

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

    worker_count = min(_MODULE_LOAD_WORKERS, len(modules))
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="vrcutil-module") as executor:
        wait([executor.submit(moduleSetup, module) for module in modules])

def moduleSetup(path:Path):
    try:
        Spec = importlib.util.spec_from_file_location(path.name, path/"__init__.py")
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
    initClient()
    initServer(direct=True)
    loadModule()
    app.start_process_monitor()

@app.onValueChange("vrcutil_restart")
def restart(*_):
    app.api.destroy()
    time.sleep(1)
    subprocess.Popen(r"C:\Users\Haruna5718\OneDrive\code\Project\VRCUtil\.venv\Scripts\python.exe c:/Users/Haruna5718/OneDrive/code/Project/VRCUtil/VRCUtil.py") # temp
    # todo: module remove args

@app.onValueChange("vrcutil_removeModule_*")
def removeModule(key, *_):
    moduleName = key[21:]
    moduleClass = app.Modules[moduleName]
    for moduleInfo in tuple(app.values["vrcutil_modules"]):
        if moduleInfo[0] == moduleName:
            app.values.remove("vrcutil_modules", moduleInfo)
    if getattr(moduleClass,"__layout__",None):
        del app.values['system_pages'][moduleName]
    if getattr(moduleClass,"__widget__",None):
        app.remove_module_widget(moduleClass.__widget__)
    else:
        app.sync_pages()
    del app.Modules[moduleName]
    app.notice(Status.Attention, "Restart required", f"please restart for remove {moduleName} completly",{"tag":"Button","text":"Restart","attr":{"value":"vrcutil_restart"},"child":[]})

@app.onSetup()
def setLockfile():
    lockFile.seek(0)
    lockFile.truncate()
    lockFile.flush()

@app.onSetup()
def startBackgroundTasks():
    threading.Thread(target=bootstrapRuntime, daemon=True).start()
    threading.Thread(target=checkUpdate, daemon=True).start()

@app.onExit()
def CloseServices():
    app.stop_process_monitor()
    app.osc.stop()
    lockFile.close()

@app.onValueChange("vrcutil_openLog")
def openlog(*_):
    open_log_window()

settingDataInit()

app.start(
    debug = "debug" in sys.argv,
    minimized = ("auto" in sys.argv) and app.values.get("settings_startMinimized", False),
    onTop = app.values.get("system_pin", False),
    min_width=800,
    min_height=500,
)