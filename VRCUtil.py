from vrcutil import VRCUtil, __version__, MODULES_PATH, INSTALL_PATH, DATA_PATH
from vrcutil.file import SafeOpen, SafeRead, EasySetting
import sys

lockFile = SafeOpen(INSTALL_PATH/"VRCUtil.lock", "w", wait=False)
if lockFile == None:
    sys.exit(1)

import threading
import bottle
import json
import time
import logging
import urllib.request
import subprocess
import importlib.util
import traceback
from pathlib import Path

from pywebwinui3 import loadPage, Notice

from vrcutil.wmi import Check

logger = logging.getLogger("vrcutil")

logging.getLogger("asyncio").setLevel(logging.INFO)

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

@app.onValueChange("settings.checkUpdate")
def checkUpdate(*_):
    if app.values.get("settings.checkUpdate", False):
        try:
            app.setValue("vrcutil.latest", "fetching")
            with urllib.request.urlopen("https://api.github.com/repos/Haruna5718/VRCUtil/releases/latest") as resp:
                return app.setValue("vrcutil.hasUpdate", '0' if app.setValue("vrcutil.latest", json.loads(resp.read().decode("utf-8"))["tag_name"])!=__version__ else '')
        except:
            pass
    app.setValue("vrcutil.latest", "unknown")

@EasySetting.useData(DATA_PATH/"Setting.json")
def settingDataInit(setting):
    settingValues = {
        "system.theme": "system",
        "system.isOnTop": False,
        "settings.osc.address": "127.0.0.1",
        "settings.osc.send": 9000,
        "settings.osc.receive": 0,
        "settings.autoStart": "0",
        "settings.checkUpdate": False,
        "settings.startMinimized": False
    }
    for k,v in settingValues.items():
        app.setValue(k, setting.setdefault(k, v))

    initClient()
    initServer(direct=True)
    
    # threading.Thread(target=app.api.setTop, args=(app.getValue("system.isOnTop"),), daemon=True).start()
    threading.Thread(target=loadModule, daemon=True).start()
    threading.Thread(target=checkUpdate, daemon=True).start()

@app.onValueChange("settings.osc.address")
@app.onValueChange("settings.osc.send")
def initClient(*_):
    app.osc._initClient(app.getValue("settings.osc.address"),int(app.getValue("settings.osc.send")))

@app.onValueChange("settings.osc.address")
@app.onValueChange("settings.osc.receive")
def initServer(*_, direct=False):
    if not direct:
        app.osc.ServerRecreateFlag = getattr(app.osc,'ServerRecreateFlag',0)+1
        currentFlag = getattr(app.osc,'ServerRecreateFlag')
        time.sleep(1)
        if app.osc.ServerRecreateFlag!=currentFlag or app.osc.server.server_address==(app.getValue("settings.osc.address"),int(app.getValue("settings.osc.receive"))):
            return
    app.osc._initServer(app.getValue("system.title"),app.getValue("settings.osc.address"),int(app.getValue("settings.osc.receive")))
    app.setValue("vrcutil.osc.receive",app.osc.server.server_address[1])

@app.onValueChange("system.theme")
@app.onValueChange("system.isOnTop")
@app.onValueChange("settings.*")
@EasySetting.useData()
def saveSettings(key:str, before, after, setting:dict):
    setting[key] = after
    return setting

def loadModule():
    modules = [i for i in (MODULES_PATH).iterdir() if i.is_dir() and not i.name.startswith("_")]
    for module in modules:
        threading.Thread(target=moduleSetup, args=(module,), daemon=True).start()

def eventSetup(targetClass):
    import inspect
    for _, callback in inspect.getmembers(targetClass):
        function = getattr(callback, "__func__", callback)

        eventDatas = getattr(function, "__VRCUtil_Events__", [])
        for eventData in eventDatas:
            if len(eventData)==1:
                getattr(app.events,eventData[0]).__iadd__(callback)
            else:
                getattr(app.events,eventData[0]).append(eventData[1],callback)

        oscHandlers = getattr(function, "__VRCUtil_OSCListen__", [])
        for path in oscHandlers:
            app.osc.addHandler(path,callback)

def moduleSetup(module:Path):
    try:
        moduleInfo:dict = json.loads(SafeRead(module/"module.json"))
        moduleName        = moduleInfo.get("name","Unknown")
        moduleVersion     = moduleInfo.get("version","Unknown")
        moduleAuthor      = moduleInfo.get("author","Unknown")
        moduleDescription = moduleInfo.get("description","Unknown")
        moduleUrls        = moduleInfo.get("urls","Unknown")
        logger.info(f"Loading Module\n{' '*53}| ├─ Name: {moduleName}\n{' '*53}| ├─ Path: {module.name}\n{' '*53}| ├─ Version: {moduleVersion}\n{' '*53}| ├─ Author: {moduleAuthor}\n{' '*53}| ├─ Description: {moduleDescription}\n{' '*53}| └─ Urls: {moduleUrls}")
        
        Spec = importlib.util.spec_from_file_location("Function", module/"Function.py")
        Module = importlib.util.module_from_spec(Spec)
        Spec.loader.exec_module(Module)

        moduleCore = getattr(Module, module.name)(app)
        
        threading.Thread(target=eventSetup, args=(moduleCore,), daemon=True).start()

        if (module/"Widget.xaml").exists():
            if Widget := loadPage(module/"Widget.xaml"):
                app.values["system.pages"][""]["child"][0]["child"][0]["child"].append(Widget)

        if (module/"Layout.xaml").exists():
            app.addPage(module/"Layout.xaml")
                
        app.Modules[module.name] = moduleCore
        app.setValue("vrcutil.moduleCount",len(app.Modules))
    except Exception as e:
        logger.error(f"Failed to load module <{module.name}>\n{traceback.format_exc()}")
        app.notice(Notice.Error, f"Failed to load module {module.name}", str(e))

@app.onSetup()
def setLockfile():
    lockFile.seek(1)
    lockFile.truncate()
    lockFile.write(app.api._window._server.address)
    lockFile.flush()
    if not Check(INSTALL_PATH/"ServiceWorker.exe"):
        try:
            subprocess.Popen([str(INSTALL_PATH/"ServiceWorker.exe")],creationflags=0x08000000)
            logger.info(f"ServiceWorker launched.")
        except Exception as e:
            logger.error(f"Failed to start ServiceWorker: {e}")

@app.server.post('/')
def syncState():
    data = bottle.request.json
    logger.info(f"Sync state received: {data}")
    for k, v in data.items():
        if app.eventStatus.get(k) != v:
            app.eventStatus[k] = v
            eventname = f"{k}{'Start' if v else 'Stop'}"
            try:
                getattr(app.events, eventname).set()
                logger.debug(f"{eventname} event triggered")
            except Exception as e:
                logger.warning(f"Unknown event \"{eventname}\": {e}")

@app.onExit()
def CloseServices():
    app.osc.stop()

@app.onValueChange("vrcutil.openLog")
def openlog(*_):
    open_log_window()

settingDataInit()

app.start(
    debug = "debug" in sys.argv,
    minimized = (("auto" in sys.argv) and app.getValue("settings.startMinimized",False)),
    onTop = app.getValue("system.isOnTop",False)    
)