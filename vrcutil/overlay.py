import ctypes
import enum
import logging
import os
import pathlib
import secrets
import socket
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass
from multiprocessing.connection import Client, Listener
from multiprocessing import shared_memory
from typing import Any, cast

os.environ["PYOPENGL_USE_ACCELERATE"] = "0"

from . import INSTALL_PATH, IS_COMPILED

_overlay_runtime_ready = False
logger = logging.getLogger("vrcutil.overlay")

glfw = cast(Any, None)
openvr = cast(Any, None)
Image = cast(Any, None)

GL_CLAMP_TO_EDGE = 0
GL_LINEAR = 0
GL_PIXEL_UNPACK_BUFFER = 0
GL_RGBA = 0
GL_STREAM_DRAW = 0
GL_TEXTURE_2D = 0
GL_TEXTURE_MAG_FILTER = 0
GL_TEXTURE_MIN_FILTER = 0
GL_TEXTURE_WRAP_S = 0
GL_TEXTURE_WRAP_T = 0
GL_UNPACK_ALIGNMENT = 0
GL_UNSIGNED_BYTE = 0

glBindBuffer = cast(Any, None)
glBindTexture = cast(Any, None)
glBufferData = cast(Any, None)
glBufferSubData = cast(Any, None)
glDeleteBuffers = cast(Any, None)
glDeleteTextures = cast(Any, None)
glGenBuffers = cast(Any, None)
glGenTextures = cast(Any, None)
glPixelStorei = cast(Any, None)
glTexImage2D = cast(Any, None)
glTexParameteri = cast(Any, None)
glTexSubImage2D = cast(Any, None)

def _ensure_image():
	global Image
	if Image is None:
		from PIL import Image as imported_Image

		Image = imported_Image
	return Image


def _debug_cleanup(message: str, *args):
	logger.debug(message, *args, exc_info=True)


def _run_hidden_command(command: list[str]):
    return subprocess.run(
        command,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def _close_shared_memory(shm: shared_memory.SharedMemory, message: str, *args):
    try:
        shm.close()
    except Exception:
        _debug_cleanup(message, *args)


def _unlink_shared_memory(shm: shared_memory.SharedMemory, message: str, *args):
    try:
        shm.unlink()
    except Exception:
        _debug_cleanup(message, *args)


def _ensure_overlay_runtime():
	global _overlay_runtime_ready
	if _overlay_runtime_ready:
		return

	global glfw, openvr, Image
	global GL_CLAMP_TO_EDGE, GL_LINEAR, GL_PIXEL_UNPACK_BUFFER, GL_RGBA, GL_STREAM_DRAW
	global GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER
	global GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_UNPACK_ALIGNMENT, GL_UNSIGNED_BYTE
	global glBindBuffer, glBindTexture, glBufferData, glBufferSubData
	global glDeleteBuffers, glDeleteTextures, glGenBuffers, glGenTextures
	global glPixelStorei, glTexImage2D, glTexParameteri, glTexSubImage2D

	import glfw as imported_glfw
	import openvr as imported_openvr
	from OpenGL.GL import (
		GL_CLAMP_TO_EDGE as imported_GL_CLAMP_TO_EDGE,
		GL_LINEAR as imported_GL_LINEAR,
		GL_PIXEL_UNPACK_BUFFER as imported_GL_PIXEL_UNPACK_BUFFER,
		GL_RGBA as imported_GL_RGBA,
		GL_STREAM_DRAW as imported_GL_STREAM_DRAW,
		GL_TEXTURE_2D as imported_GL_TEXTURE_2D,
		GL_TEXTURE_MAG_FILTER as imported_GL_TEXTURE_MAG_FILTER,
		GL_TEXTURE_MIN_FILTER as imported_GL_TEXTURE_MIN_FILTER,
		GL_TEXTURE_WRAP_S as imported_GL_TEXTURE_WRAP_S,
		GL_TEXTURE_WRAP_T as imported_GL_TEXTURE_WRAP_T,
		GL_UNPACK_ALIGNMENT as imported_GL_UNPACK_ALIGNMENT,
		GL_UNSIGNED_BYTE as imported_GL_UNSIGNED_BYTE,
		glBindBuffer as imported_glBindBuffer,
		glBindTexture as imported_glBindTexture,
		glBufferData as imported_glBufferData,
		glBufferSubData as imported_glBufferSubData,
		glDeleteBuffers as imported_glDeleteBuffers,
		glDeleteTextures as imported_glDeleteTextures,
		glGenBuffers as imported_glGenBuffers,
		glGenTextures as imported_glGenTextures,
		glPixelStorei as imported_glPixelStorei,
		glTexImage2D as imported_glTexImage2D,
		glTexParameteri as imported_glTexParameteri,
		glTexSubImage2D as imported_glTexSubImage2D,
	)

	glfw = imported_glfw
	openvr = imported_openvr
	GL_CLAMP_TO_EDGE = imported_GL_CLAMP_TO_EDGE
	GL_LINEAR = imported_GL_LINEAR
	GL_PIXEL_UNPACK_BUFFER = imported_GL_PIXEL_UNPACK_BUFFER
	GL_RGBA = imported_GL_RGBA
	GL_STREAM_DRAW = imported_GL_STREAM_DRAW
	GL_TEXTURE_2D = imported_GL_TEXTURE_2D
	GL_TEXTURE_MAG_FILTER = imported_GL_TEXTURE_MAG_FILTER
	GL_TEXTURE_MIN_FILTER = imported_GL_TEXTURE_MIN_FILTER
	GL_TEXTURE_WRAP_S = imported_GL_TEXTURE_WRAP_S
	GL_TEXTURE_WRAP_T = imported_GL_TEXTURE_WRAP_T
	GL_UNPACK_ALIGNMENT = imported_GL_UNPACK_ALIGNMENT
	GL_UNSIGNED_BYTE = imported_GL_UNSIGNED_BYTE
	glBindBuffer = imported_glBindBuffer
	glBindTexture = imported_glBindTexture
	glBufferData = imported_glBufferData
	glBufferSubData = imported_glBufferSubData
	glDeleteBuffers = imported_glDeleteBuffers
	glDeleteTextures = imported_glDeleteTextures
	glGenBuffers = imported_glGenBuffers
	glGenTextures = imported_glGenTextures
	glPixelStorei = imported_glPixelStorei
	glTexImage2D = imported_glTexImage2D
	glTexParameteri = imported_glTexParameteri
	glTexSubImage2D = imported_glTexSubImage2D
	_ensure_image()
	_overlay_runtime_ready = True


LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
ENUMWINDOWSPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
WINEVENTPROC = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    ctypes.c_long,
    ctypes.c_long,
    wintypes.DWORD,
    wintypes.DWORD,
)
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
BI_RGB = 0
DIB_RGB_COLORS = 0
EVENT_SYSTEM_MOVESIZESTART = 0x000A
EVENT_SYSTEM_MOVESIZEEND = 0x000B
EVENT_SYSTEM_MINIMIZESTART = 0x0016
EVENT_SYSTEM_MINIMIZEEND = 0x0017
EVENT_OBJECT_SHOW = 0x8002
EVENT_OBJECT_HIDE = 0x8003
EVENT_OBJECT_LOCATIONCHANGE = 0x800B
GWL_EXSTYLE = -20
GW_HWNDPREV = 3
GW_OWNER = 4
OBJID_WINDOW = 0
PM_REMOVE = 0x0001
SW_HIDE = 0
SWP_NOACTIVATE = 0x0010
SWP_NOSENDCHANGING = 0x0400
SWP_SHOWWINDOW = 0x0040
ULW_ALPHA = 0x00000002
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_POPUP = 0x80000000
HWND_TOP = wintypes.HWND(0)
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
DESKTOP_OVERLAY_ANCHORS = {
    "TopLeft": ("left", "top"),
    "TopRight": ("right", "top"),
    "BottomLeft": ("left", "bottom"),
    "BottomRight": ("right", "bottom"),
}

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class SIZE(ctypes.Structure):
    _fields_ = [
        ("cx", wintypes.LONG),
        ("cy", wintypes.LONG),
    ]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 1),
    ]


