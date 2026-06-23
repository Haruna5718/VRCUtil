import json
import time
import msvcrt
import ctypes
import pathlib
import threading
import functools
import os
from ctypes import wintypes

if os.name == "nt":
	_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
	_CreateFileW = _kernel32.CreateFileW
	_CreateFileW.argtypes = [
		wintypes.LPCWSTR,
		wintypes.DWORD,
		wintypes.DWORD,
		wintypes.LPVOID,
		wintypes.DWORD,
		wintypes.DWORD,
		wintypes.HANDLE,
	]
	_CreateFileW.restype = wintypes.HANDLE

	_ReadFile = _kernel32.ReadFile
	_ReadFile.argtypes = [
		wintypes.HANDLE,
		wintypes.LPVOID,
		wintypes.DWORD,
		ctypes.POINTER(wintypes.DWORD),
		wintypes.LPVOID,
	]
	_ReadFile.restype = wintypes.BOOL

	_SetFilePointerEx = _kernel32.SetFilePointerEx
	_SetFilePointerEx.argtypes = [
		wintypes.HANDLE,
		ctypes.c_longlong,
		ctypes.POINTER(ctypes.c_longlong),
		wintypes.DWORD,
	]
	_SetFilePointerEx.restype = wintypes.BOOL

	_GetFileSizeEx = _kernel32.GetFileSizeEx
	_GetFileSizeEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_longlong)]
	_GetFileSizeEx.restype = wintypes.BOOL

	_CloseHandle = _kernel32.CloseHandle
	_CloseHandle.argtypes = [wintypes.HANDLE]
	_CloseHandle.restype = wintypes.BOOL

	_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
	_GENERIC_READ = 0x80000000
	_FILE_SHARE_READ = 0x00000001
	_FILE_SHARE_WRITE = 0x00000002
	_OPEN_EXISTING = 3
	_FILE_BEGIN = 0

class SafeOpen:
	def __init__(self, path, mode="r+", encoding="utf-8", wait=True, touch=False, timeout=None, attempts=None, interval=0.01):
		self.path = pathlib.Path(path)
		self.mode = mode
		self.encoding = encoding
		self.timeout = timeout
		self.attempts = attempts
		self.interval = interval
		self.file = None
		self._open(wait, touch)

	def _open(self, isWait, isTouch):
		start = time.monotonic()
		attempt = 0
		if isTouch:
			self.path.parent.mkdir(parents=True, exist_ok=True)
			self.path.touch()
		while True:
			f = None
			try:
				f = open(self.path, self.mode, encoding=self.encoding)
				msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
				self.file = f
				return self.file
			except (OSError, PermissionError):
				if isWait:
					attempt += 1
					if self.attempts is not None and attempt >= self.attempts:
						return None
					if self.timeout is not None and time.monotonic() - start >= self.timeout:
						return None
					try:
						f.close()
					except:
						pass
					if self.interval > 0:
						time.sleep(self.interval)
				else:
					return None

	def close(self):
		if self.file is None:
			return
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

def _read_shared_bytes(path: str | pathlib.Path, offset: int = 0) -> bytes:
	if os.name != "nt":
		with open(path, "rb") as f:
			f.seek(offset)
			return f.read()

	handle = _CreateFileW(
		str(path),
		_GENERIC_READ,
		_FILE_SHARE_READ | _FILE_SHARE_WRITE,
		None,
		_OPEN_EXISTING,
		0,
		None,
	)
	if handle == _INVALID_HANDLE_VALUE:
		raise ctypes.WinError(ctypes.get_last_error())

	try:
		size = ctypes.c_longlong()
		if not _GetFileSizeEx(handle, ctypes.byref(size)):
			raise ctypes.WinError(ctypes.get_last_error())
		if offset and not _SetFilePointerEx(handle, offset, None, _FILE_BEGIN):
			raise ctypes.WinError(ctypes.get_last_error())

		length = max(0, int(size.value) - int(offset))
		if length <= 0:
			return b""

		buffer = ctypes.create_string_buffer(length)
		read = wintypes.DWORD()
		if not _ReadFile(handle, buffer, length, ctypes.byref(read), None):
			raise ctypes.WinError(ctypes.get_last_error())
		return buffer.raw[: read.value]
	finally:
		_CloseHandle(handle)

