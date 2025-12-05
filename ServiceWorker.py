from vrcutil import wmi, steam, INSTALL_PATH,DATA_PATH
import sys

if "debug" in sys.argv:
	import ctypes
	ctypes.windll.kernel32.AllocConsole()
	sys.stdout = open("CONOUT$", "w")
	sys.stderr = open("CONOUT$", "w")
	sys.stdin  = open("CONIN$", "r")

elif wmi.Check(INSTALL_PATH/"ServiceWorker.exe")>1:
	sys.exit(1)

import subprocess
import json
import requests
import time
import logging
import enum

from vrcutil.file import SafeRead

logger = logging.getLogger("vrcutil.serviceworker")

# ----------------------------

class AutostartCondition(enum.IntEnum):
	Disable="0"
	SteamVR="1"
	VRChat="2"
	StartUp="3"

def VRCUtilAutostart(Condition:AutostartCondition):
	try:
		if json.loads(SafeRead(DATA_PATH/"Setting.json")).get("settings_autoStart",AutostartCondition.Disable) == Condition:
			subprocess.Popen([str(INSTALL_PATH/"VRCUtil.exe"), "auto"])
			logger.info(f"VRCUtil launched ({Condition.name})")
	except:
		logger.error("Failed to check VRCUtil autostart setting")

class StateManager:
	def __init__(self):
		self.processWatcher = wmi.ProcessWatcher()
		self.state = {
			"steamvr": False,
			"vrchat": False
		}
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

		VRCUtilAutostart(AutostartCondition.StartUp)

	def syncState(self):
		if not self.synced and wmi.Check(INSTALL_PATH/"VRCUtil.exe"):
			self.synced = True
			path = "Unknown"
			try:
				for _ in range(5):
					try:
						path = SafeRead(INSTALL_PATH/"VRCUtil.lock")
						return requests.post(path, json=self.state)
					except:
						logger.warning(f"Failed to connect to VRCUtil instance for state sync \"{path}\". Retrying...")
						time.sleep(1)
						self.onVRCUtil(_, True)
			finally:
				self.synced = False
			logger.error(f"Failed to connect to VRCUtil instance for state sync.")

	def onVRCUtil(self, _, state):
		if state:
			self.syncState()

	def onVRChat(self, _, state):
		if state:
			VRCUtilAutostart(AutostartCondition.VRChat)
		self.state["vrchat"] = state
		self.syncState()

	def onSteamVR(self, _, state):
		if state:
			VRCUtilAutostart(AutostartCondition.SteamVR)
		self.state["steamvr"] = state
		self.syncState()

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
logger.info("ServiceWorker exited.")
stateManager.processWatcher.stop()