user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.ATOM
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    ctypes.c_void_p,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND,
    wintypes.HDC,
    ctypes.POINTER(wintypes.POINT),
    ctypes.POINTER(SIZE),
    wintypes.HDC,
    ctypes.POINTER(wintypes.POINT),
    wintypes.COLORREF,
    ctypes.POINTER(BLENDFUNCTION),
    wintypes.DWORD,
]
user32.UpdateLayeredWindow.restype = wintypes.BOOL
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
user32.EnumWindows.argtypes = [ENUMWINDOWSPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.PeekMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
    wintypes.UINT,
]
user32.PeekMessageW.restype = wintypes.BOOL
user32.SetWinEventHook.argtypes = [
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.HMODULE,
    WINEVENTPROC,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
]
user32.SetWinEventHook.restype = wintypes.HANDLE
user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]
user32.UnhookWinEvent.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = LRESULT
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC,
    ctypes.POINTER(BITMAPINFO),
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p),
    wintypes.HANDLE,
    wintypes.DWORD,
]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
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


def _query_process_path(pid: int):
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return None
    try:
        buffer_size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(buffer_size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(buffer_size)):
            return None
        return pathlib.Path(buffer.value).resolve()
    finally:
        kernel32.CloseHandle(handle)


def _hwnd_value(hwnd):
    if hwnd is None:
        return 0
    return int(getattr(hwnd, "value", hwnd) or 0)


@dataclass(frozen=True)
class DesktopOverlayLayout:
    anchor: str = "TopLeft"
    offset_x_percent: float = 2.0
    offset_y_percent: float = 2.0
    scale: float = 1.0


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _host_command(port: int) -> list[str]:
    args = [f"--overlay", f"{port}"]
    if not IS_COMPILED:
        return [sys.executable, str(INSTALL_PATH / "VRCUtil.py"), *args]
    return [str(INSTALL_PATH / "VRCUtil.exe"), *args]


def _host_startupinfo():
    if os.name != "nt":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.lpAttributeList["parent_process"] = int(ctypes.windll.kernel32.GetCurrentProcess())
    return startupinfo


class _OverlayProcessClient:
    SHUTDOWN_WAIT = 0.4
    KILL_WAIT = 0.1

    def __init__(self):
        self._connection = None
        self._process = None
        self._port = None
        self._disabled = False
        self._lock = threading.RLock()

    def _cleanup_stray_processes(self, port: int | None):
        if os.name != "nt" or port is None:
            return

        token = f"--overlay {int(port)}"
        escaped_token = token.replace("'", "''")
        script = (
            f"$token = '{escaped_token}';"
            f"$selfPid = {os.getpid()};"
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -like ('*' + $token + '*') -and $_.ProcessId -ne $PID -and $_.ProcessId -ne $selfPid } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        try:
            _run_hidden_command(
                ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script]
            )
        except OSError:
            _debug_cleanup("Failed to clean up stray overlay host processes")

    def _connect(self, port: int):
        deadline = time.time() + 10.0
        last_error = None

        while time.time() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(
                    f"Overlay host exited before accepting a connection (exit code {self._process.returncode})"
                ) from last_error
            try:
                return Client(("127.0.0.1", port))
            except OSError as exc:
                last_error = exc
                time.sleep(0.1)

        raise RuntimeError("Failed to connect to the overlay host") from last_error

    def start(self):
        with self._lock:
            if self._connection is not None:
                return
            if self._disabled:
                raise RuntimeError("Overlay host startup is disabled")
            port = _reserve_port()
            self._port = port
            self._process = subprocess.Popen(
                _host_command(port),
                creationflags=subprocess.CREATE_NO_WINDOW,
                cwd=INSTALL_PATH,
                startupinfo=_host_startupinfo(),
            )

            try:
                self._connection = self._connect(port)
            except Exception:
                self.stop(request_shutdown=False)
                raise

    def request(self, command: str, **payload):
        with self._lock:
            self.start()
            try:
                self._connection.send({"command": command, **payload})
                response = self._connection.recv()
            except (EOFError, OSError):
                self.stop(request_shutdown=False)
                raise

        if not response.get("ok", False):
            raise RuntimeError(response.get("error", "Overlay host request failed"))
        return response.get("result")

    def post(self, command: str, **payload):
        with self._lock:
            self.start()
            try:
                self._connection.send({"command": command, "_nowait": True, **payload})
            except (EOFError, OSError):
                self.stop(request_shutdown=False)
                raise

    def _stop_connection(self, connection, request_shutdown: bool):
        try:
            if request_shutdown:
                connection.send({"command": "shutdown"})
        except OSError:
            _debug_cleanup("Failed to request overlay host shutdown")
        try:
            connection.close()
        except OSError:
            _debug_cleanup("Failed to close overlay host connection")

    def _wait_for_exit(self, process, timeout: float, warning_message: str | None = None):
        try:
            process.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            if warning_message is not None:
                logger.warning(warning_message, process.pid)
            return False

    def _force_stop_process(self, process, *, after_timeout: bool):
        if os.name == "nt":
            try:
                _run_hidden_command(["taskkill", "/PID", str(process.pid), "/T", "/F"])
            except OSError:
                _debug_cleanup(
                    "Failed to force-kill overlay host tree%s: pid=%s",
                    " after timeout" if after_timeout else "",
                    process.pid,
                )
            return

        try:
            process.kill()
        except OSError:
            _debug_cleanup(
                "Failed to kill overlay host process%s: pid=%s",
                " after timeout" if after_timeout else "",
                process.pid,
            )

    def _stop_process(self, process, *, immediate: bool):
        if immediate:
            self._force_stop_process(process, after_timeout=False)
            self._wait_for_exit(process, self.KILL_WAIT, "Overlay host did not terminate after forced stop: pid=%s")
            return

        if self._wait_for_exit(process, self.SHUTDOWN_WAIT):
            return

        self._force_stop_process(process, after_timeout=True)
        self._wait_for_exit(process, self.KILL_WAIT, "Overlay host still alive after timeout kill: pid=%s")

    def stop(self, request_shutdown: bool = True, disable: bool = False, immediate: bool = False):
        with self._lock:
            if disable:
                self._disabled = True
            connection = self._connection
            process = self._process
            port = self._port
            self._connection = None
            self._process = None
            self._port = None

            if connection is not None:
                self._stop_connection(connection, request_shutdown)

            if process is not None:
                self._stop_process(process, immediate=immediate)

            self._cleanup_stray_processes(port)

    def set_disabled(self, disabled: bool):
        with self._lock:
            self._disabled = bool(disabled)


class OpenGLManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._shared_buffers: dict[tuple[int, str], tuple[shared_memory.SharedMemory, int]] = {}

    def _ensure_shared_buffer(self, key: tuple[int, str], byte_length: int):
        current = self._shared_buffers.get(key)
        if current is not None and current[1] >= byte_length:
            return current[0]

        if current is not None:
            shm, _ = current
            _close_shared_memory(shm, "Failed to close previous shared buffer for overlay texture")
            _unlink_shared_memory(shm, "Failed to unlink previous shared buffer for overlay texture")

        shm = shared_memory.SharedMemory(create=True, size=byte_length)
        self._shared_buffers[key] = (shm, byte_length)
        return shm

    def release(self, overlay_handle: int | None):
        if overlay_handle is None:
            return
        prefix = f"{int(overlay_handle)}:"
        for key in tuple(self._shared_buffers):
            if f"{key[0]}:{key[1]}".startswith(prefix):
                shm, _ = self._shared_buffers.pop(key)
                _close_shared_memory(shm, "Failed to close shared buffer for overlay texture")
                _unlink_shared_memory(shm, "Failed to unlink shared buffer for overlay texture")

    def submit(self, image, overlay, overlay_handle: int | None, name: str = "Default", sync: bool = False):
        _ensure_overlay_runtime()
        handle = overlay_handle if overlay_handle is not None else getattr(overlay, "overlay_handle", None)
        if handle is None:
            raise RuntimeError("Overlay is not initialized")

        rgba = image.convert("RGBA") if isinstance(image, Image.Image) and image.mode != "RGBA" else image
        if not isinstance(rgba, Image.Image):
            raise TypeError("OpenGLManager.submit expects a PIL image")

        payload = rgba.tobytes()
        key = (int(handle), name)
        with self._lock:
            shm = self._ensure_shared_buffer(key, len(payload))
            shm.buf[: len(payload)] = payload
            shared_name = shm.name

        payload_data = {
            "overlay_handle": int(handle),
            "name": name,
            "size": rgba.size,
            "byte_length": len(payload),
            "shared_name": shared_name,
        }
        if sync:
            Manager.request("set_texture_shared", **payload_data)
        else:
            Manager.post("set_texture_shared", **payload_data)


