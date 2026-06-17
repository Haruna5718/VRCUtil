WINDOW_NAME = "VRCUtil"
MUTEX_NAME = "Haruna5718.VRCUtil"
RELEASE_URL = "https://github.com/Haruna5718/VRCUtil/releases/latest"
RELEASE_API_URL = "https://api.github.com/repos/Haruna5718/VRCUtil/releases/latest"
UPDATE_CHECK_INTERVAL = 60 * 60

# Args ========================================

import argparse

parser = argparse.ArgumentParser()

parser.add_argument("--overlay", nargs=2, metavar=("PORT", "KEY"))
parser.add_argument("--debug", action="store_true")
parser.add_argument("--minimize", action="store_true")
parser.add_argument("--nogui", action="store_true")

args = parser.parse_args()

# Overlay ========================================

if (args.overlay):
    from vrcutil.overlay import _OverlayServer
    raise SystemExit(_OverlayServer().serve(int(args.overlay[0]), args.overlay[1]))

# Single ========================================

import ctypes
import os
import sys
from pathlib import Path

ERROR_ALREADY_EXISTS = 183
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

CreateMutexW = kernel32.CreateMutexW
CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
CreateMutexW.restype = ctypes.c_void_p

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [ctypes.c_void_p]
CloseHandle.restype = ctypes.c_bool

SetCurrentProcessExplicitAppUserModelID = shell32.SetCurrentProcessExplicitAppUserModelID
SetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.c_wchar_p]
SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long

SetCurrentProcessExplicitAppUserModelID(MUTEX_NAME)

mutexHandle = CreateMutexW(None, True, f"Local\\{MUTEX_NAME}")
if not mutexHandle:
    raise ctypes.WinError(ctypes.get_last_error())

if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
    hwnd = user32.FindWindowW(None, WINDOW_NAME)
    if hwnd:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
    CloseHandle(mutexHandle)
    sys.exit(0)

# Log ========================================

import logging

logging.getLogger("asyncio").setLevel(logging.INFO)
logging.getLogger("PIL.Image").setLevel(logging.INFO)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)-8s | %(asctime)s | %(name)-30s | %(message)s",
    datefmt="%H:%M:%S"
)

from Logger import open_log_window

# Setting ========================================

import pystray
import PIL.Image

from vrcutil.core import VRCUtil, Module, logger
from vrcutil.nogui import create_nogui_app

app = create_nogui_app(WINDOW_NAME, "VRCUtil.ico", Path(__file__).parent) if args.nogui else VRCUtil(WINDOW_NAME, "VRCUtil.ico")
window_runtime = app.api if args.nogui else app
app.values.set("vrcutil_debug", args.debug, False)
raw_window_destroy = window_runtime.destroy


class VRCUtilTray:
    def __init__(self, app: VRCUtil, no_gui: bool = False):
        self.app = app
        self.no_gui = bool(no_gui)
        self.icon = None

    def install(self) -> bool:
        if self.icon is not None:
            return True

        self.icon = pystray.Icon(
            WINDOW_NAME,
            PIL.Image.open(INSTALL_PATH / self.app.values.get("system_icon")),
            WINDOW_NAME,
            pystray.Menu(*self._menu_items()),
        )
        threading.Thread(target=self.icon.run, daemon=True).start()
        return True

    def _menu_items(self):
        if self.no_gui:
            return (
                pystray.MenuItem("Exit", self.exit_app),
            )

        return (
            pystray.MenuItem("Open", self.open_window, default=True),
            pystray.MenuItem("Exit", self.exit_app),
        )

    def uninstall(self):
        if self.icon is None:
            return
        icon = self.icon
        self.icon = None
        try:
            icon.visible = False
        except Exception:
            pass
        icon.stop()

    def set_enabled(self, enabled: bool):
        enabled = bool(enabled)
        if enabled:
            self.install()
        else:
            self.uninstall()

    def open_window(self, *_):
        window_runtime.show()
        window_runtime.restore()

    def exit_app(self, *_):
        target = terminate_process if self.no_gui else window_destroy
        threading.Thread(target=target, daemon=True).start()

tray = VRCUtilTray(app, no_gui=args.nogui)

