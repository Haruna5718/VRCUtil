import ctypes
import logging
import os
import pathlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from ctypes import wintypes

logger = logging.getLogger("vrcutil.wmi")

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
	_fields_ = [
		("dwSize", wintypes.DWORD),
		("cntUsage", wintypes.DWORD),
		("th32ProcessID", wintypes.DWORD),
		("th32DefaultHeapID", ctypes.c_size_t),
		("th32ModuleID", wintypes.DWORD),
		("cntThreads", wintypes.DWORD),
		("th32ParentProcessID", wintypes.DWORD),
		("pcPriClassBase", ctypes.c_long),
		("dwFlags", wintypes.DWORD),
		("szExeFile", wintypes.WCHAR * wintypes.MAX_PATH),
	]


kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wintypes.BOOL
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
	wintypes.HANDLE,
	wintypes.DWORD,
	wintypes.LPWSTR,
	ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


def _normalize_process_path(path: str | pathlib.Path) -> str:
	return str(pathlib.Path(path).resolve()).casefold()


def _query_process_path(pid: int) -> str | None:
	handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
	if not handle:
		return None

	try:
		buffer_size = wintypes.DWORD(32768)
		buffer = ctypes.create_unicode_buffer(buffer_size.value)
		if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(buffer_size)):
			return None
		return str(pathlib.Path(buffer.value).resolve())
	finally:
		kernel32.CloseHandle(handle)


def _iter_process_paths(target_names: set[str] | None = None):
	snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
	if snapshot == INVALID_HANDLE_VALUE:
		raise ctypes.WinError(ctypes.get_last_error())

	entry = PROCESSENTRY32W()
	entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)

	try:
		if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
			return

		while True:
			process_name = entry.szExeFile.casefold()
			if target_names is None or process_name in target_names:
				process_path = _query_process_path(entry.th32ProcessID)
				if process_path:
					yield process_path

			if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
				break
	finally:
		kernel32.CloseHandle(snapshot)


def Check(path: str | pathlib.Path):
	target_path = pathlib.Path(path).resolve()
	target_name = target_path.name.casefold()
	target = str(target_path).casefold()

	count = 0
	try:
		for process_path in _iter_process_paths({target_name}):
			if process_path.casefold() == target:
				count += 1
	except Exception:
		logger.error("Process check failed", exc_info=True)
		return 0

	if count:
		logger.info(f"Process checked (True): {target_path}")
		return count

	logger.info(f"Process checked (False): {target_path}")
	return 0


class Watcher:
	Creation = "creation"
	Deletion = "deletion"


class ProcessWatcher:
	def __init__(self, poll_interval: float = 1.0):
		self.running = False
		self.threads: list[threading.Thread] = []
		self.target: dict[str, list] = {}
		self._callback_executor: ThreadPoolExecutor | None = None
		self._poll_interval = max(0.1, float(poll_interval))
		self._last_seen: dict[str, bool] = {}
		self._creation_enabled = True
		self._deletion_enabled = True

	def _ensure_executor(self):
		if self._callback_executor is None:
			worker_count = max(4, min(16, (os.cpu_count() or 1) * 2))
			self._callback_executor = ThreadPoolExecutor(
				max_workers=worker_count,
				thread_name_prefix="vrcutil-proc",
			)

	def _dispatch_callback(self, callback, path, state):
		try:
			callback(path, state)
		except Exception:
			logger.error("An error occurred while processing callback", exc_info=True)

	def _emit_state(self, path: str, state: bool):
		self._ensure_executor()
		for callback in tuple(self.target.get(path, ())):
			self._callback_executor.submit(self._dispatch_callback, callback, path, state)
		logger.debug(f"Process detected ({'creation' if state else 'deletion'}): {path}")

	def _scan_states(self) -> dict[str, bool]:
		if not self.target:
			return {}

		target_names = {pathlib.Path(path).name.casefold() for path in self.target}
		running = {
			process_path.casefold()
			for process_path in _iter_process_paths(target_names)
		}
		return {path: path in running for path in self.target}

	def _poll(self):
		while self.running:
			try:
				current = self._scan_states()
				for path, state in current.items():
					before = self._last_seen.get(path, False)
					if state == before:
						continue

					self._last_seen[path] = state
					if state and self._creation_enabled:
						self._emit_state(path, True)
					elif not state and self._deletion_enabled:
						self._emit_state(path, False)
			except Exception:
				if not self.running:
					return
				logger.error("An error occurred while polling process state", exc_info=True)

			time.sleep(self._poll_interval)

	def start(self, creation=True, deletion=True, checkCurrent=False):
		self.running = True
		self._creation_enabled = creation
		self._deletion_enabled = deletion
		self._ensure_executor()

		initial = self._scan_states()
		self._last_seen = dict(initial)

		if checkCurrent:
			for path, state in initial.items():
				if state and creation:
					self._emit_state(path, True)
				elif not state and deletion:
					self._emit_state(path, False)

		poll_thread = threading.Thread(
			target=self._poll,
			daemon=True,
			name="vrcutil-process-poll",
		)
		poll_thread.start()
		self.threads.append(poll_thread)
		return self

	def stop(self):
		self.running = False
		for thread in self.threads[:]:
			thread.join(timeout=1)
		self.threads = []
		self._last_seen = {}
		if self._callback_executor is not None:
			self._callback_executor.shutdown(wait=False)
			self._callback_executor = None

	def addTarget(self, path: pathlib.Path | str, callback):
		normalized = _normalize_process_path(path)
		self.target.setdefault(normalized, []).append(callback)
		logger.info(f"Target registered: {path}")
		return self