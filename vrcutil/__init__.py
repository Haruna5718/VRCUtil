import threading
import pywebwinui3
import pathlib
import sys


__version__ = '3.0.0-dev'

IS_DEBUG = not getattr(sys, 'frozen', False)

# INSTALL_PATH = pathlib.Path(__file__).parent.parent.resolve() if IS_DEBUG else pathlib.Path("C:/Program Files/VRCUtil/")
# DATA_PATH = INSTALL_PATH if IS_DEBUG else pathlib.Path.home()/"AppData"/"Local"/"VRCUtil"
# MODULES_PATH = DATA_PATH/"Modules"

INSTALL_PATH = pathlib.Path(r"C:\Users\Haruna5718\OneDrive\code\Project\VRCUtil\dist\VRCUtil")
DATA_PATH = INSTALL_PATH
MODULES_PATH = INSTALL_PATH/"Modules"


from . import event, file, osc, pip, registry, steam, wmi

__all__ = ["event", "file", "osc", "pip", "registry", "steam", "wmi"]


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

class Module:
	def __init__(self):
		pass
