import json
import pathlib
import logging
import inspect
import threading
import traceback

from PySide6.QtCore import Qt
import pywebwinui3.core
import pywebwinui3.util
import pywebwinui3.type

from . import event, file, osc, steam, wmi, __version__, INSTALL_PATH, DATA_PATH, MODULES_PATH

logger = logging.getLogger("vrcutil")


class RuntimeProcessStateManager:
    def __init__(self, app: "VRCUtil"):
        self.app = app
        self.processWatcher = wmi.ProcessWatcher()
        self._registered = False
        self._started = False

    def _register_targets(self):
        if self._registered:
            return

        try:
            self.processWatcher.addTarget(steam.findApp("438100") / "UnityCrashHandler64.exe", self._on_vrchat)
        except Exception:
            logger.debug("VRChat process target unavailable\n%s", traceback.format_exc())

        try:
            self.processWatcher.addTarget(steam.findApp("250820") / "bin/win64/vrcompositor.exe", self._on_steamvr)
        except Exception:
            logger.debug("SteamVR process target unavailable\n%s", traceback.format_exc())

        self._registered = True

    def start(self):
        if self._started:
            return

        self._register_targets()
        if not self.processWatcher.target:
            logger.info("Runtime process watcher skipped: no targets registered")
            return

        self.processWatcher.start(checkCurrent=True)
        self._started = True
        logger.info("Runtime process watcher started")

    def stop(self):
        if not self._started:
            return

        self.processWatcher.stop()
        self._started = False
        logger.info("Runtime process watcher stopped")

    def _on_steamvr(self, _, state):
        self.app.syncProcessState({"steamvr": state})

    def _on_vrchat(self, _, state):
        self.app.syncProcessState({"vrchat": state})

