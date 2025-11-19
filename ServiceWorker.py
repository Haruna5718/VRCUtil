import requests
import time
import json
import logging
import subprocess

from vrcutil.file import SafeRead
from vrcutil import wmi, steam, INSTALL_PATH

logger = logging.getLogger("vrcutil.serviceworker")

# ----------------------------

class StateManager:
	def __init__(self):
		self.processWatcher = wmi.ProcessWatcher()
		self.state = {
			"SteamVR": False,
			"VRChat": False
		}
		self.syncPath = None
		self.synced = False
		self.processWatcher.addTarget(INSTALL_PATH/"VRCUtil.exe", self.onVRCUtil)
		try:
			self.processWatcher.addTarget(steam.findApp("438100")/"UnityCrashHandler64.exe", self.onVRChat)
		except:
			pass
		try:
			self.processWatcher.addTarget(steam.findApp("250820")/"bin/win64/vrcompositor.exe", self.onSteamVR)
		except:
			pass
		self.processWatcher.start(checkCurrent=True)

	def syncState(self):
		if not self.synced and self.syncPath:
			self.synced = True
			try:
				for _ in range(5):
					try:
						return requests.post(self.syncPath, json=self.state)
					except:
						logger.warning(f"Failed to connect to VRCUtil instance for state sync \"{self.syncPath}\". Retrying...")
						time.sleep(1)
						self.onVRCUtil(_, True)
			finally:
				self.synced = False
			logger.error(f"Failed to connect to VRCUtil instance for state sync.")
			self.syncPath = None

	def onVRCUtil(self, path, state):
		if state:
			self.syncPath = SafeRead(INSTALL_PATH/"VRCUtil.lock")
			print(self.syncPath)
			self.syncState()
		else:
			if not (self.syncPath and wmi.Check(path)):
				self.syncPath = None


	def onVRChat(self, _, state):
		if self.state["VRChat"]==state:
			return
		self.state["VRChat"] = state
		self.syncState()
		if state and json.loads(SafeRead(INSTALL_PATH/"VRCUtil.lock")).get("settings.autoStart","0") == "2":
			subprocess.Popen([str(INSTALL_PATH/"VRCUtil.exe")])

	def onSteamVR(self, _, state):
		if self.state["SteamVR"]==state:
			return
		self.state["SteamVR"] = state
		self.syncState()


if __name__ == "__main__" and not wmi.Check(INSTALL_PATH/"ServiceWorker.exe"):
	logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)-8s | %(asctime)s | %(name)-30s | %(message)s",
        datefmt="%H:%M:%S"
    )
	stateManager = StateManager()
	while True:
		try:
			time.sleep(1)
		except KeyboardInterrupt:
			break
	stateManager.processWatcher.stop()
	logger.info("ServiceWorker exited.")

# pyinstaller --onefile ServiceWorker.py