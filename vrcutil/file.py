import functools
import pathlib
import json
import time
import msvcrt
import win32file
import win32con

class SafeOpen:
	def __init__(self, path, mode="r+", encoding="utf-8", wait=True, touch=True):
		self.path = pathlib.Path(path)
		self.mode = mode
		self.encoding = encoding
		self.file = self._open(wait)
		if touch:
			self.path.touch()

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

def SafeRead(path: str|pathlib.Path) -> str:
	handle = None
	try:
		handle = win32file.CreateFile(
			str(path),
			win32con.GENERIC_READ,
			win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
			None,
			win32con.OPEN_EXISTING,
			0,
			None
		)
		win32file.SetFilePointer(handle, 1, win32file.FILE_BEGIN)
		return win32file.ReadFile(handle, win32file.GetFileSize(handle))[1].decode("utf-8", errors="ignore")
	finally:
		if handle:
			win32file.CloseHandle(handle)

class EasySetting:
	@staticmethod
	def _getPath(func,file) -> pathlib.Path:
		return pathlib.Path(func.__code__.co_filename).resolve().parent/(file or "Setting.json")
	
	@classmethod
	def useData(cls, settingFile=None):
		def decorator(func):
			@functools.wraps(func)
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
			@functools.wraps(func)
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
			@functools.wraps(func)
			def wrapper(*args, **kwargs):
				with SafeOpen(cls._getPath(func,settingFile), "r") as f:
					data = json.load(f)
				result = func(*args, **kwargs, setting=data)
				return result
			return wrapper
		return decorator