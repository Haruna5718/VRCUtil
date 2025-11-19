from vrcutil.file import SafeOpen, EasySetting
import sys

lockFile = SafeOpen("VRCUtil.lock", "w", wait=False)
if lockFile == None:
    sys.exit(1)

from pywebwinui3 import loadPage, Notice
import threading
import bottle
from pathlib import Path
import json
import time
import logging
import subprocess

from vrcutil import VRCUtil, __version__, MODULES_PATH, INSTALL_PATH
from vrcutil.osc import EasyOSC
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

app = VRCUtil("VRCUtil")

app.setValue("system.version", __version__)
app.setValue("system.icon", "./app.ico")

@app.onValueChange("settings.checkUpdate")
def checkUpdate(*_):
    if app.values.get("settings.checkUpdate", False):
        try:
            app.setValue("system.latest", "fetching")
            import requests
            return app.setValue("system.latest", requests.get("https://api.github.com/repos/Haruna5718/VRCUtil/releases/latest").json()["tag_name"])
        except:
            pass
    app.setValue("system.latest", "unknown")

def settingDataInit():
    with SafeOpen("Setting.json", "r+", encoding="utf-8") as f:
        setting = json.load(f)
        settingValues = {
            "system.theme": "system",
            "system.isOnTop": False,
            "settings.osc.address": "127.0.0.1",
            "settings.osc.send": 9000,
            "settings.osc.receive": 30000,
            "settings.autoStart": "0",
            "settings.checkUpdate": False,
            "settings.startMinimized": False
        }
        for k,v in settingValues.items():
            app.setValue(k, setting.setdefault(k, v))
        f.seek(0)
        f.truncate()
        json.dump(setting, f, ensure_ascii=False, indent=4)
    app.osc = EasyOSC(app.getValue("system.title"),app.getValue("settings.osc.address"),int(app.getValue("settings.osc.send")),int(app.getValue("settings.osc.receive")))
    
    threading.Thread(target=app.api.setTop, args=(app.getValue("system.isOnTop"),), daemon=True).start()
    threading.Thread(target=loadModule, daemon=True).start()
    threading.Thread(target=checkUpdate, daemon=True).start()

    @app.onValueChange("settings.osc.address")
    @app.onValueChange("settings.osc.send")
    def reInitClient(*_):
        app.osc._initClient(app.getValue("settings.osc.address"),int(app.getValue("settings.osc.send")))
    
    @app.onValueChange("settings.osc.address")
    @app.onValueChange("settings.osc.receive")
    def reInitServer(*_):
        app.osc.ServerRecreateFlag = getattr(app.osc,'ServerRecreateFlag',0)+1
        currentFlag = getattr(app.osc,'ServerRecreateFlag')
        time.sleep(1)
        if app.osc.ServerRecreateFlag==currentFlag and app.osc.server.server_address!=(address:=(app.getValue("settings.osc.address"),int(app.getValue("settings.osc.receive")))):
            app.osc._initServer(app.getValue("system.title"),*address)

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
    import importlib.util
    import traceback

    try:
        Spec = importlib.util.spec_from_file_location("Function", module/"Function.py")
        Module = importlib.util.module_from_spec(Spec)
        Spec.loader.exec_module(Module)

        moduleClass = getattr(Module, module.name)

        moduleVersion = getattr(moduleClass, "Version", "Unknown")
        moduleAuthor = getattr(moduleClass, "Author", "Unknown")
        moduleDescription = getattr(moduleClass, "Description", "Unknown")
        moduleUrls = getattr(moduleClass, "Urls", "Unknown")
        logger.info(f"Loading Module\n{' '*53}| ├─ Name: {module.name}\n{' '*53}| ├─ Version: {moduleVersion}\n{' '*53}| ├─ Author: {moduleAuthor}\n{' '*53}| ├─ Description: {moduleDescription}\n{' '*53}| └─ Urls: {moduleUrls}")

        moduleCore = moduleClass(app)
        
        threading.Thread(target=eventSetup, args=(moduleCore,), daemon=True).start()

        if (module/"Widget.xaml").exists():
            if Widget := loadPage(module/"Widget.xaml"):
                app.values["system.pages"][""]["child"][0]["child"][0]["child"].append(Widget)

        if (module/"Layout.xaml").exists():
            app.addPage(module/"Layout.xaml")
            app.setValue("vrcutil.dashboard",True)
                
        app.Modules[module.name] = moduleCore
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
            subprocess.Popen([str(INSTALL_PATH/"ServiceWorker.exe")])
            logger.error(f"ServiceWorker launched.")
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

threading.Thread(target=settingDataInit,daemon=True).start()
app.start("debug" in sys.argv)