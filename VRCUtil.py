from vrcutil import __version__, MODULES_PATH, INSTALL_PATH, DATA_PATH, IS_DEBUG
from vrcutil.file import SafeOpen, SafeRead, EasySetting, BufferedJsonSaver
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

from pywebwinui3.util import loadPage
from pywebwinui3.core import Status

from vrcutil.core import VRCUtil, Module, logger
from vrcutil.wmi import Check

logging.getLogger("asyncio").setLevel(logging.INFO)
logging.getLogger("PIL.Image").setLevel(logging.INFO)

pywebviewLogger = logging.getLogger("pywebview")
[pywebviewLogger.removeHandler(i) for i in pywebviewLogger.handlers[:]]
pywebviewLogger.setLevel(logging.NOTSET)
pywebviewLogger.propagate = True

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)-8s | %(asctime)s | %(name)-30s | %(message)s",
    datefmt="%H:%M:%S"
)

from Logger import open_log_window

app = VRCUtil("VRCUtil","./VRCUtil.ico")

@app.onValueChange("settings_checkUpdate")
def checkUpdate(*_):
    if app.values.get("settings_checkUpdate", False):
        try:
            app.values.set("vrcutil_latest", "fetching")
            with urllib.request.urlopen("https://api.github.com/repos/Haruna5718/VRCUtil/releases/latest") as resp:
                return app.values.set("vrcutil_hasUpdate", '0' if app.values.set("vrcutil_latest", json.loads(resp.read().decode("utf-8"))["tag_name"])!=__version__ else '')
        except:
            pass
    app.values.set("vrcutil_latest", "unknown")

@EasySetting.useData(DATA_PATH/"Setting.json")
def settingDataInit(setting:dict):
    settingSaver = BufferedJsonSaver(DATA_PATH/"Setting.json")
    settingValues = {
        "system_theme": "system",
        "system_pin": False,
        "settings_osc_address": "127.0.0.1",
        "settings_osc_send": 9000,
        "settings_osc_receive": 0,
        "settings_autoStart": "0",
        "settings_checkUpdate": False,
        "settings_startMinimized": False
    }
    for k,v in settingValues.items():
        app.values.set(k, setting.setdefault(k, v))

    app.events.valueChange += ("system_theme", lambda k,_,v: settingSaver.save(k,v))
    app.events.valueChange += ("system_pin", lambda k,_,v: settingSaver.save(k,v))
    app.events.valueChange += ("settings_*", lambda k,_,v: settingSaver.save(k,v))

    initClient()
    initServer(direct=True)
    
    threading.Thread(target=loadModule, daemon=True).start()
    threading.Thread(target=checkUpdate, daemon=True).start()

@app.onValueChange("settings_osc_address")
@app.onValueChange("settings_osc_send")
def initClient(*_):
    if (address:=app.values.get("settings_osc_address")) and (port:=app.values.get("settings_osc_send")):
        if not app.osc.client or app.osc.client._port!=port or app.osc.client._address!=address:
            app.osc._initClient(app.values["settings_osc_address"],int(app.values["settings_osc_send"]))

@app.onValueChange("settings_osc_address")
@app.onValueChange("settings_osc_receive")
def initServer(*_, direct=False):
    if not direct:
        app.osc.ServerRecreateFlag = getattr(app.osc,'ServerRecreateFlag',0)+1
        currentFlag = getattr(app.osc,'ServerRecreateFlag')
        time.sleep(1)
        if app.osc.ServerRecreateFlag!=currentFlag or app.osc.server.server_address==(app.values["settings_osc_address"],int(app.values["settings_osc_receive"])):
            return
    app.osc._initServer(app.values["system_title"],app.values["settings_osc_address"],int(app.values["settings_osc_receive"]))
    app.values.set("vrcutil_osc_receive",app.osc.server.server_address[1])

def loadModule():
    modules = [i for i in MODULES_PATH.iterdir() if i.is_dir() and not i.name.startswith("_")]
    for module in modules:
        threading.Thread(target=moduleSetup, args=(module,), daemon=True).start()

def moduleSetup(path:Path):
    try:
        Spec = importlib.util.spec_from_file_location(path.name, path/"__init__.py")
        module = importlib.util.module_from_spec(Spec)
        Spec.loader.exec_module(module)

        moduleClass:Module = getattr(module, path.name)(app)
        app.Modules[path.name] = moduleClass
        app.values.append("vrcutil_modules",[path.name, moduleClass.__name__, moduleClass.__version__, moduleClass.__description__, moduleClass.__urls__])
    except Exception as e:
        logger.error(f"Failed to load module {path.name}\n{traceback.format_exc()}")
        app.notice(Status.Critical, f"Failed to load module {path.name}", str(e))

@app.onValueChange("vrcutil_restart")
def restart(*_):
    app.tray.exit()
    time.sleep(1)
    subprocess.Popen(r"C:\Users\Haruna5718\OneDrive\code\Project\VRCUtil\.venv\Scripts\python.exe c:/Users/Haruna5718/OneDrive/code/Project/VRCUtil/VRCUtil.py")

@app.onValueChange("vrcutil_removeModule_*")
def removeModule(key, *_):
    moduleName = key[21:]
    moduleClass = app.Modules[moduleName]
    [app.values.remove("vrcutil_modules",i) for i in app.values["vrcutil_modules"] if i[0]==moduleName]
    if getattr(moduleClass,"__layout__",None):
        del app.values['system_pages'][moduleName]
    if getattr(moduleClass,"__widget__",None):
        app.values["system_pages"][""]["child"][0]["child"][0]["child"].remove(moduleClass.__widget__)
    app.values._sync("system_pages",None,app.values["system_pages"],True)
    del app.Modules[moduleName]
    app.notice(Status.Attention, "Restart required", f"please restart for remove {moduleName} completly",{"tag":"Button","text":"Restart","attr":{"value":"vrcutil_restart"},"child":[]})

@app.onSetup()
def setLockfile():
    lockFile.seek(1)
    lockFile.truncate()
    lockFile.write(app.api._window._server.address)
    lockFile.flush()
    if not IS_DEBUG:
        if not Check(INSTALL_PATH/"ServiceWorker.exe"):
            try:
                subprocess.Popen([str(INSTALL_PATH/"ServiceWorker.exe")],creationflags=0x08000000)
                logger.info(f"ServiceWorker launched.")
            except Exception as e:
                logger.error(f"Failed to start ServiceWorker\n{traceback.format_exc()}")

@app.onExit()
def CloseServices():
    lockFile.close()
    app.osc.stop()

@app.onValueChange("vrcutil_openLog")
def openlog(*_):
    open_log_window()

settingDataInit()

app.start(
    debug = "debug" in sys.argv,
    minimized = ("auto" in sys.argv) and app.values.get("settings_startMinimized", False),
    onTop = app.values.get("system_pin", False)
)