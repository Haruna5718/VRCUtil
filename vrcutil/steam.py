import vdf
import json
import logging
from pathlib import Path

from .file import SafeRead
from . import registry

logger = logging.getLogger("vrcutil.steam")

_installPath = None
_libraryData = None

def installPath() -> Path:
	global _installPath
	if not _installPath:
		_installPath = Path(registry.read(registry.targetType.localMachine, r"Software\WOW6432Node\Valve\Steam", "installPath")[0])
		logger.debug(f"Steam installed path checked: {_installPath}")
	return _installPath
		
def libraryData() -> dict:
	global _libraryData
	if not _libraryData:
		data = vdf.load(open(installPath()/"steamapps"/"libraryfolders.vdf", encoding="utf-8"))
		_libraryData = {Path(item.get("path"))/"steamapps":list(item.get("apps",{}).keys()) for item in data.get("libraryfolders",{}).values()}
		logger.debug(f"Steam library data collected ({len(_libraryData)})")
	return _libraryData

def findApp(appid:str) -> str:
	if (appLibrary:=[k for k, v in libraryData().items() if appid in v]):
		appPath = appLibrary[0]/"common"/vdf.load(open(appLibrary[0]/f"appmanifest_{appid}.acf", encoding="utf-8")).get("AppState").get("installdir")
		logger.debug(f"Find app path: {appid} {appPath}")
		return appPath

class VR:
	VRCONFIG_DIR = "config/appconfig.json"
	APPCONFIG_DIR = "config/vrappconfig"
	def __init__(self, manifest:Path|str):
		self.manifest = Path(manifest)
		self._manifestData = None
		self._name = None
		self._config = None
	
	@property
	def info(self) -> dict:
		self._manifestData = self._manifestData or json.loads(SafeRead(self.manifest))
		return self._manifestData
	
	@property
	def name(self) -> str:
		self._name = self._name or self.info['applications'][0]['name']
		return self._name

	@property
	def config(self) -> Path:
		self._config = self._config or installPath()/self.APPCONFIG_DIR/f"{self.name}.vrappconfig"
		return self._config
	
	def setAutostart(self, state:bool):
		if not self.config.exists():
			self.install()

		appConfigData:dict = json.loads(SafeRead(self.config) or '{"last_launch_time": "0"}')
		with open(self.config, "w") as file:
			appConfigData["autolaunch"] = state
			json.dump(appConfigData, file, indent=4)

		logger.info(f"SteamVR app autolaunch setted: {self.name} {state}")

		return state
		
	def install(self):
		configData = json.loads(SafeRead(installPath()/self.VRCONFIG_DIR))
		if str(self.manifest) not in configData["manifest_installPaths"]:
			with open(installPath()/self.VRCONFIG_DIR, "w") as file:
				configData["manifest_installPaths"].append(str(self.manifest))
				json.dump(configData, file, indent=4)

		(self.config).touch()
		self.setAutostart(False)

		logger.info(f"SteamVR app registed: {self.name} {self.manifest}")
	
	def uninstall(self):
		configData = json.loads(SafeRead(installPath()/self.VRCONFIG_DIR))
		if str(self.manifest) in configData["manifest_installPaths"]:
			with open(installPath()/self.VRCONFIG_DIR, "w") as file:
				configData["manifest_installPaths"].remove(str(self.manifest))
				json.dump(configData, file, indent=4)

		(self.config).unlink(missing_ok=True)

		logger.info(f"SteamVR app unregisted: {self.name} {self.manifest}")