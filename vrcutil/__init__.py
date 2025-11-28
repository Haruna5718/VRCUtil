import threading
import pywebwinui3
import pathlib
import bottle
import sys
import os
import webview
import pystray
import PIL.Image

__version__ = '3.0.0-dev'

IS_DEBUG = not getattr(sys, 'frozen', False)

if IS_DEBUG:
    INSTALL_PATH = pathlib.Path(__file__).resolve().parent.parent
    DATA_PATH = INSTALL_PATH
else:
    INSTALL_PATH = pathlib.Path(sys.executable).resolve().parent
    DATA_PATH = pathlib.Path(os.environ["APPDATA"])/"VRCUtil"

MODULES_PATH = DATA_PATH/"Modules"


from . import event, file, osc, registry, steam, wmi

__all__ = ["event", "file", "osc", "registry", "steam", "wmi"]


class VRCUtil(pywebwinui3.MainWindow):
    def __init__(self, title, icon):
        super().__init__(title)
        self.basePath = INSTALL_PATH

        self.osc = osc.EasyOSC(title, init=False)

        threading.Thread(target=self.__initVRCUtil__, args=(title, icon,), daemon=True).start()

    def __initVRCUtil__(self, title, icon):
        self.api.minimize = self.api._window.minimize
        self.api.destroy = self.api._window.hide
        self.api._window.hidden = True

        self.steam = steam.VR(INSTALL_PATH/"manifest.vrmanifest")
        
        self.Modules = {}
        self.eventStatus = {}

        self.events.exit = self.api._window.events.closed
        self.events.SteamVRStart = pywebwinui3.event.Event()
        self.events.SteamVRStop = pywebwinui3.event.Event()
        self.events.VRChatStart = pywebwinui3.event.Event()
        self.events.VRChatStop = pywebwinui3.event.Event()
        
        self.addPage("Dashboard.xaml")
        self.addSettings("Settings.xaml")

        self.setValue("vrcutil.version", __version__)
        self.setValue("system.icon", icon)
        self.tray = VRCUtilTray(self, title, icon, start=True)

    def start(self, debug=False, minimized=False, onTop=False):
        WEB_PATH = pathlib.Path(pywebwinui3.__file__).parent

        @self.server.route('/')
        @self.server.route('/PYWEBWINUI3/<filepath:path>')
        def web(filepath=None):
            return bottle.static_file(filepath or "index.html", root=str(WEB_PATH/("web/PYWEBWINUI3" if filepath else "web")))
        
        @self.server.route('/<filepath:path>')
        def file(filepath):
            if (DATA_PATH/filepath).is_file():
                return bottle.static_file(filepath, root=str(DATA_PATH))
            if (INSTALL_PATH/filepath).is_file():
                return bottle.static_file(filepath, root=str(INSTALL_PATH))
            
        self.api._window.on_top = onTop
        self.api._window.hidden = minimized

        webview.start(self._setup, debug=debug)

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
	def __init__(self):
		pass
