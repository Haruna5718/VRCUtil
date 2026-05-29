import ctypes
import enum
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from multiprocessing.connection import Client, Listener
from multiprocessing import shared_memory
from typing import Any, cast

os.environ["PYOPENGL_USE_ACCELERATE"] = "0"

from . import INSTALL_PATH, IS_COMPILED

_overlay_runtime_ready = False

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
	from PIL import Image as imported_Image

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
	Image = imported_Image
	_overlay_runtime_ready = True


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _host_command(port: int, key: str) -> list[str]:
    args = [f"--overlay", f"{port}", f"{key}"]
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
    KILL_WAIT = 0.4

    def __init__(self):
        self._connection = None
        self._process = None
        self._lock = threading.RLock()

    def _connect(self, port: int, key: bytes):
        deadline = time.time() + 10.0
        last_error = None

        while time.time() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(
                    f"Overlay host exited before accepting a connection (exit code {self._process.returncode})"
                ) from last_error
            try:
                return Client(("127.0.0.1", port), authkey=key)
            except OSError as exc:
                last_error = exc
                time.sleep(0.1)

        raise RuntimeError("Failed to connect to the overlay host") from last_error

    def start(self):
        with self._lock:
            if self._connection is not None:
                return
            port = _reserve_port()
            key_text = secrets.token_hex(32)
            key = key_text.encode("ascii")
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self._process = subprocess.Popen(
                _host_command(port, key_text),
                creationflags=creationflags,
                cwd=INSTALL_PATH,
                startupinfo=_host_startupinfo(),
            )

            try:
                self._connection = self._connect(port, key)
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

    def stop(self, request_shutdown: bool = True):
        with self._lock:
            connection = self._connection
            process = self._process
            self._connection = None
            self._process = None

            if connection is not None:
                try:
                    if request_shutdown:
                        connection.send({"command": "shutdown"})
                except OSError:
                    pass
                try:
                    connection.close()
                except OSError:
                    pass

            if process is not None:
                try:
                    process.wait(timeout=self.SHUTDOWN_WAIT)
                except subprocess.TimeoutExpired:
                    try:
                        process.kill()
                    except OSError:
                        pass
                    try:
                        process.wait(timeout=self.KILL_WAIT)
                    except subprocess.TimeoutExpired:
                        pass


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
            try:
                shm.close()
            except Exception:
                pass
            try:
                shm.unlink()
            except Exception:
                pass

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
                try:
                    shm.close()
                except Exception:
                    pass
                try:
                    shm.unlink()
                except Exception:
                    pass

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
                        pass

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
    def stop(cls):
        cls._client.stop()


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
                Manager.request("destroy_overlay", overlay_handle=self.overlay_handle)
            finally:
                if hasattr(self, "opengl") and self.opengl is not None:
                    try:
                        self.opengl.release(self.overlay_handle)
                    except Exception:
                        pass
                self.overlay_handle = None
                self.overlay = None
                self._last_transform = None
                self._last_width_sent = None
                self._requested_visible = None


class _OverlayServer:
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
        for key in tuple(self.texture_cache):
            if key.startswith(f"{overlay_handle}:"):
                texture = self.texture_cache.pop(key, None)
                self.texture_sizes.pop(key, None)
                pbo = self.pbo_cache.pop(key, None)
                self.pbo_sizes.pop(key, None)
                shared_name = self.texture_shared_names.pop(key, None)
                if shared_name is not None:
                    shm = self.shared_memory_cache.pop(shared_name, None)
                    if shm is not None:
                        try:
                            shm.close()
                        except Exception:
                            pass
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
            stale = self.shared_memory_cache.pop(current_name, None) if current_name is not None else None
            if stale is not None:
                try:
                    stale.close()
                except Exception:
                    pass
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
                    pass
        self.overlays.clear()
        self.texture_shared_names.clear()
        for shm in self.shared_memory_cache.values():
            try:
                shm.close()
            except Exception:
                pass
        self.shared_memory_cache.clear()
        for pbo in self.pbo_cache.values():
            try:
                glDeleteBuffers(1, [pbo])
            except Exception:
                pass
        self.pbo_cache.clear()
        self.pbo_sizes.clear()

        if self.window is not None:
            glfw.destroy_window(self.window)
            self.window = None
        glfw.terminate()
        if self._initialized:
            openvr.shutdown()

    def serve(self, port: int, key: str):
        listener = Listener(("127.0.0.1", port), authkey=key.encode("ascii"))
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
