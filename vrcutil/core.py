import json
import pathlib
import logging
import threading
import traceback
from contextlib import contextmanager
import pywebwinui3.core
import pywebwinui3.util
import pywebwinui3.type

from . import file, osc, steam, wmi, __version__, INSTALL_PATH, DATA_PATH, MODULES_PATH

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
        self._resource_roots.extend(
            [
                ("install", INSTALL_PATH.resolve()),
                ("data", DATA_PATH.resolve()),
            ]
        )
        self.process_state = RuntimeProcessStateManager(self)
        self._opengl = None
        self._page_lock = threading.RLock()
        self._module_lock = threading.RLock()
        self._page_sync_depth = 0
        self._page_sync_dirty = False
        self._module_sync_depth = 0
        self._module_sync_dirty = False
        self._module_infos: dict[str, list] = {}
        self._dashboard_widget_sort_keys: dict[int, tuple[str, str]] = {}
        self._steamvr_overlay_lock = threading.Lock()
        self._steamvr_overlay_pending: bool | None = None
        self._steamvr_overlay_worker: threading.Thread | None = None

        self.osc = osc.EasyOSC(title, init=False)
        self.__initVRCUtil__()

    def resolve_path(self, value):
        if value is None:
            return None

        path = pathlib.Path(value)
        if path.is_absolute():
            return path

        if path.parts and path.parts[0] == "Modules":
            data_path = DATA_PATH / path
            if data_path.exists():
                return data_path.resolve()

        install_path = INSTALL_PATH / path
        if install_path.exists():
            return install_path.resolve()

        data_path = DATA_PATH / path
        if data_path.exists():
            return data_path.resolve()

        return install_path.resolve()

    def __initVRCUtil__(self):
        self.Modules:dict[str,Module] = {}

        with self.batch_ui_sync():
            self.addPage(INSTALL_PATH / "Dashboard.xaml")
            self.addSettings(INSTALL_PATH / "Settings.xaml")

            self.values.set("vrcutil_modules", [], False)
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

    def _request_page_sync(self):
        with self._page_lock:
            if self._page_sync_depth:
                self._page_sync_dirty = True
                return
        self.sync_pages()

    def _sync_registered_modules(self):
        self.values.set(
            "vrcutil_modules",
            sorted(
                self._module_infos.values(),
                key=lambda item: (str(item[1] or item[0] or "").casefold(), str(item[0] or "").casefold()),
            ),
        )

    def _request_module_sync(self):
        with self._module_lock:
            if self._module_sync_depth:
                self._module_sync_dirty = True
                return
        self._sync_registered_modules()

    @contextmanager
    def batch_ui_sync(self):
        with self._page_lock:
            self._page_sync_depth += 1
        with self._module_lock:
            self._module_sync_depth += 1

        try:
            yield
        finally:
            should_sync_pages = False
            should_sync_modules = False

            with self._page_lock:
                self._page_sync_depth = max(0, self._page_sync_depth - 1)
                if self._page_sync_depth == 0 and self._page_sync_dirty:
                    self._page_sync_dirty = False
                    should_sync_pages = True

            with self._module_lock:
                self._module_sync_depth = max(0, self._module_sync_depth - 1)
                if self._module_sync_depth == 0 and self._module_sync_dirty:
                    self._module_sync_dirty = False
                    should_sync_modules = True

            if should_sync_pages:
                self.sync_pages()
            if should_sync_modules:
                self._sync_registered_modules()

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
        self._request_page_sync()

    def remove_module_widget(self, widget: dict):
        changed = False
        with self._page_lock:
            container = self._dashboard_widget_container()
            if widget in container:
                container.remove(widget)
                changed = True
            self._dashboard_widget_sort_keys.pop(id(widget), None)
        if changed:
            self._request_page_sync()

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
            self._module_infos[module_key] = module_info
        self._request_module_sync()

    def unregister_module(self, module_key: str):
        with self._module_lock:
            self.Modules.pop(module_key, None)
            self._module_infos.pop(module_key, None)
        self._request_module_sync()

    def _schedule_overlay_sync(self, state: bool):
        with self._steamvr_overlay_lock:
            self._steamvr_overlay_pending = state
            if self._steamvr_overlay_worker and self._steamvr_overlay_worker.is_alive():
                return

            self._steamvr_overlay_worker = threading.Thread(
                target=self._run_overlay_sync,
                daemon=True,
            )
            self._steamvr_overlay_worker.start()

    def _run_overlay_sync(self):
        from . import overlay

        while True:
            with self._steamvr_overlay_lock:
                state = self._steamvr_overlay_pending
                self._steamvr_overlay_pending = None

            if state is None:
                with self._steamvr_overlay_lock:
                    self._steamvr_overlay_worker = None
                return

            try:
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

            with self._steamvr_overlay_lock:
                if self._steamvr_overlay_pending is None:
                    self._steamvr_overlay_worker = None
                    return

    def syncProcessState(self, data: dict[str, object]):
        logger.info("Sync state received: %s", data)
        for key, value in data.items():
            state = bool(value)
            value_key = f"{key}_state"
            before = bool(self.values.get(value_key, False))

            if key == "steamvr" and before != state:
                self._schedule_overlay_sync(state)

            self.values.set(value_key, state)

    def start(
        self,
        debug=False,
        *,
        hidden=False,
        onTop=None,
        width=None,
        height=None,
        min_width=800,
        min_height=500,
    ):
        if onTop is not None:
            self.values.set("system_pin", bool(onTop), False)

        super().start(
            debug=debug,
            hidden=hidden,
            on_top=bool(self.values.get("system_pin", False)),
            width=width,
            height=height,
            min_width=min_width,
            min_height=min_height,
        )