def SafeRead(path: str|pathlib.Path) -> str:
	path = pathlib.Path(path)
	try:
		return _read_shared_bytes(path, 0).decode("utf-8", errors="ignore")
	except Exception as first_error:
		try:
			return _read_shared_bytes(path, 1).decode("utf-8", errors="ignore")
		except Exception:
			raise first_error

class SafeJson(SafeOpen):
	def __init__(self, path, mode="r+", encoding="utf-8", wait=True, touch=True, timeout=None, attempts=None, interval=0.01):
		super().__init__(path, mode, encoding, wait, touch, timeout, attempts, interval)
		if self.file:
			try:
				self.data = json.load(self.file)
			except:
				self.data = {}
		else:
			self.data = {}

	def save(self):
		if self.file is None:
			return
		self.file.seek(0)
		self.file.truncate()
		json.dump(self.data, self.file, ensure_ascii=False, indent=4)

class EasySetting:
	@staticmethod
	def _getPath(func,file) -> pathlib.Path:
		if file:
			target = pathlib.Path(file)
			if target.is_absolute():
				return target
		module_file = None
		try:
			module_file = func.__globals__.get("__file__")
		except Exception:
			module_file = None
		if module_file:
			return pathlib.Path(module_file).resolve().parent / (file or "Setting.json")
		filename = pathlib.Path(func.__code__.co_filename)
		if not filename.is_absolute():
			filename = pathlib.Path.cwd() / filename
		return filename.resolve().parent / (file or "Setting.json")
	
	@classmethod
	def useData(cls, settingFile=None):
		def decorator(func):
			@functools.wraps(func)
			def wrapper(*args, **kwargs):
				with SafeOpen(cls._getPath(func,settingFile), "r+", touch=True) as f:
					try:
						data = json.load(f)
					except:
						data = {}
					result = func(*args, **kwargs, setting=data)
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
					with SafeOpen(cls._getPath(func,settingFile), "w", touch=True) as f:
						json.dump(result, f, ensure_ascii=False, indent=4)
				return result
			return wrapper
		return decorator
	
	@classmethod
	def loadData(cls, settingFile=None):
		def decorator(func):
			@functools.wraps(func)
			def wrapper(*args, **kwargs):
				with SafeOpen(cls._getPath(func,settingFile), "r", touch=True) as f:
					try:
						data = json.load(f)
					except:
						data = {}
				result = func(*args, **kwargs, setting=data)
				return result
			return wrapper
		return decorator
	
class BufferedJsonSaver:
	def __init__(self, path:str|pathlib.Path):
		self.path = path
		self._saveTimer = None
		self._bufferTime = 1
		self._saveBuffer:dict[str] = {}
		self._lock = threading.Lock()

	def save(self, key, value):
		with self._lock:
			if self._saveBuffer.get(key) == value and self._saveTimer and self._saveTimer.is_alive():
				return
			self._saveBuffer[key] = value
			self._saveSchedule()

	def _saveSchedule(self):
		if self._saveTimer and self._saveTimer.is_alive():
			return
		self._saveTimer = threading.Timer(self._bufferTime, self._saveData)
		self._saveTimer.daemon = True
		self._saveTimer.start()

	def _saveData(self):
		with self._lock:
			pending = dict(self._saveBuffer)

		if not pending:
			return

		with SafeOpen(self.path, "r+", touch=True) as f:
			try:
				data = json.load(f)
				changed = {k: v for k, v in pending.items() if data.get(k) != v}
			except:
				data = {}
				changed = pending

			if changed:
				data.update(changed)
				f.seek(0)
				f.truncate()
				json.dump(data, f, ensure_ascii=False, indent=4)

		with self._lock:
			for key, value in pending.items():
				if self._saveBuffer.get(key) == value:
					self._saveBuffer.pop(key, None)
			self._saveTimer = None
			if self._saveBuffer:
				self._saveSchedule()
