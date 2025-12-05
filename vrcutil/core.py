import json
import bottle
import pathlib
import pystray
import logging
import inspect
import PIL.Image
import threading
import traceback
import pywebwinui3.core
import pywebwinui3.util
import pywebwinui3.type

from . import file, osc, steam, __version__, INSTALL_PATH, DATA_PATH, MODULES_PATH

logger = logging.getLogger("vrcutil")

class VRCUtil(pywebwinui3.core.MainWindow):
    def __init__(self, title, icon):
        super().__init__(title, icon)
        self.rootPath = INSTALL_PATH
        self.api._window.hidden = True
        self.api.minimize = self.api._window.minimize
        self.api.destroy = self.api._window.hide

        self.osc = osc.EasyOSC(title, init=False)

        threading.Thread(target=self.__initVRCUtil__, args=(title, icon,), daemon=True).start()

    def __initVRCUtil__(self, title, icon):

        self.steam = steam.VR(INSTALL_PATH/"manifest.vrmanifest")
        
        self.Modules:dict[str,Module] = {}
        
        self.addPage("Dashboard.xaml")
        self.addSettings("Settings.xaml")

        self.values.set("vrcutil_version", __version__, False)
        self.tray = VRCUtilTray(self, title, icon, start=True)

    def serverRouteFile(self, filepath:str):
        return bottle.static_file(filepath, root=DATA_PATH if (DATA_PATH/filepath).is_file() else self.rootPath)

    def syncProcessState(self):
        data = bottle.request.json
        logger.info(f"Sync state received: {data}")
        for k, v in data.items():
            self.values.set(f"{k}_state", bool(v))

    def start(self, debug=False, minimized=False, onTop=False):
        self.api._window.on_top = onTop
        self.api._window.hidden = minimized

        self.server.post('/',callback=self.syncProcessState)

        super().start(debug)

class VRCUtilTray(pystray.Icon):
    def __init__(self, app:VRCUtil, title, icon, start=False):
        self.app = app
        super().__init__(
            title,
            PIL.Image.open(icon),
            title,
            pystray.Menu(
                pystray.MenuItem("Open", self.open, default=True),
                pystray.MenuItem("Exit", self.exit)
            )
        )
        if start:
            threading.Thread(target=self.start, daemon=True).start()

    def open(self):
        self.app.api._window.show()
        self.app.api._window.restore()

    def exit(self):
        self.stop()
        self.app.api._window.destroy()
    
    def start(self):
        self.run()

class Module:
    def __init__(self, app:VRCUtil):
        self.app = app

        self.__init_info__()
        self.__init_event__()
        self.__init_layout__()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.__path__ = pathlib.Path(cls.__dict__['__init__'].__code__.co_filename).parent.name

    def __init_info__(self):
        self.__info__:dict[str,str|list[dict[str,str]]] = json.loads(file.SafeRead(MODULES_PATH/self.__path__/"module.json"))
        self.__name__:str|None                 = self.__info__.get("name")
        self.__version__:str|None              = self.__info__.get("version")
        self.__author__:str|None               = self.__info__.get("author")
        self.__description__:str|None          = self.__info__.get("description")
        self.__urls__:list[dict[str,str]]|None = self.__info__.get("urls")
        logger.info(f"Module loaded {self.__name__ or 'Unknown'}\n{' '*53}| ├─ Path: {self.__path__}\n{' '*53}| ├─ Version: {self.__version__ or 'Unknown'}\n{' '*53}| ├─ Author: {self.__author__ or 'Unknown'}\n{' '*53}| ├─ Description: {self.__description__ or 'Unknown'}")

    def __init_event__(self):
        for _, callback in inspect.getmembers(self, inspect.ismethod):
            for eventData in getattr(callback.__func__, "__VRCUtil_Events__", []):
                getattr(self.app.events,eventData[0]).__iadd__(callback if len(eventData)==1 else (eventData[1],callback))

            for path in getattr(callback.__func__, "__VRCUtil_OSCListen__", []):
                self.app.osc.addHandler(path, f"{callback.__name__}_{path}", callback)

    def __init_layout__(self):
        if (layoutPath:=MODULES_PATH/self.__path__/"Layout.xaml").exists():
            try:
                self.__layout__ = pywebwinui3.util.loadPage(layoutPath)
                self.__layout__["attr"]["path"] = self.__path__
                self.app.addPage(pageData=self.__layout__)
            except Exception as e:
                logger.error(f"Faild to load page: {layoutPath}\n{traceback.format_exc()}")
                self.app.notice(pywebwinui3.type.Status.Caution, f"Faild to load page {self.__name__}", str(e))

        if (widgetPath:=MODULES_PATH/self.__path__/"Widget.xaml").exists():
            try:
                self.__widget__ = pywebwinui3.util.loadPage(widgetPath)
                self.app.values.get("system_pages")[""]["child"][0]["child"][0]["child"].append(self.__widget__)
            except Exception as e:
                logger.error(f"Faild to load widget: {widgetPath}\n{traceback.format_exc()}")
                self.app.notice(pywebwinui3.type.Status.Caution, f"Faild to load widget {self.__name__}", str(e))

