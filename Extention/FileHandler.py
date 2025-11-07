from functools import wraps
from pathlib import Path
import json
import time
import msvcrt

class SafeOpen:
	def __init__(self, path, mode="r+", encoding="utf-8", wait=True):
		self.path = Path(path)
		self.mode = mode
		self.encoding = encoding
		self.file = self._open(wait)

	def _open(self, isWait):
		while True:
			try:
				f = open(self.path, self.mode, encoding=self.encoding)
				try:
					msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
					self.file = f
					return self.file
				except OSError:
					f.close()
					time.sleep(0.01)
			except (OSError, PermissionError):
				if isWait:
					time.sleep(0.01)
				else:
					return None

	def close(self):
		self.file.flush()
		self.file.seek(0)
		try:
			msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
		except OSError:
			pass
		self.file.close()

	def __enter__(self):
		return self
		
	def __exit__(self, *_):
		self.close()

	def __getattr__(self, name):
		return getattr(self.file, name)

class EasySetting:
	def _getPath(func,file) -> Path:
		return Path(func.__code__.co_filename).resolve().parent/(file or "Setting.json")
	
	@classmethod
	def useData(cls, settingFile=None):
		def decorator(func):
			@wraps(func)
			def wrapper(*args, **kwargs):
				with SafeOpen(cls._getPath(func,settingFile), "r+") as f:
					result = func(*args, **kwargs, setting=json.load(f))
					if result:
						f.seek(0)
						f.truncate()
						json.dump(result, f, ensure_ascii=False, indent=4)
				return result
			return wrapper
		return decorator

	@classmethod
	def saveData(cls, settingFile=None):
		def decorator(func):
			@wraps(func)
			def wrapper(*args, **kwargs):
				result = func(*args, **kwargs)
				if result:
					with SafeOpen(cls._getPath(func,settingFile), "w") as f:
						json.dump(result, f, ensure_ascii=False, indent=4)
				return result
			return wrapper
		return decorator
	
	@classmethod
	def loadData(cls, settingFile=None):
		def decorator(func):
			@wraps(func)
			def wrapper(*args, **kwargs):
				with SafeOpen(cls._getPath(func,settingFile), "r") as f:
					data = json.load(f)
				result = func(*args, **kwargs, setting=data)
				return result
			return wrapper
		return decorator