def bind_destroy(target):
    window_runtime.destroy = target
    js_api = getattr(app, "api", None) if window_runtime is app else None
    if js_api is not None:
        js_api.destroy = target

def update_destroy_binding(enabled: bool):
    bind_destroy(window_runtime.hide if bool(enabled) else window_destroy)

from vrcutil import __version__, MODULES_PATH, INSTALL_PATH, DATA_PATH, PACKAGES_PATH, IS_COMPILED, EXECUTABLE, registry, steam
from vrcutil.file import SafeJson, BufferedJsonSaver

import threading

try:
    registry.setShortcutAppId(Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/VRCUtil.lnk", MUTEX_NAME)
except Exception:
    pass

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

settingSaver = BufferedJsonSaver(DATA_PATH/"Setting.json")

with SafeJson(DATA_PATH/"Setting.json") as setting:
    settingInit = {
        "system_pin": False,
        "system_theme": "system",
        "system_window_width": 900,
        "system_window_height": 600,
        "settings_useTray": True,
        "settings_osc_address": "127.0.0.1",
        "settings_osc_send": 9000,
        "settings_osc_receive": 0,
        "settings_autoStart": "0",
        "settings_checkUpdate": True
    }
    for k,v in settingInit.items():
        app.values.set(k, setting.data.setdefault(k, v), False)

    setting.save()

    app.events.valueChange += ("settings_*", lambda k, _, v: settingSaver.save(k, v))
    app.events.valueChange += ("system_theme", lambda k, _, v: settingSaver.save(k, v))
    app.events.valueChange += ("system_pin", lambda k, _, v: settingSaver.save(k, v))
    app.events.valueChange += ("system_window_width", lambda k, _, v: settingSaver.save(k, v))
    app.events.valueChange += ("system_window_height", lambda k, _, v: settingSaver.save(k, v))
    app.events.valueChange += ("settings_osc_address", initClient)
    app.events.valueChange += ("settings_osc_address", initServer)
    app.events.valueChange += ("settings_osc_send", initClient)
    app.events.valueChange += ("settings_osc_receive", initServer)

def save_window_size():
    if args.nogui:
        return

    try:
        width, height = window_runtime.get_window_size()
        width = int(width)
        height = int(height)
    except Exception:
        logger.debug("Failed to capture window size", exc_info=True)
        return

    app.values.set("system_window_width", width, False)
    app.values.set("system_window_height", height, False)

    try:
        with SafeJson(DATA_PATH/"Setting.json") as setting:
            setting.data["system_window_width"] = width
            setting.data["system_window_height"] = height
            setting.save()
    except Exception:
        logger.debug("Failed to persist window size", exc_info=True)

def window_destroy():
    save_window_size()
    raw_window_destroy()

import urllib.request
import subprocess
import tempfile
import shutil
import importlib.util
import site
import json
import traceback
from concurrent.futures import ThreadPoolExecutor, wait

from pywebwinui3.core import Status

_cleanup_done = False
_cleanup_lock = threading.Lock()

_notified_update_version = None
_update_check_lock = threading.Lock()
_update_check_stop = threading.Event()

@app.onValueChange("settings_checkUpdate")
def checkUpdate(*_):
    global _notified_update_version
    if app.values.get("settings_checkUpdate", False):
        if not _update_check_lock.acquire(blocking=False):
            return
        try:
            app.values.set("vrcutil_latest", "fetching")
            with urllib.request.urlopen(RELEASE_API_URL, timeout=5) as resp:
                latest_version = json.load(resp)["tag_name"]
                app.values.set("vrcutil_latest", latest_version)
                if latest_version != __version__ and latest_version != _notified_update_version:
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
                                "url": RELEASE_URL,
                            },
                            "child": [],
                        },
                    )
                return app.values.set("vrcutil_hasUpdate", Status.Attention if latest_version != __version__ else "")
        except:
            pass
        finally:
            _update_check_lock.release()
    app.values.set("vrcutil_latest", "unknown")

def updateCheckLoop():
    checkUpdate()
    while not _update_check_stop.wait(UPDATE_CHECK_INTERVAL):
        if app.values.get("settings_checkUpdate", False):
            checkUpdate()


