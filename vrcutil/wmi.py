import gc
import wmi
import time
import pathlib
import logging
import threading
import pythoncom

logger = logging.getLogger("vrcutil.wmi")

def Check(path:str|pathlib.Path):
	pythoncom.CoInitialize()
	try:
		if count:=len([i for i in wmi.WMI().Win32_Process(name=str(pathlib.Path(path).name)) if i.ExecutablePath==str(path)]):
			logger.info(f"Process checked (True): {path}")
			return count
	except:
		pass
	finally:
		pythoncom.CoUninitialize()
	logger.info(f"Process checked (False): {path}")
	return 0

class Watcher:
	Creation = "creation"
	Deletion = "deletion"
	def __init__(self, type:str, parent):
		self.type = type
		self.c = None
		self.watcher = None
		self.running = parent.running

	def __enter__(self):
		pythoncom.CoInitialize()
		self.c = wmi.WMI()
		while self.running:
			try:
				self.watcher = self.c.Win32_Process.watch_for(self.type)
				logger.debug(f"watcher created ({self.type})")
				return self.watcher
			except Exception as e:
				logger.warning(f"Failed to create WMI watcher ({self.type}): {e}")
				time.sleep(1)

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.running = False
		if self.c:
			del self.c
		if self.watcher:
			del self.watcher
		pythoncom.CoUninitialize()
		gc.collect()
		logger.debug(f"Watcher closed ({self.type})")

class ProcessWatcher:
	def __init__(self):
		self.running = False
		self.threads:list[threading.Thread] = []
		self.target = {}

	def _processWatching(self,target):
		with Watcher(target, self) as watcher:
			while self.running:
				try:
					threading.Thread(target=self._processEvent, args=(watcher(),target), daemon=True).start()
				except Exception as e:
					logger.error(f"An error occurred while watching process: {e}")
					return self._processWatching(target)

	def _processEvent(self, event, target):
		if self.running and (event.ExecutablePath in self.target):
			for callback in self.target[event.ExecutablePath]:
				threading.Thread(target=callback, args=(event.ExecutablePath,target=="creation",), daemon=True).start()
			logger.debug(f"Process detected ({target}): {event.ExecutablePath}")
		
	def start(self, creation=True, deletion=True, checkCurrent=False):
		self.running = True
		if creation:
			creationThread = threading.Thread(target=self._processWatching, args=(Watcher.Creation,))
			creationThread.start()
			self.threads.append(creationThread)
		if deletion:
			deletionThread = threading.Thread(target=self._processWatching, args=(Watcher.Deletion,))
			deletionThread.start()
			self.threads.append(deletionThread)
		if checkCurrent:
			for path,callbacks in list(self.target.items()):
				if (creation if (state:=Check(path)) else deletion):
					for callback in callbacks:
						threading.Thread(target=callback, args=(path,state,), daemon=True).start()
		return self

	def stop(self):
		self.running = False
		for i in self.threads[:]:
			i.join()
		self.threads = []

	def addTarget(self, path:pathlib.Path|str, callback):
		self.target.setdefault(str(pathlib.Path(path).resolve()),[]).append(callback)
		logger.info(f"Target registered: {path}")
		return self