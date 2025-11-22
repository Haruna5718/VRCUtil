import threading
import pywebwinui3
import pathlib
import bottle
import sys
import os
import webview

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
    def __init__(self, title):
        super().__init__(title)
        self.basePath = INSTALL_PATH

        threading.Thread(target=self.__initVRCUtil__, daemon=True).start()

    def __initVRCUtil__(self):

        self.steam = steam.VR(INSTALL_PATH/"manifest.vrmanifest")
        self.osc:osc.EasyOSC = None
        self.Modules = {}
        self.eventStatus = {}

        self.events.exit = self.api._window.events.closed
        self.events.SteamVRStart = pywebwinui3.event.Event()
        self.events.SteamVRStop = pywebwinui3.event.Event()
        self.events.VRChatStart = pywebwinui3.event.Event()
        self.events.VRChatStop = pywebwinui3.event.Event()
        
        self.addPage("Dashboard.xaml")
        self.addSettings("Settings.xaml")

    def start(self, debug=False):
        @self.server.route('/')
        @self.server.route('/PYWEBWINUI3/<filepath:path>')
        def web(filepath=None):
            return bottle.static_file(filepath or "index.html", root=str(INSTALL_PATH/("_internal/pywebwinui3/web/PYWEBWINUI3" if filepath else "_internal/pywebwinui3/web")))
        
        @self.server.route('/<filepath:path>')
        def file(filepath):
            if (DATA_PATH/filepath).is_file():
                return bottle.static_file(filepath, root=str(DATA_PATH))
            if (INSTALL_PATH/filepath).is_file():
                return bottle.static_file(filepath, root=str(INSTALL_PATH))
            
        webview.start(self._setup,debug=debug)

class Module:
	def __init__(self):
		pass
