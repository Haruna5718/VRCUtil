from pywebwinui3 import MainWindow, loadPage, Notice
from Extention import EasyOSC, SafeOpen, EasySetting, ProcessWatcher, Steam
from pywebwinui3.event import Event
import threading
from pathlib import Path
import json
import time
import logging
import sys

__version__ = '3.0.0-dev'

logger = logging.getLogger("vrcutil")

class VRCUtil(MainWindow):
    def __init__(self, title):
        super().__init__(title)
        threading.Thread(target=self.__initVRCUtil__, daemon=True).start()
        # self.addPage("Test.xaml",imagePreload=False)

    def __initVRCUtil__(self):
        self.processWatcher = ProcessWatcher()
        self.osc:EasyOSC = None
        self.steam = Steam()
        self.Modules = {}

        self.events.exit = self.api._window.events.closed
        self.events.SteamVRStart = Event()
        self.events.SteamVRStop = Event()
        self.events.VRChatStart = Event()
        self.events.VRChatStop = Event()
        
        self.addPage("Dashboard.xaml")
        self.addSettings("Settings.xaml")
        self.processWatcher.addTarget(self.steam.findSteamAppPath("438100","UnityCrashHandler64.exe"),self._onVRChat)
        self.processWatcher.addTarget(self.steam.findSteamAppPath("250820","bin/win64/vrcompositor.exe"),self._onSteamVR)

    def _onSteamVR(self, path, state):
        if state:
            self.events.SteamVRStart.set(path)
        else:
            self.events.SteamVRStop.set(path)

    def _onVRChat(self, path, state):
        if state:
            self.events.VRChatStart.set(path)
        else:
            self.events.VRChatStop.set(path)

class Module:
	def __init__(self):
		pass

if __name__ == "__main__":
    if ("--multi" not in sys.argv) and (SafeOpen("VRCUtil.lock", "w", wait=False) == None):
        sys.exit(1)

    if ("--vrchat" in sys.argv):
        try:
            with open("Setting.json", "r", encoding="utf-8") as f:
                if json.load(f).get("settings.autoStart","0") != "2":
                    raise
        except:
            sys.exit(1)

    logging.getLogger("asyncio").setLevel(logging.INFO)

    logging.getLogger('bottle').setLevel(logging.CRITICAL)

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
                "settings.osc.receive": 9001,
                "settings.autoStart": "0",
                "settings.checkUpdate": False,
                "settings.debugLog": False
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
        modules = [i for i in (Path(__file__).parent/"Modules").iterdir() if i.is_dir() and not i.name.startswith("_")]
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

            if Widget := loadPage(module/"Widget.xaml"):
                app.values["system.pages"][""]["child"].append(Widget)

            app.addPage(module/"Layout.xaml")
                    
            app.Modules[module.name] = moduleCore
        except Exception as e:
            logger.error(f"Failed to load module <{module.name}>\n{traceback.format_exc()}")
            app.notice(Notice.Error, f"Failed to load module {module.name}", str(e))

    @app.onSetup()
    def startWatcher():
        app.processWatcher.start(checkCurrent=True)

    @app.onExit()
    def CloseServices():
        app.osc.stop()
        app.processWatcher.stop()

    @app.onValueChange("vrcutil.openLog")
    def openlog(*_):
        open_log_window()

    threading.Thread(target=settingDataInit,daemon=True).start()
    app.start("debug" in sys.argv)