class EasyModule(Module):
    def __init__(self, app:VRCUtil, load:dict[str]=None, init:dict[str]=None, save:list[str]=None):
        super().__init__(app)

        if load:
            self.__init_value_load__(load)
        if init:
            self.__init_value_init__(init)
        if save:
            self._valueSaver = file.BufferedJsonSaver(DATA_PATH/MODULES_PATH.name/self.__path__/"Setting.json")
            self.__init_value_save__(save)

    def __init_value_load__(self, load:dict[str]):
        with file.SafeOpen(DATA_PATH/MODULES_PATH.name/self.__path__/"Setting.json", "r+", touch=True) as f:
            try:
                data = json.load(f)
            except:
                data = {}
            for k,v in load.items():
                self.app.values.set(k, data.setdefault(k, v))
            f.seek(0)
            f.truncate()
            json.dump(data, f, ensure_ascii=False, indent=4)

    def __init_value_init__(self, init:dict[str]):
        for k,v in init.items():
            self.app.values.set(k, v)

    def __init_value_save__(self, save:list[str]):
        for k in save:
            self.app.events.valueChange += (k, lambda k,_,v: self._valueSaver.save(k,v))

# class ModuleManager:
#     def __init__(self, event_bus):
#         self.event_bus = event_bus
#         self.loaded = {}
#         self.handlers = {}
#         self.threads = {}
#         self.tasks = {}

#         self.app = app

#         self.__init_info__()
#         self.__init_event__()
#         self.__init_layout__()

#     def __init_subclass__(cls, **kwargs):
#         super().__init_subclass__(**kwargs)
#         cls.__path__ = pathlib.Path(cls.__dict__['__init__'].__code__.co_filename).parent.name

#     def __init_event__(self):
#         for _, callback in inspect.getmembers(self, inspect.ismethod):
#             for eventData in getattr(callback.__func__, "__VRCUtil_Events__", []):
#                 getattr(self.app.events,eventData[0]).__iadd__(callback if len(eventData)==1 else (eventData[1],callback))

#             for path in getattr(callback.__func__, "__VRCUtil_OSCListen__", []):
#                 self.app.osc.addHandler(path, f"{callback.__name__}_{path}", callback)

#     def __init_layout__(self):
#         if (layoutPath:=MODULES_PATH/self.__path__/"Layout.xaml").exists():
#             try:
#                 self.__layout__ = pywebwinui3.util.loadPage(layoutPath)
#                 self.__layout__["attr"]["path"] = self.__path__
#                 self.app.addPage(pageData=self.__layout__)
#             except Exception as e:
#                 logger.error(f"Faild to load page: {layoutPath}\n{traceback.format_exc()}")
#                 self.app.notice(pywebwinui3.type.Status.Caution, f"Faild to load page {self.__name__}", str(e))

#         if (widgetPath:=MODULES_PATH/self.__path__/"Widget.xaml").exists():
#             try:
#                 self.__widget__ = pywebwinui3.util.loadPage(widgetPath)
#                 self.app.values.get("system_pages")[""]["child"][0]["child"][0]["child"].append(self.__widget__)
#             except Exception as e:
#                 logger.error(f"Faild to load widget: {widgetPath}\n{traceback.format_exc()}")
#                 self.app.notice(pywebwinui3.type.Status.Caution, f"Faild to load widget {self.__name__}", str(e))

#     def load(self, path, module_name):
#         module = self._load_module(path, module_name)
#         cls = getattr(module, module_name)

#         inst = cls()
#         self.loaded[module_name] = inst
#         self.handlers[module_name] = []
#         self.threads[module_name] = []
#         self.tasks[module_name] = []

#         inst.on_load(self)

#     def unload(self, module_name):
#         instance = self.loaded[module_name]

#         # 이벤트 제거
#         for event_name, handler in self.handlers[module_name]:
#             self.event_bus.off(event_name, handler)

#         # 태스크 / 스레드 종료
#         self._stop_all_threads(module_name)
#         self._stop_all_tasks(module_name)

#         # 모듈에서 자체 정리
#         instance.on_unload()

#         # 참조 제거
#         del self.loaded[module_name]
#         del self.handlers[module_name]
#         del self.threads[module_name]
#         del self.tasks[module_name]