@app.onValueChange("settings_autoStart")
def updateAutostart(*_):
    if IS_COMPILED:
        mode = str(app.values.get("settings_autoStart", "0"))

        try:
            manifest = INSTALL_PATH / "manifest.vrmanifest"
            if manifest.exists() and steam.hasSteamVR():
                vr = steam.VR(manifest)
                if mode == "1":
                    if not vr.installed or not vr.config.exists():
                        vr.install()
                    vr.setAutostart(True)
                elif vr.installed and vr.autostart:
                    vr.setAutostart(False)
        except Exception:
            logger.error("Failed to sync SteamVR autostart\n%s", traceback.format_exc())

        try:
            registry.Program.setStartupShortcutState("VRCUtil", mode=="3")
        except Exception:
            logger.error("Failed to sync system autostart\n%s", traceback.format_exc())

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
    if (entry:=sorted(path.glob("__init__*.pyd"))):
        return entry[0]

    if (entry := sorted(path.glob("__init__*.pyc"))):
        return entry[0]

    if (entry := path / "__init__.py").is_file():
        return entry

def moduleSetup(path:Path):
    try:
        entry = resolveModuleEntry(path)
        if entry is None:
            raise ImportError(f"Failed to find module entry for {path.name}")
        Spec = importlib.util.spec_from_file_location(path.name, entry, submodule_search_locations=[str(path)],)
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
    packagesPath = str(PACKAGES_PATH)
    if packagesPath not in sys.path:
        site.addsitedir(packagesPath)
    initClient()
    initServer(direct=True)
    loadModule()
    app.start_process_monitor()

GlobalTempDir = None
_background_tasks_started = False

@app.onValueChange("vrcutil_restart")
def restart(*_):
    subprocess.Popen(
        ["cmd", "/c", f"timeout /T 1 >nul & {EXECUTABLE}{' --debug' if args.debug else ''}"],
        cwd=INSTALL_PATH,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    window_destroy()

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

    if IS_COMPILED:
        modulePath = MODULES_PATH/moduleName
        GlobalTempDir = GlobalTempDir or Path(tempfile.mkdtemp())
        shutil.move(str(modulePath), str(GlobalTempDir/modulePath.name))

    app.notice(Status.Attention, "Restart required", f"please restart for remove {moduleName} completly",{"tag":"Button","text":"Restart","attr":{"value":"vrcutil_restart"},"child":[]})

@app.onSetup()
def startBackgroundTasks():
    global _background_tasks_started
    if _background_tasks_started:
        return
    _background_tasks_started = True
    threading.Thread(target=updateCheckLoop, daemon=True).start()

def CloseServices():
    global _cleanup_done
    with _cleanup_lock:
        if _cleanup_done:
            return
        _cleanup_done = True

    _update_check_stop.set()
    try:
        tray.uninstall()
    except:
        pass
    try:
        app.osc.stop()
    except:
        pass
    try:
        app.stop_process_monitor()
    except:
        pass
    try:
        if GlobalTempDir:
            subprocess.Popen(["cmd", "/c", f"timeout /T 5 >nul & rmdir /S /Q {GlobalTempDir}"], creationflags=subprocess.CREATE_NO_WINDOW)
    except:
        pass
    try:
        CloseHandle(mutexHandle)
    except Exception:
        pass

app.onExit()(CloseServices)

@app.onValueChange("vrcutil_openLog")
def openlog(*_):
    open_log_window()

@app.onValueChange("settings_useTray")
def updateTray(*_, after=None):
    if args.nogui:
        return
    enabled = bool(app.values.get("settings_useTray", True) if after is None else after)
    tray.set_enabled(enabled)
    update_destroy_binding(enabled)

threading.Thread(target=bootstrapRuntime, daemon=True).start()
startBackgroundTasks()

def terminate_process():
    CloseServices()
    os._exit(0)

if args.nogui:
    bind_destroy(terminate_process)
    window_destroy = terminate_process
    tray.set_enabled(True)
    app.start(debug=args.debug)
    threading.Event().wait()
else:
    tray_enabled = bool(app.values.get("settings_useTray", True))
    tray.set_enabled(tray_enabled)
    update_destroy_binding(tray_enabled)
    app.start(
        debug=args.debug,
        hidden=tray_enabled and args.minimize,
        width=app.values.get("system_window_width", 900),
        height=app.values.get("system_window_height", 600),
    )
