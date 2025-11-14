import wmi
import threading
import pythoncom
from pathlib import Path
import logging
import time
import gc

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

import pythoncom
import win32com.client

class CustomWMI:
	Creation = "SELECT * FROM __InstanceCreationEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_Process'"
	Deletion = "SELECT * FROM __InstanceDeletionEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_Process'"

	def __init__(self, query, namespace="root\\cimv2"):
		self.query = query
		self.namespace = namespace
		self.locator = None
		self.service = None
		self.event_source = None
		self.running = True

	def __enter__(self):
		pythoncom.CoInitialize()
		self.locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
		self.service = self.locator.ConnectServer(".", self.namespace)
		while self.running and self.event_source==None:
			try:
				self.event_source = self.service.ExecNotificationQuery(self.query)
			except Exception as e:
				logger.error(f"An error occurred while connecting to WMI: {e}")
				time.sleep(1)
		return self

	def watch(self):
		try:
			return self.event_source.NextEvent()
		except Exception as e:
			return None

	def __exit__(self, exc_type, exc_val, exc_tb):
		if self.event_source:
			del self.event_source
		if self.service:
			del self.service
		if self.locator:
			del self.locator
		pythoncom.CoUninitialize()
		gc.collect()

class ProcessWatcher:
	def __init__(self):
		self.watching = False
		self.threads:list[threading.Thread] = []
		self.target = {}

	def _processWatching(self,target):
		logger.debug(f"watcher created ({'creation' if target else 'deletion'})")
		# with CustomWMI(CustomWMI.Creation if target else CustomWMI.Deletion) as watcher:
		# 	while self.watching:
		# 		try:
		# 			if ((process:=getattr(watcher.watch(),"ExecutablePath",None)) in self.target) and self.watching:
		# 				for callback in self.target[process]:
		# 					threading.Thread(target=callback, args=(process,target,), daemon=True).start()
		# 		except Exception as e:
		# 			logger.error(f"An error occurred while watching process: {e}")
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
		for _ in self.threads[:]:
			self.threads.pop().join()

	def addTarget(self, path:Path|str, callback):
		self.target.setdefault(str(Path(path).resolve()),[]).append(callback)
		logger.info(f"Target registered: {path}")
		return self