import vdf
import winreg
from pathlib import Path

class Steam:
	def __init__(self):
		self.path = None
		self.libraryData = None

	def getSteamPath(self, cache=True) -> Path:
		try:
			if cache and self.path:
				return self.path
			with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Valve\Steam") as key:
				self.path = Path(winreg.QueryValueEx(key, "InstallPath")[0])
				return self.path
		except:
			return None

	def getLibraryData(self, cache=True) -> dict|None:
		try:
			if cache and self.libraryData:
				return self.libraryData
			data = vdf.load(open(self.getSteamPath()/"steamapps"/"libraryfolders.vdf", encoding="utf-8"))
			self.libraryData = {Path(item.get("path"))/"steamapps":list(item.get("apps",{}).keys()) for item in data.get("libraryfolders",{}).values()}
			return self.libraryData
		except:
			return None

	def findSteamAppPath(self, appid:str, additional:str = "") -> str:
		try:
			if (appLibrary:=[k for k, v in self.getLibraryData().items() if appid in v]):
				return str(appLibrary[0]/"common"/vdf.load(open(appLibrary[0]/f"appmanifest_{appid}.acf", encoding="utf-8")).get("AppState").get("installdir")/additional)
		except:
			return None
		
# print(Steam().findSteamAppPath("438100","UnityCrashHandler64.exe"))