class VRCUtil(pywebwinui3.core.MainWindow):
    def __init__(self, title, icon):
        super().__init__(title, icon)
        self.state_endpoint: str | None = None
        self.process_state = RuntimeProcessStateManager(self)
        self._opengl = None
        self._page_lock = threading.RLock()
        self._module_lock = threading.RLock()
        self._dashboard_widget_sort_keys: dict[int, tuple[str, str]] = {}

        self.osc = osc.EasyOSC(title, init=False)
        self.__initVRCUtil__(title, icon)

    def resolve_path(self, value):
        if value is None:
            return None

        path = pathlib.Path(value)
        if path.is_absolute():
            return path

        install_candidate = INSTALL_PATH / path
        if install_candidate.exists() or install_candidate.parent.exists():
            return install_candidate.resolve()

        data_candidate = DATA_PATH / path
        if data_candidate.exists() or data_candidate.parent.exists():
            return data_candidate.resolve()

        return super().resolve_path(value)

    def __initVRCUtil__(self, title, icon):
        self.Modules:dict[str,Module] = {}
        
        self.addPage("Dashboard.xaml")
        self.addSettings("Settings.xaml")

        self.values.set("vrcutil_version", __version__, False)
        self.values.set("steamvr_state", False, False)
        self.values.set("vrchat_state", False, False)

    @property
    def opengl(self):
        if self._opengl is None:
            from . import overlay

            self._opengl = overlay.OpenGLManager()
        return self._opengl

    def start_process_monitor(self):
        self.process_state.start()

    def stop_process_monitor(self):
        self.process_state.stop()

    def _dashboard_widget_container(self) -> list:
        return self.values["system_pages"][""]["child"][0]["child"][0]["child"]

    def sync_pages(self):
        self.values._sync("system_pages", None, self.values["system_pages"], True)

    def add_module_widget(self, widget: dict, module_name: str | None, module_path: str | None):
        sort_key = (
            str(module_name or module_path or "").casefold(),
            str(module_path or module_name or "").casefold(),
        )

        with self._page_lock:
            container = self._dashboard_widget_container()
            self._dashboard_widget_sort_keys[id(widget)] = sort_key
            container.append(widget)
            container.sort(key=lambda item: self._dashboard_widget_sort_keys.get(id(item), ("", "")))
            self.sync_pages()

    def remove_module_widget(self, widget: dict):
        with self._page_lock:
            container = self._dashboard_widget_container()
            if widget in container:
                container.remove(widget)
            self._dashboard_widget_sort_keys.pop(id(widget), None)
            self.sync_pages()

    def register_module(self, module_key: str, module_class: "Module"):
        module_info = [
            module_key,
            module_class.__name__,
            module_class.__version__,
            module_class.__description__,
            module_class.__urls__,
        ]

        with self._module_lock:
            self.Modules[module_key] = module_class
            modules = [item for item in self.values.get("vrcutil_modules", []) or [] if item[0] != module_key]
            modules.append(module_info)
            modules.sort(key=lambda item: (str(item[1] or item[0] or "").casefold(), str(item[0] or "").casefold()))
            self.values.set("vrcutil_modules", modules)

    def addSettings(self, pageFile: str | pathlib.Path | None = None, pageData: dict | None = None):
        if pageFile and not pageData:
            pageData = pywebwinui3.util.loadPage(self.resolve_path(pageFile))
        with self._page_lock:
            return super().addSettings(pageData=pageData)

    def addPage(self, pageFile: str | pathlib.Path | None = None, pageData: dict | None = None):
        if pageFile and not pageData:
            pageData = pywebwinui3.util.loadPage(self.resolve_path(pageFile))
        with self._page_lock:
            return super().addPage(pageData=pageData)

    def syncProcessState(self, data: dict[str, object]):
        logger.info("Sync state received: %s", data)
        for key, value in data.items():
            state = bool(value)
            value_key = f"{key}_state"
            before = bool(self.values.get(value_key, False))

            if key == "steamvr" and before != state:
                try:
                    from . import overlay

                    if state:
                        logger.info("try to init openvr...")
                        overlay.Manager.openvr()
                        logger.info("openvr initialized")
                    else:
                        logger.info("try to stop openvr...")
                        overlay.Manager.stop()
                        logger.info("openvr stopped")
                except Exception:
                    logger.error("Failed to sync OpenVR state\n%s", traceback.format_exc())

            self.values.set(value_key, state)

    def start(self, debug=False, minimized=False, onTop=None, min_width=None, min_height=None):
        if onTop is not None:
            self.values.set("system_pin", bool(onTop), False)
        if min_width is not None or min_height is not None:
            self.sync_window_min_size(
                self._window_min_width if min_width is None else min_width,
                self._window_min_height if min_height is None else min_height,
                sync=False,
            )

        self.api.ensure_runtime(debug=debug)

        if minimized and self.api._window is not None:
            self.api._window.setWindowState(self.api._window.windowState() | Qt.WindowMinimized)

        super().start(debug)


class Module:
    def __init__(self, app:VRCUtil):
        self.app = app

        self.__init_info__()
        self.__init_event__()
        self.__init_layout__()
        self.__init_widget__()

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

    def __init_widget__(self):
        if (widgetPath:=MODULES_PATH/self.__path__/"Widget.xaml").exists():
            try:
                self.__widget__ = pywebwinui3.util.loadPage(widgetPath)
                self.app.add_module_widget(self.__widget__, self.__name__ or self.__path__, self.__path__)
            except Exception as e:
                logger.error(f"Faild to load widget: {widgetPath}\n{traceback.format_exc()}")
                self.app.notice(pywebwinui3.type.Status.Caution, f"Faild to load widget {self.__name__}", str(e))

class EasyModule(Module):
    def __init__(self, app:VRCUtil, load:dict[str]=None, init:dict[str]=None, save:list[str]=None):
        self.app = app

        if load:
            self.__init_value_load__(load)
        if init:
            self.__init_value_init__(init)

        super().__init__(app)

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