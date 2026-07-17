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
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
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


def _open_process(pid: int) -> wintypes.HANDLE | None:
	return kernel32.OpenProcess(
		PROCESS_QUERY_LIMITED_INFORMATION | 0x00100000,
		False,
		pid,
	) or None


def _query_process_path(handle: wintypes.HANDLE) -> str | None:
	buffer_size = wintypes.DWORD(32768)
	buffer = ctypes.create_unicode_buffer(buffer_size.value)
	if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(buffer_size)):
		return None
	return str(pathlib.Path(buffer.value).resolve())


def _iter_processes(target_names: set[str] | None = None):
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
				yield entry.th32ProcessID, process_name

			if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
				break
	finally:
		kernel32.CloseHandle(snapshot)


def _iter_process_paths(target_names: set[str] | None = None):
	for pid, _ in _iter_processes(target_names):
		handle = _open_process(pid)
		if not handle:
			continue

		try:
			process_path = _query_process_path(handle)
			if process_path:
				yield process_path
		finally:
			kernel32.CloseHandle(handle)


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
		self._process_handles: dict[str, wintypes.HANDLE] = {}
		self._next_discovery = 0.0
		self._creation_enabled = True
		self._deletion_enabled = True
		self._stop_event = threading.Event()

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

	def _close_process_handle(self, path: str):
		handle = self._process_handles.pop(path, None)
		if handle:
			kernel32.CloseHandle(handle)

	def _find_missing_processes(self, states: dict[str, bool]):
		missing = {path for path, state in states.items() if not state}
		if not missing or time.monotonic() < self._next_discovery:
			return
		self._next_discovery = time.monotonic() + max(1.0, self._poll_interval * 5)

		targets_by_name: dict[str, set[str]] = {}
		for path in missing:
			targets_by_name.setdefault(pathlib.Path(path).name.casefold(), set()).add(path)

		for pid, process_name in _iter_processes(set(targets_by_name)):
			for target in tuple(targets_by_name[process_name]):
				if states[target]:
					continue

				handle = _open_process(pid)
				if not handle:
					continue

				try:
					process_path = _query_process_path(handle)
					if process_path and _normalize_process_path(process_path) == target:
						self._process_handles[target] = handle
						states[target] = True
						handle = None
				finally:
					if handle:
						kernel32.CloseHandle(handle)

	def _scan_states(self) -> dict[str, bool]:
		states: dict[str, bool] = {}
		for path in self.target:
			handle = self._process_handles.get(path)
			if handle and kernel32.WaitForSingleObject(handle, 0) == 0x00000102:
				states[path] = True
				continue

			self._close_process_handle(path)
			states[path] = False

		self._find_missing_processes(states)
		return states

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

			if self._stop_event.wait(self._poll_interval):
				return

	def start(self, creation=True, deletion=True, checkCurrent=False):
		self.running = True
		self._stop_event.clear()
		self._creation_enabled = creation
		self._deletion_enabled = deletion
		self._next_discovery = 0.0
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
		self._stop_event.set()
		for thread in self.threads[:]:
			thread.join(timeout=0.25)
		self.threads = []
		self._last_seen = {}
		self._next_discovery = 0.0
		for path in tuple(self._process_handles):
			self._close_process_handle(path)
		if self._callback_executor is not None:
			self._callback_executor.shutdown(wait=False)
			self._callback_executor = None

	def addTarget(self, path: pathlib.Path | str, callback):
		normalized = _normalize_process_path(path)
		self.target.setdefault(normalized, []).append(callback)
		logger.info(f"Target registered: {path}")
		return self
