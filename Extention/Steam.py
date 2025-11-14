import vdf
import json
import winreg
import logging
import threading
from pathlib import Path

logger = logging.getLogger("vrcutil.steam.connector")

class Steam:
	def __init__(self):
		self._path = None
		self._libraryData = None

	@property
	def path(self):
		return self._path or self._getSteamPath()
	
	@property
	def libraryData(self):
		return self._libraryData or self._getLibraryData()

	def _getSteamPath(self) -> Path:
		with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Valve\Steam") as key:
			self._path = Path(winreg.QueryValueEx(key, "InstallPath")[0])
			logger.debug(f"Steam installed path checked: {self._path}")
			return self._path

	def _getLibraryData(self) -> dict:
		data = vdf.load(open(self.path/"steamapps"/"libraryfolders.vdf", encoding="utf-8"))
		self._libraryData = {Path(item.get("path"))/"steamapps":list(item.get("apps",{}).keys()) for item in data.get("libraryfolders",{}).values()}
		logger.debug(f"Steam library data collected ({len(self._libraryData)})")
		return self._libraryData

	def findSteamAppPath(self, appid:str) -> str:
		if (appLibrary:=[k for k, v in self.libraryData.items() if appid in v]):
			appPath = appLibrary[0]/"common"/vdf.load(open(appLibrary[0]/f"appmanifest_{appid}.acf", encoding="utf-8")).get("AppState").get("installdir")
			logger.debug(f"Find app path: {appid} {appPath}")
			return appPath
		
	def setSteamVRAutostart(self, state:bool, appName:str, appPath:Path|str=None):
		appConfigPath = self.path/"config"/"vrappconfig"/f"{appName}.vrappconfig"
		if not appConfigPath.exists() and appPath:
			self.installSteamVRApp(appPath,appName)
		with open(appConfigPath, "r+") as file:
			try:
				data = json.load(file)
			except:
				data = {"last_launch_time": "0"}

			data["autolaunch"] = state

			file.seek(0)
			file.truncate()

			json.dump(data, file, indent=4)
			logger.info(f"SteamVR app autolaunch setted: {appName} {state}")
		return state
		
	def installSteamVRApp(self, appPath:Path|str, appName:str):
		vrmanifestPath = Path(appPath)/'manifest.vrmanifest'
		(self.path/"config"/"vrappconfig"/f"{appName}.vrappconfig").touch()

		threading.Thread(target=self.setSteamVRAutostart, args=(False,)).start()

		with open(self.path/"config"/"appconfig.json", "r+") as file:
			data = json.load(file)

			if str(vrmanifestPath) not in data["manifest_paths"]:
				data["manifest_paths"].append(str(vrmanifestPath))
				file.seek(0)
				file.truncate()
				json.dump(data, file, indent=4)
		logger.info(f"SteamVR app registed: {appName} {appPath}")
	
	def uninstallSteamVRApp(self, appPath:Path|str, appName:str):
		vrmanifestPath = Path(appPath)/'manifest.vrmanifest'
		(self.path/"config"/"vrappconfig"/f"{appName}.vrappconfig").unlink(missing_ok=True)
		with open(self.path/"config"/"appconfig.json", "r+") as file:
			data = json.load(file)

			if str(vrmanifestPath) in data["manifest_paths"]:
				data["manifest_paths"].remove(str(vrmanifestPath))
				file.seek(0)
				file.truncate()
				json.dump(data, file, indent=4)
		logger.info(f"SteamVR app unregisted: {appName} {appPath}")