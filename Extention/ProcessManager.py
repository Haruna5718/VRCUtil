import wmi
import threading
import pythoncom
from pathlib import Path
import time
import logging

logger = logging.getLogger("vrcutil.processmanager")

def checkProcessState(path:str):
	pythoncom.CoInitialize()
	try:
		if wmi.WMI().Win32_Process(ExecutablePath=path):
			return True
	except:
		pass
	finally:
		pythoncom.CoUninitialize()
	return False

class ProcessWatcher:
	def __init__(self):
		self.watching = False
		self.threads:list[threading.Thread] = []
		self.target = {}

	def _createWatcher(self,type:str):
		while self.watching:
			try:
				watcher = wmi.WMI().Win32_Process.watch_for(type)
				logger.debug(f"watcher created ({type})")
				return watcher
			except Exception as e:
				logger.error(f"failed to create process watcher, retry in 1 seconds: {e}")
				time.sleep(1)
			
	def _processWatching(self,target):
		pythoncom.CoInitialize()
		try:
			watcher = self._createWatcher("creation" if target else "deletion")
			while self.watching:
				try:
					if ((process:=getattr(watcher(),"ExecutablePath",None)) in self.target) and self.watching:
						for callback in self.target[process]:
							threading.Thread(target=callback, args=(process,target,), daemon=True).start()
				except Exception as e:
					logger.error(f"An error occurred while watching process: {e}")
					del watcher
					watcher = self._createWatcher("creation" if target else "deletion")
		finally:
			watcher.stop()
			del watcher
			pythoncom.CoUninitialize()

			logger.debug(f"Watcher closed ({'creation' if target else 'deletion'})")
		
	def start(self, creation=True, deletion=True, checkCurrent=False):
		self.watching = True
		if creation:
			creationThread = threading.Thread(target=self._processWatching, args=(True,))
			creationThread.start()
			self.threads.append(creationThread)
		if deletion:
			deletionThread = threading.Thread(target=self._processWatching, args=(False,))
			deletionThread.start()
			self.threads.append(deletionThread)
		if checkCurrent:
			for path,callbacks in list(self.target.items()):
				if (creation if (state:=checkProcessState(path)) else deletion):
					for callback in callbacks:
						threading.Thread(target=callback, args=(path,state,), daemon=True).start()
						logger.info(f"Process checked ({state}): {path}")
		return self

	def stop(self):
		self.watching = False
		for i in self.threads[:]:
			i.join()
		self.threads = []

	def addTarget(self, path:Path|str, callback):
		self.target.setdefault(str(Path(path).resolve()),[]).append(callback)
		logger.info(f"Target registered: {path}")
		return self