class Module:
    _event_binding_cache: dict[type, list[tuple[str, tuple, tuple]]] = {}

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
        self.__info__:dict[str,str|list[dict[str,str]]] = json.loads(file.SafeRead(MODULES_PATH / self.__path__ / "module.json"))
        self.__name__:str|None                 = self.__info__.get("name")
        self.__version__:str|None              = self.__info__.get("version")
        self.__author__:str|None               = self.__info__.get("author")
        self.__description__:str|None          = self.__info__.get("description")
        self.__urls__:list[dict[str,str]]|None = self.__info__.get("urls")
        if logger.isEnabledFor(logging.INFO):
            logger.info(
                "Module loaded %s\n%s| ├─ Path: %s\n%s| ├─ Version: %s\n%s| ├─ Author: %s\n%s| ├─ Description: %s",
                self.__name__ or "Unknown",
                " " * 53,
                self.__path__,
                " " * 53,
                self.__version__ or "Unknown",
                " " * 53,
                self.__author__ or "Unknown",
                " " * 53,
                self.__description__ or "Unknown",
            )

    @classmethod
    def _get_event_bindings(cls):
        cached = cls._event_binding_cache.get(cls)
        if cached is not None:
            return cached

        bindings = []
        for name, attr in cls.__dict__.items():
            func = attr
            if isinstance(attr, (staticmethod, classmethod)):
                func = attr.__func__

            event_data = tuple(getattr(func, "__VRCUtil_Events__", ()))
            osc_paths = tuple(getattr(func, "__VRCUtil_OSCListen__", ()))
            if event_data or osc_paths:
                bindings.append((name, event_data, osc_paths))

        cls._event_binding_cache[cls] = bindings
        return bindings

    def __init_event__(self):
        for name, events, osc_paths in self._get_event_bindings():
            callback = getattr(self, name)
            for eventData in events:
                getattr(self.app.events, eventData[0]).__iadd__(callback if len(eventData) == 1 else (eventData[1], callback))
            for path in osc_paths:
                self.app.osc.addHandler(path, f"{callback.__name__}_{path}", callback)

    def __init_layout__(self):
        if (layoutPath:=MODULES_PATH / self.__path__ / "Layout.xaml").exists():
            try:
                self.__layout__ = pywebwinui3.util.loadPage(layoutPath)
                self.__layout__["attr"]["path"] = self.__path__
                self.app.addPage(pageData=self.__layout__)
            except Exception as e:
                logger.error(f"Faild to load page: {layoutPath}\n{traceback.format_exc()}")
                self.app.notice(pywebwinui3.type.Status.Caution, f"Faild to load page {self.__name__}", str(e))

    def __init_widget__(self):
        if (widgetPath:=MODULES_PATH / self.__path__ / "Widget.xaml").exists():
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
            self._valueSaver = file.BufferedJsonSaver(MODULES_PATH / self.__path__ / "Setting.json")
            self.__init_value_save__(save)

    def __init_value_load__(self, load:dict[str]):
        with file.SafeOpen(MODULES_PATH / self.__path__ / "Setting.json", "r+", touch=True) as f:
            try:
                data = json.load(f)
            except:
                data = {}
            changed = False
            for k,v in load.items():
                if k not in data:
                    data[k] = v
                    changed = True
                self.app.values.set(k, data[k])
            if changed:
                f.seek(0)
                f.truncate()
                json.dump(data, f, ensure_ascii=False, indent=4)

    def __init_value_init__(self, init:dict[str]):
        for k,v in init.items():
            self.app.values.set(k, v)

    def __init_value_save__(self, save:list[str]):
        for k in save:
            self.app.events.valueChange += (k, lambda k,_,v: self._valueSaver.save(k,v))