class DesktopOverlayWindow:
    IDLE_POLL_INTERVAL = 1 / 60
    ACTIVE_POLL_INTERVAL = 1 / 144
    ACTIVE_POLL_GRACE = 0.35
    STOP_WAIT = 1.0
    PROCESS_PATH_CACHE_TTL = 2.0
    PROCESS_PATH_CACHE_LIMIT = 64
    REFERENCE_CLIENT_WIDTH = 1920
    REFERENCE_CLIENT_HEIGHT = 1080
    TARGET_WINDOW_EVENTS = frozenset(
        (
            EVENT_SYSTEM_MOVESIZESTART,
            EVENT_SYSTEM_MOVESIZEEND,
            EVENT_SYSTEM_MINIMIZESTART,
            EVENT_SYSTEM_MINIMIZEEND,
            EVENT_OBJECT_SHOW,
            EVENT_OBJECT_HIDE,
            EVENT_OBJECT_LOCATIONCHANGE,
        )
    )
    HOOK_RANGES = (
        (EVENT_SYSTEM_MOVESIZESTART, EVENT_SYSTEM_MINIMIZEEND),
        (EVENT_OBJECT_SHOW, EVENT_OBJECT_LOCATIONCHANGE),
    )

    def __init__(self, name: str, target_process: str):
        self.name = str(name)
        self.target_process = str(target_process).casefold()
        self._thread = None
        self._stopper = threading.Event()
        self._wake_event = threading.Event()
        self._lock = threading.Lock()
        self._hwnd = None
        self._frame = None
        self._frame_token = 0
        self._layout = DesktopOverlayLayout()
        self._last_window_state = None
        self._last_canvas_state = None
        self._last_scaled_state = None
        self._last_scaled_image = None
        self._target_window = None
        self._target_window_pid = None
        self._last_probe_at = 0.0
        self._active_until = 0.0
        self._process_path_cache = {}
        self._hook_pid = None
        self._hook_handles = []
        self._class_atom = 0
        self._class_name = f"VRCUtil.DesktopOverlay.{self.name}.{os.getpid()}.{id(self)}"
        self._wndproc = WNDPROC(self._window_proc)
        self._wineventproc = WINEVENTPROC(self._event_hook_proc)
        self._memory_dc = None
        self._memory_dc_base_bitmap = None
        self._bitmap = None
        self._bitmap_bits = None
        self._bitmap_size = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stopper.clear()
        self._wake_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"{self.name}-desktop-overlay")
        self._thread.start()

    def stop(self):
        self._stopper.set()
        self._wake_event.set()
        if self._hwnd and user32.IsWindow(self._hwnd):
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(self.STOP_WAIT)
            if thread.is_alive():
                logger.warning("Desktop overlay thread did not stop within %.2fs: %s", self.STOP_WAIT, self.name)
                return False
        self._thread = None
        return True

    def configure(
        self,
        *,
        anchor: str | None = None,
        offset_x_percent: float | None = None,
        offset_y_percent: float | None = None,
        scale: float | None = None,
    ):
        with self._lock:
            current = self._layout
            anchor_value = str(anchor or current.anchor)
            if anchor_value not in DESKTOP_OVERLAY_ANCHORS:
                anchor_value = current.anchor
            offset_x = current.offset_x_percent if offset_x_percent is None else max(0.0, min(100.0, float(offset_x_percent)))
            offset_y = current.offset_y_percent if offset_y_percent is None else max(0.0, min(100.0, float(offset_y_percent)))
            scale_value = current.scale if scale is None else max(0.25, min(3.0, float(scale)))
            self._layout = DesktopOverlayLayout(anchor_value, round(offset_x, 2), round(offset_y, 2), round(scale_value, 2))

    def update(self, image: Any | None):
        if image is None:
            with self._lock:
                self._frame = None
                self._frame_token += 1
            return
        frame = image.convert("RGBA")
        with self._lock:
            self._frame = frame
            self._frame_token += 1

    def _window_proc(self, hwnd, message, wparam, lparam):
        if message == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        if message == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def _event_hook_proc(self, _hook, event, hwnd, id_object, id_child, _event_thread, _event_time):
        if id_object != OBJID_WINDOW or id_child != 0:
            return
        if not hwnd or not self._target_window:
            return
        if _hwnd_value(hwnd) != _hwnd_value(self._target_window):
            return
        if event in self.TARGET_WINDOW_EVENTS:
            self._mark_active()
            self._wake_event.set()

    def _register_window_class(self):
        if self._class_atom:
            return
        window_class = WNDCLASSW()
        window_class.lpfnWndProc = self._wndproc
        window_class.hInstance = kernel32.GetModuleHandleW(None)
        window_class.lpszClassName = self._class_name
        self._class_atom = user32.RegisterClassW(ctypes.byref(window_class))
        if not self._class_atom:
            raise ctypes.WinError(ctypes.get_last_error())

    def _create_window(self):
        self._register_window_class()
        self._hwnd = user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            self._class_name,
            "",
            WS_POPUP,
            0,
            0,
            1,
            1,
            None,
            None,
            kernel32.GetModuleHandleW(None),
            None,
        )
        if not self._hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        user32.ShowWindow(self._hwnd, SW_HIDE)

    def _destroy_window(self):
        if self._hwnd and user32.IsWindow(self._hwnd):
            user32.DestroyWindow(self._hwnd)
        self._hwnd = None

    def _install_event_hooks(self, pid: int):
        self._uninstall_event_hooks()
        self._hook_pid = int(pid)
        for event_min, event_max in self.HOOK_RANGES:
            hook = user32.SetWinEventHook(
                event_min,
                event_max,
                None,
                self._wineventproc,
                self._hook_pid,
                0,
                WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
            )
            if hook:
                self._hook_handles.append(hook)
        if not self._hook_handles:
            self._hook_pid = None

    def _uninstall_event_hooks(self):
        for hook in self._hook_handles:
            try:
                user32.UnhookWinEvent(hook)
            except Exception:
                _debug_cleanup("Failed to unhook desktop overlay event hook: %s", self.name)
        self._hook_handles = []
        self._hook_pid = None

    def _update_event_hooks(self, hwnd):
        if not hwnd or not user32.IsWindow(hwnd):
            self._uninstall_event_hooks()
            return
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            self._uninstall_event_hooks()
            return
        if self._hook_pid == int(pid.value) and self._hook_handles:
            return
        self._install_event_hooks(int(pid.value))

    def _pump_messages(self):
        message = wintypes.MSG()
        while user32.PeekMessageW(ctypes.byref(message), None, 0, 0, PM_REMOVE):
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))

    def _current_state(self):
        with self._lock:
            return self._frame, self._frame_token, self._layout

    def _get_process_path(self, pid: int):
        pid = int(pid)
        if pid <= 0:
            return None

        now = time.monotonic()
        cached = self._process_path_cache.get(pid)
        if cached is not None and now < cached[0]:
            return cached[1]

        process_path = _query_process_path(pid)
        self._process_path_cache[pid] = (now + self.PROCESS_PATH_CACHE_TTL, process_path)
        if len(self._process_path_cache) > self.PROCESS_PATH_CACHE_LIMIT:
            self._process_path_cache = {
                cached_pid: cached_value
                for cached_pid, cached_value in self._process_path_cache.items()
                if cached_value[0] > now
            }
        return process_path

    def _window_matches_target(self, hwnd):
        if not hwnd or not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
            return False
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        pid_value = int(pid.value)
        if not pid_value:
            return False
        if _hwnd_value(hwnd) == _hwnd_value(self._target_window) and self._target_window_pid == pid_value:
            return True
        process_path = self._get_process_path(pid_value)
        return bool(process_path and process_path.name.casefold() == self.target_process)

    def _find_target_window(self):
        candidates = []

        def callback(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            if user32.GetWindow(hwnd, GW_OWNER):
                return True
            if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            pid_value = int(pid.value)
            process_path = self._get_process_path(pid_value)
            if not process_path or process_path.name.casefold() != self.target_process:
                return True
            rect = wintypes.RECT()
            if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
                return True
            width = max(0, rect.right - rect.left)
            height = max(0, rect.bottom - rect.top)
            if not width or not height:
                return True
            candidates.append((width * height, _hwnd_value(hwnd), pid_value))
            return True

        user32.EnumWindows(ENUMWINDOWSPROC(callback), 0)
        if not candidates:
            self._target_window_pid = None
            return None
        _, hwnd_value, pid_value = max(candidates)
        self._target_window_pid = pid_value
        return wintypes.HWND(hwnd_value)

    def _resolve_target_window(self):
        if self._window_matches_target(self._target_window):
            return self._target_window
        now = time.monotonic()
        if not self._target_window and now - self._last_probe_at < 0.5:
            return None
        self._last_probe_at = now
        self._target_window = self._find_target_window()
        if self._target_window is None:
            self._target_window_pid = None
        return self._target_window

    def _client_rect(self, hwnd):
        if not hwnd:
            return None
        rect = wintypes.RECT()
        if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return None
        width = max(0, rect.right - rect.left)
        height = max(0, rect.bottom - rect.top)
        if not width or not height:
            return None
        top_left = wintypes.POINT(0, 0)
        bottom_right = wintypes.POINT(width, height)
        if not user32.ClientToScreen(hwnd, ctypes.byref(top_left)):
            return None
        if not user32.ClientToScreen(hwnd, ctypes.byref(bottom_right)):
            return None
        return (
            int(top_left.x),
            int(top_left.y),
            max(0, int(bottom_right.x - top_left.x)),
            max(0, int(bottom_right.y - top_left.y)),
        )

    def _z_order_anchor(self, hwnd):
        anchor = user32.GetWindow(hwnd, GW_HWNDPREV)
        while anchor and _hwnd_value(anchor) == _hwnd_value(self._hwnd):
            anchor = user32.GetWindow(anchor, GW_HWNDPREV)
        if anchor and user32.GetWindowLongW(anchor, GWL_EXSTYLE) & WS_EX_TOPMOST:
            return HWND_TOP
        return anchor or HWND_TOP

    def _current_overlay_anchor(self):
        if not self._hwnd or not user32.IsWindow(self._hwnd):
            return None
        anchor = user32.GetWindow(self._hwnd, GW_HWNDPREV)
        while anchor and _hwnd_value(anchor) == _hwnd_value(self._hwnd):
            anchor = user32.GetWindow(anchor, GW_HWNDPREV)
        return anchor

    def _hide(self):
        if self._hwnd and user32.IsWindow(self._hwnd):
            user32.ShowWindow(self._hwnd, SW_HIDE)
        self._last_window_state = None

    def _release_bitmap_resources(self):
        if self._memory_dc is not None and self._bitmap is not None and self._memory_dc_base_bitmap is not None:
            try:
                gdi32.SelectObject(self._memory_dc, self._memory_dc_base_bitmap)
            except Exception:
                _debug_cleanup("Failed to restore desktop overlay bitmap selection: %s", self.name)
        if self._bitmap is not None:
            try:
                gdi32.DeleteObject(self._bitmap)
            except Exception:
                _debug_cleanup("Failed to delete desktop overlay bitmap: %s", self.name)
        if self._memory_dc is not None:
            try:
                gdi32.DeleteDC(self._memory_dc)
            except Exception:
                _debug_cleanup("Failed to delete desktop overlay DC: %s", self.name)
        self._memory_dc = None
        self._memory_dc_base_bitmap = None
        self._bitmap = None
        self._bitmap_bits = None
        self._bitmap_size = None

    def _mark_active(self):
        self._active_until = time.monotonic() + self.ACTIVE_POLL_GRACE

    def _poll_interval(self):
        if time.monotonic() < self._active_until:
            return self.ACTIVE_POLL_INTERVAL
        return self.IDLE_POLL_INTERVAL

    def _ensure_bitmap_resources(self, screen_dc, width: int, height: int):
        if self._memory_dc is None:
            self._memory_dc = gdi32.CreateCompatibleDC(screen_dc)
            if not self._memory_dc:
                raise ctypes.WinError(ctypes.get_last_error())

        size = (int(width), int(height))
        if self._bitmap is not None and self._bitmap_bits is not None and self._bitmap_size == size:
            return

        bits = ctypes.c_void_p()
        bitmap_info = BITMAPINFO()
        bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bitmap_info.bmiHeader.biWidth = width
        bitmap_info.bmiHeader.biHeight = -height
        bitmap_info.bmiHeader.biPlanes = 1
        bitmap_info.bmiHeader.biBitCount = 32
        bitmap_info.bmiHeader.biCompression = BI_RGB
        bitmap = gdi32.CreateDIBSection(screen_dc, ctypes.byref(bitmap_info), DIB_RGB_COLORS, ctypes.byref(bits), None, 0)
        if not bitmap:
            raise ctypes.WinError(ctypes.get_last_error())

        previous = gdi32.SelectObject(self._memory_dc, bitmap)
        if not previous:
            gdi32.DeleteObject(bitmap)
            raise ctypes.WinError(ctypes.get_last_error())

        if self._bitmap is None:
            self._memory_dc_base_bitmap = previous
        else:
            try:
                gdi32.DeleteObject(self._bitmap)
            except Exception:
                _debug_cleanup("Failed to delete previous desktop overlay bitmap: %s", self.name)

        self._bitmap = bitmap
        self._bitmap_bits = bits
        self._bitmap_size = size

    def _scaled_frame(self, frame: Any, token: int, width: int, height: int):
        ImageModule = _ensure_image()
        scale_state = (token, width, height)
        if self._last_scaled_state == scale_state and self._last_scaled_image is not None:
            return self._last_scaled_image
        if frame.size == (width, height):
            scaled = frame
        else:
            scaled = frame.resize((width, height), ImageModule.Resampling.LANCZOS)
        self._last_scaled_state = scale_state
        self._last_scaled_image = scaled
        return scaled

    def _responsive_scale_factor(self, client_width: int, client_height: int):
        width_factor = client_width / self.REFERENCE_CLIENT_WIDTH if self.REFERENCE_CLIENT_WIDTH else 1.0
        height_factor = client_height / self.REFERENCE_CLIENT_HEIGHT if self.REFERENCE_CLIENT_HEIGHT else 1.0
        return max(0.25, min(width_factor, height_factor))

    def _compose_canvas(self, frame: Any, token: int, client_width: int, client_height: int, layout: DesktopOverlayLayout):
        ImageModule = _ensure_image()
        anchor_x, anchor_y = DESKTOP_OVERLAY_ANCHORS[layout.anchor]
        offset_x = round(client_width * layout.offset_x_percent / 100)
        offset_y = round(client_height * layout.offset_y_percent / 100)
        responsive_scale = layout.scale * self._responsive_scale_factor(client_width, client_height)
        draw_width = max(1, round(frame.width * responsive_scale))
        draw_height = max(1, round(frame.height * responsive_scale))
        fit_scale = min(1.0, client_width / draw_width if draw_width else 1.0, client_height / draw_height if draw_height else 1.0)
        draw_width = max(1, round(draw_width * fit_scale))
        draw_height = max(1, round(draw_height * fit_scale))
        scaled = self._scaled_frame(frame, token, draw_width, draw_height)
        left = offset_x if anchor_x == "left" else client_width - draw_width - offset_x
        top = offset_y if anchor_y == "top" else client_height - draw_height - offset_y
        left = max(0, min(max(0, client_width - draw_width), left))
        top = max(0, min(max(0, client_height - draw_height), top))
        canvas = ImageModule.new("RGBA", (client_width, client_height), (0, 0, 0, 0))
        canvas.alpha_composite(scaled, (left, top))
        return canvas, (token, client_width, client_height, draw_width, draw_height, left, top, layout)

    def _update_layered_window(self, left: int, top: int, image: Any):
        width, height = image.size
        if not width or not height:
            return
        screen_dc = user32.GetDC(None)
        try:
            self._ensure_bitmap_resources(screen_dc, width, height)
            rgba = image if image.mode == "RGBA" else image.convert("RGBA")
            image_buffer = rgba.tobytes("raw", "BGRA")
            ctypes.memmove(self._bitmap_bits.value, image_buffer, len(image_buffer))
            position = wintypes.POINT(left, top)
            source = wintypes.POINT(0, 0)
            size = SIZE(width, height)
            blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
            if not user32.UpdateLayeredWindow(
                self._hwnd,
                screen_dc,
                ctypes.byref(position),
                ctypes.byref(size),
                self._memory_dc,
                ctypes.byref(source),
                0,
                ctypes.byref(blend),
                ULW_ALPHA,
            ):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            user32.ReleaseDC(None, screen_dc)

    def _sync(self):
        frame, token, layout = self._current_state()
        if frame is None:
            self._uninstall_event_hooks()
            self._hide()
            return
        target = self._resolve_target_window()
        if not target or user32.IsIconic(target):
            self._uninstall_event_hooks()
            self._hide()
            return
        self._update_event_hooks(target)
        client_rect = self._client_rect(target)
        if client_rect is None:
            self._hide()
            return
        left, top, width, height = client_rect
        anchor = self._z_order_anchor(target)
        window_state = (_hwnd_value(target), left, top, width, height, _hwnd_value(anchor))
        current_anchor = self._current_overlay_anchor()
        if self._last_window_state != window_state or _hwnd_value(current_anchor) != _hwnd_value(anchor):
            self._mark_active()
            if not user32.SetWindowPos(
                self._hwnd,
                anchor,
                left,
                top,
                width,
                height,
                SWP_NOACTIVATE | SWP_NOSENDCHANGING | SWP_SHOWWINDOW,
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            self._last_window_state = window_state
        canvas, canvas_state = self._compose_canvas(frame, token, width, height, layout)
        if self._last_canvas_state != canvas_state:
            self._update_layered_window(left, top, canvas)
            self._last_canvas_state = canvas_state

    def _run(self):
        try:
            self._create_window()
            while not self._stopper.is_set():
                self._pump_messages()
                self._sync()
                triggered = self._wake_event.wait(self._poll_interval())
                if triggered:
                    self._wake_event.clear()
                if self._stopper.is_set():
                    break
        except Exception:
            logger.error("Desktop overlay thread failed: %s", self.name, exc_info=True)
        finally:
            try:
                self._uninstall_event_hooks()
                self._hide()
                self._pump_messages()
                self._destroy_window()
            finally:
                self._release_bitmap_resources()
                self._wake_event.clear()
                self._hwnd = None
                self._frame = None
                self._target_window = None
                self._target_window_pid = None
                self._last_window_state = None
                self._last_canvas_state = None
                self._last_scaled_state = None
                self._last_scaled_image = None
                self._active_until = 0.0
                self._thread = None


class VRChatDesktopOverlay(DesktopOverlayWindow):
    def __init__(self, name: str):
        super().__init__(name, "vrchat.exe")


class _OverlayCommandDispatcher:
    def __init__(self):
        self._pending: dict[tuple[int, str], tuple[str, dict[str, object]]] = {}
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._thread = None
        self._started = False
        self._start_lock = threading.Lock()

    def _ensure_started(self):
        if self._started:
            return

        with self._start_lock:
            if self._started:
                return
            self._thread = threading.Thread(target=self._run, daemon=True, name="OverlayCommandSender")
            self._thread.start()
            self._started = True

    def _run(self):
        while True:
            self._event.wait()
            while True:
                with self._lock:
                    if not self._pending:
                        self._event.clear()
                        break
                    pending = list(self._pending.values())
                    self._pending.clear()

                for command, payload in pending:
                    try:
                        Manager.post(command, **payload)
                    except Exception:
                        _debug_cleanup("Failed to dispatch overlay command: %s", command)

    def submit(self, key: tuple[int, str], command: str, **payload):
        self._ensure_started()
        with self._lock:
            self._pending[key] = (command, payload)
            self._event.set()


_OVERLAY_COMMANDS = _OverlayCommandDispatcher()


class Manager:
    _client = _OverlayProcessClient()

    @classmethod
    def openvr(cls):
        _ensure_overlay_runtime()
        cls._client.start()
        cls._client.request("initialize")

    @classmethod
    def request(cls, command: str, **payload):
        return cls._client.request(command, **payload)

    @classmethod
    def post(cls, command: str, **payload):
        cls._client.post(command, **payload)

    @classmethod
    def stop(cls, immediate: bool = False):
        cls._client.stop(immediate=immediate)

    @classmethod
    def suspend(cls):
        cls._client.set_disabled(True)

    @classmethod
    def shutdown(cls, immediate: bool = False):
        cls._client.stop(disable=True, immediate=immediate)

    @classmethod
    def resume(cls):
        cls._client.set_disabled(False)


class VROverlay:
    class Align(enum.IntEnum):
        LEFT = 0
        RIGHT = 1
        TOP = 2
        BOTTOM = 3
        CENTER = 4

    def __init__(self, name: str, hide_on_dashboard: bool = False):
        self.name = name
        self.overlay_handle: int | None = None
        self.overlay = None
        self.vr = None
        self._hide_on_dashboard = False
        self._width = 0.3
        self._last_transform = None
        self._last_width_sent = None
        self._requested_visible = None
        self.HideOnDashboard = hide_on_dashboard

    @property
    def HideOnDashboard(self) -> bool:
        return self._hide_on_dashboard

    @HideOnDashboard.setter
    def HideOnDashboard(self, value: bool):
        value = bool(value)
        if self._hide_on_dashboard == value:
            return
        self._hide_on_dashboard = value
        if self.overlay_handle is not None:
            Manager.post("set_hide_on_dashboard", overlay_handle=self.overlay_handle, hide_on_dashboard=self._hide_on_dashboard)

    @property
    def Width(self) -> float:
        return self._width

    @Width.setter
    def Width(self, value: float):
        self._width = float(value)
        if self.overlay_handle is not None and self._last_width_sent != self._width:
            self._last_width_sent = self._width
            _OVERLAY_COMMANDS.submit(
                (int(self.overlay_handle), "width"),
                "set_width",
                overlay_handle=self.overlay_handle,
                width=self._width,
            )

    def __enter__(self):
        return self.init()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def init(self):
        Manager.openvr()
        self.overlay_handle = int(
            Manager.request(
                "create_overlay",
                name=self.name,
                hide_on_dashboard=self.HideOnDashboard,
            )
        )
        self.overlay = self
        self._last_transform = None
        self._last_width_sent = None
        self._requested_visible = None
        self.Width = self.Width
        return self

    def transform(
        self,
        vertical: Align = Align.LEFT,
        horizontal: Align = Align.BOTTOM,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 1.2,
        tracked_device_index: int | None = None,
    ):
        if self.overlay_handle is None:
            raise RuntimeError("Overlay is not initialized")

        transform = (
            int(vertical),
            int(horizontal),
            float(x),
            float(y),
            float(z),
            openvr.k_unTrackedDeviceIndex_Hmd if tracked_device_index is None else int(tracked_device_index),
        )
        if self._last_transform == transform:
            return self
        self._last_transform = transform

        _OVERLAY_COMMANDS.submit(
            (int(self.overlay_handle), "transform"),
            "transform",
            overlay_handle=self.overlay_handle,
            vertical=transform[0],
            horizontal=transform[1],
            x=transform[2],
            y=transform[3],
            z=transform[4],
            tracked_device_index=transform[5],
        )
        return self

    def show(self):
        if self.overlay_handle is not None and self._requested_visible is not True:
            self._requested_visible = True
            Manager.post("show_overlay", overlay_handle=self.overlay_handle)

    def hide(self):
        if self.overlay_handle is not None and self._requested_visible is not False:
            self._requested_visible = False
            Manager.post("hide_overlay", overlay_handle=self.overlay_handle)

    def stop(self):
        if self.overlay_handle is not None:
            try:
                try:
                    Manager.request("destroy_overlay", overlay_handle=self.overlay_handle)
                except Exception:
                    _debug_cleanup("Failed to destroy overlay: %s", self.name)
            finally:
                if hasattr(self, "opengl") and self.opengl is not None:
                    try:
                        self.opengl.release(self.overlay_handle)
                    except Exception:
                        _debug_cleanup("Failed to release overlay OpenGL buffers: %s", self.name)
                self.overlay_handle = None
                self.overlay = None
                self._last_transform = None
                self._last_width_sent = None
                self._requested_visible = None


class OverlayServer:
    def __init__(self):
        self.vr = None
        self.overlay = None
        self.window = None
        self._initialized = False
        self.dashboard_visible = False
        self._last_dashboard_check = 0.0
        self.texture_cache: dict[str, int] = {}
        self.texture_sizes: dict[str, tuple[int, int]] = {}
        self.pbo_cache: dict[str, int] = {}
        self.pbo_sizes: dict[str, int] = {}
        self.overlays: dict[int, dict[str, object]] = {}
        self._projection_bounds: tuple[float, float, float, float] | None = None
        self.shared_memory_cache: dict[str, shared_memory.SharedMemory] = {}
        self.texture_shared_names: dict[str, str] = {}

    def initialize(self):
        _ensure_overlay_runtime()
        if self._initialized:
            return
        openvr.init(openvr.VRApplication_Overlay)
        self.vr = openvr.VRSystem()
        self.overlay = openvr.VROverlay()
        self._initialized = True
        return True

    def _init_gl(self):
        _ensure_overlay_runtime()
        if self.window is not None:
            return
        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW for overlay host")
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        self.window = glfw.create_window(1, 1, "VRCUtil Overlay Host", None, None)
        if not self.window:
            raise RuntimeError("Failed to create the hidden overlay host window")
        glfw.make_context_current(self.window)
        glfw.swap_interval(0)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

    def _texture_key(self, overlay_handle: int, name: str) -> str:
        return f"{overlay_handle}:{name}"

    def _overlay_texture_keys(self, overlay_handle: int):
        prefix = f"{overlay_handle}:"
        return [key for key in tuple(self.texture_cache) if key.startswith(prefix)]

    def _close_cached_shared_memory(self, shared_name: str | None, message: str, *args):
        if shared_name is None:
            return
        shm = self.shared_memory_cache.pop(shared_name, None)
        if shm is not None:
            _close_shared_memory(shm, message, *args)

    def _ensure_texture(self, key: str, size: tuple[int, int]):
        texture = self.texture_cache.get(key)
        if texture is None:
            texture = glGenTextures(1)
            self.texture_cache[key] = texture
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        if self.texture_sizes.get(key) != tuple(size):
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, *size, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
            self.texture_sizes[key] = tuple(size)

    def _ensure_pbo(self, key: str, byte_length: int):
        pbo = self.pbo_cache.get(key)
        if pbo is None:
            pbo = glGenBuffers(1)
            self.pbo_cache[key] = pbo
        glBindBuffer(GL_PIXEL_UNPACK_BUFFER, pbo)
        if self.pbo_sizes.get(key) != int(byte_length):
            glBufferData(GL_PIXEL_UNPACK_BUFFER, int(byte_length), None, GL_STREAM_DRAW)
            self.pbo_sizes[key] = int(byte_length)
        return pbo

    def _apply_visibility(self, overlay_handle: int):
        state = self.overlays[overlay_handle]
        should_show = bool(state["requested_visible"]) and not (self.dashboard_visible and bool(state["hide_on_dashboard"]))
        if should_show == bool(state["visible"]):
            return

        if should_show:
            self.overlay.showOverlay(overlay_handle)
        else:
            self.overlay.hideOverlay(overlay_handle)
        state["visible"] = should_show

    def _tracks_dashboard(self) -> bool:
        return any(bool(state["hide_on_dashboard"]) for state in self.overlays.values())

    def _get_projection_bounds(self):
        self.initialize()
        if self._projection_bounds is None:
            l1, r1, b1, t1 = self.vr.getProjectionRaw(openvr.Eye_Left)
            l2, r2, b2, t2 = self.vr.getProjectionRaw(openvr.Eye_Right)
            self._projection_bounds = (max(l1, l2), min(r1, r2), max(b1, b2), min(t1, t2))
        return self._projection_bounds

    def _refresh_dashboard_visibility(self, force: bool = False):
        if not self._tracks_dashboard():
            if self.dashboard_visible:
                self.dashboard_visible = False
                for overlay_handle in tuple(self.overlays):
                    self._apply_visibility(overlay_handle)
            return

        now = time.monotonic()
        if not force and now - self._last_dashboard_check < 0.2:
            return

        self._last_dashboard_check = now
        self.initialize()
        visible = bool(self.overlay.isDashboardVisible())
        if visible == self.dashboard_visible:
            return

        self.dashboard_visible = visible
        for overlay_handle in tuple(self.overlays):
            self._apply_visibility(overlay_handle)

    def create_overlay(self, name: str, hide_on_dashboard: bool):
        self.initialize()
        overlay_handle = int(self.overlay.createOverlay(f"Haruna5718.VRCUtil.{name}.{secrets.token_hex(4)}", name))
        self.overlays[overlay_handle] = {
            "name": name,
            "hide_on_dashboard": bool(hide_on_dashboard),
            "requested_visible": False,
            "visible": False,
        }
        self.overlay.setOverlayWidthInMeters(overlay_handle, 0.3)
        self.overlay.setOverlaySortOrder(overlay_handle, 1000)
        bounds = openvr.VRTextureBounds_t()
        bounds.uMin = 0
        bounds.uMax = 1
        bounds.vMin = 1
        bounds.vMax = 0
        self.overlay.setOverlayTextureBounds(overlay_handle, bounds)
        self._refresh_dashboard_visibility(force=True)
        return overlay_handle

    def destroy_overlay(self, overlay_handle: int):
        state = self.overlays.pop(overlay_handle, None)
        if state is None:
            return
        for key in self._overlay_texture_keys(overlay_handle):
            texture = self.texture_cache.pop(key, None)
            self.texture_sizes.pop(key, None)
            pbo = self.pbo_cache.pop(key, None)
            self.pbo_sizes.pop(key, None)
            self._close_cached_shared_memory(
                self.texture_shared_names.pop(key, None),
                "Failed to close shared memory while destroying overlay resources",
            )
            if pbo is not None:
                glDeleteBuffers(1, [pbo])
            if texture is not None:
                glDeleteTextures([texture])
        if self._initialized:
            self.overlay.destroyOverlay(overlay_handle)

    def set_hide_on_dashboard(self, overlay_handle: int, hide_on_dashboard: bool):
        self.initialize()
        self.overlays[overlay_handle]["hide_on_dashboard"] = bool(hide_on_dashboard)
        self._refresh_dashboard_visibility(force=True)
        self._apply_visibility(overlay_handle)

    def set_width(self, overlay_handle: int, width: float):
        self.initialize()
        self.overlay.setOverlayWidthInMeters(overlay_handle, float(width))

    def transform(self, overlay_handle: int, vertical: int, horizontal: int, x: float, y: float, z: float, tracked_device_index: int | None = None):
        self.initialize()
        transform = openvr.HmdMatrix34_t()

        for i in range(3):
            for j in range(4):
                transform.m[i][j] = 1.0 if i == j else 0.0

        left, right, bottom, top = self._get_projection_bounds()
        transform.m[2][3] = -z

        match VROverlay.Align(vertical):
            case VROverlay.Align.LEFT:
                transform.m[0][3] = (left + x) * z
            case VROverlay.Align.RIGHT:
                transform.m[0][3] = (right - x) * z
            case _:
                transform.m[0][3] = x * z

        match VROverlay.Align(horizontal):
            case VROverlay.Align.TOP:
                transform.m[1][3] = (top - y) * z
            case VROverlay.Align.BOTTOM:
                transform.m[1][3] = (bottom + y) * z
            case _:
                transform.m[1][3] = y * z

        self.overlay.setOverlayTransformTrackedDeviceRelative(
            overlay_handle,
            openvr.k_unTrackedDeviceIndex_Hmd if tracked_device_index is None else int(tracked_device_index),
            transform,
        )

    def show_overlay(self, overlay_handle: int):
        self.initialize()
        self.overlays[overlay_handle]["requested_visible"] = True
        self._apply_visibility(overlay_handle)

    def hide_overlay(self, overlay_handle: int):
        self.initialize()
        self.overlays[overlay_handle]["requested_visible"] = False
        self._apply_visibility(overlay_handle)

    def _get_shared_memory(self, key: str, shared_name: str):
        current_name = self.texture_shared_names.get(key)
        if current_name != shared_name:
            self._close_cached_shared_memory(current_name, "Failed to close stale shared memory: %s", shared_name)
            self.texture_shared_names[key] = shared_name

        shm = self.shared_memory_cache.get(shared_name)
        if shm is None:
            shm = shared_memory.SharedMemory(name=shared_name)
            self.shared_memory_cache[shared_name] = shm
        return shm

    def set_texture_shared(self, overlay_handle: int, name: str, size: tuple[int, int], byte_length: int, shared_name: str):
        self.initialize()
        self._init_gl()
        key = self._texture_key(overlay_handle, name)
        self._ensure_texture(key, tuple(size))
        shm = self._get_shared_memory(key, shared_name)
        self._ensure_pbo(key, byte_length)
        pixel_buffer_type = ctypes.c_ubyte * int(byte_length)
        glBufferSubData(
            GL_PIXEL_UNPACK_BUFFER,
            0,
            int(byte_length),
            pixel_buffer_type.from_buffer(shm.buf),
        )
        glBindTexture(GL_TEXTURE_2D, self.texture_cache[key])
        glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            0,
            0,
            size[0],
            size[1],
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            None,
        )
        glBindBuffer(GL_PIXEL_UNPACK_BUFFER, 0)

        texture = openvr.Texture_t()
        texture.handle = ctypes.c_void_p(int(self.texture_cache[key]))
        texture.eType = openvr.TextureType_OpenGL
        texture.eColorSpace = openvr.ColorSpace_Auto
        self.overlay.setOverlayTexture(overlay_handle, texture)

    def close(self):
        _ensure_overlay_runtime()
        if self._initialized:
            for overlay_handle in tuple(self.overlays):
                try:
                    self.overlay.destroyOverlay(overlay_handle)
                except Exception:
                    _debug_cleanup("Failed to destroy overlay handle during host close: %s", overlay_handle)
        self.overlays.clear()
        self.texture_shared_names.clear()
        for shm in self.shared_memory_cache.values():
            _close_shared_memory(shm, "Failed to close shared memory during overlay host close")
        self.shared_memory_cache.clear()
        for pbo in self.pbo_cache.values():
            try:
                glDeleteBuffers(1, [pbo])
            except Exception:
                _debug_cleanup("Failed to delete OpenGL pixel buffer during overlay host close")
        self.pbo_cache.clear()
        self.pbo_sizes.clear()

        if self.window is not None:
            glfw.destroy_window(self.window)
            self.window = None
        glfw.terminate()
        if self._initialized:
            openvr.shutdown()

    def serve(self, port: int):
        listener = Listener(("127.0.0.1", port))
        try:
            connection = listener.accept()
            with connection:
                while True:
                    if not connection.poll(0.2 if self._tracks_dashboard() else 1.0):
                        self._refresh_dashboard_visibility()
                        continue

                    try:
                        request = connection.recv()
                    except EOFError:
                        break

                    if request["command"] == "shutdown":
                        connection.send({"ok": True, "result": None})
                        break

                    nowait = bool(request.get("_nowait"))
                    try:
                        result = getattr(self, request["command"])(**{k: v for k, v in request.items() if k not in {"command", "_nowait"}})
                    except Exception as exc:
                        if not nowait:
                            connection.send({"ok": False, "error": str(exc)})
                    else:
                        if not nowait:
                            connection.send({"ok": True, "result": result})
        finally:
            listener.close()
            self.close()
