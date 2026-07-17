import os
import ctypes
import logging
import socket
import subprocess
import sys
import threading
import time
from multiprocessing.connection import Client, Listener
from typing import TYPE_CHECKING, Any, cast

from . import INSTALL_PATH, IS_COMPILED

openvr = cast(Any, None)
logger = logging.getLogger("vrcutil.openvr")

if TYPE_CHECKING:
    import openvr as _openvr_module

    _VRSystemType = _openvr_module.IVRSystem
else:
    _VRSystemType = Any


def _debug_cleanup(message: str, *args):
    logger.debug(message, *args, exc_info=True)


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _host_command(port: int) -> list[str]:
    args = ["--openvr", str(port)]
    if not IS_COMPILED:
        return [sys.executable, str(INSTALL_PATH / "VRCUtil.py"), *args]
    return [str(INSTALL_PATH / "VRCUtil.exe"), *args]


def _host_startupinfo():
    if sys.platform != "win32":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.lpAttributeList["parent_process"] = int(ctypes.windll.kernel32.GetCurrentProcess())
    return startupinfo


class _OpenVRProcessClient:
    SHUTDOWN_WAIT = 0.1
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

        token = f"--openvr {int(port)}"
        escaped_token = token.replace("'", "''")
        script = (
            f"$token = '{escaped_token}';"
            f"$selfPid = {os.getpid()};"
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -like ('*' + $token + '*') -and $_.ProcessId -ne $PID -and $_.ProcessId -ne $selfPid } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        try:
            subprocess.run(
                ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except OSError:
            _debug_cleanup("Failed to clean up stray OpenVR helper processes")

    def _connect(self, port: int):
        deadline = time.time() + 10.0
        last_error = None

        while time.time() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(
                    f"OpenVR helper exited before accepting a connection (exit code {self._process.returncode})"
                ) from last_error
            try:
                return Client(("127.0.0.1", port))
            except OSError as exc:
                last_error = exc
                time.sleep(0.1)

        raise RuntimeError("Failed to connect to the OpenVR helper") from last_error

    def start(self):
        with self._lock:
            if self._connection is not None:
                return
            if self._disabled:
                raise RuntimeError("OpenVR helper startup is disabled")

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
            raise RuntimeError(response.get("error", "OpenVR helper request failed"))
        return response.get("result")

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
                try:
                    if request_shutdown:
                        connection.send({"command": "shutdown"})
                except OSError:
                    _debug_cleanup("Failed to request OpenVR helper shutdown")
                try:
                    connection.close()
                except OSError:
                    _debug_cleanup("Failed to close OpenVR helper connection")

            if process is not None:
                if immediate:
                    if os.name == "nt":
                        try:
                            subprocess.run(
                                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                check=False,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                            )
                        except OSError:
                            _debug_cleanup("Failed to force-kill OpenVR helper tree: pid=%s", process.pid)
                    else:
                        try:
                            process.kill()
                        except OSError:
                            _debug_cleanup("Failed to kill OpenVR helper process: pid=%s", process.pid)
                    try:
                        process.wait(timeout=self.KILL_WAIT)
                    except subprocess.TimeoutExpired:
                        logger.warning("OpenVR helper did not terminate after forced stop: pid=%s", process.pid)
                else:
                    if os.name == "nt":
                        try:
                            process.wait(timeout=self.SHUTDOWN_WAIT)
                        except subprocess.TimeoutExpired:
                            try:
                                subprocess.run(
                                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                    check=False,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                )
                            except OSError:
                                _debug_cleanup("Failed to force-kill OpenVR helper tree after timeout: pid=%s", process.pid)
                            try:
                                process.wait(timeout=self.KILL_WAIT)
                            except subprocess.TimeoutExpired:
                                logger.warning("OpenVR helper still alive after timeout kill: pid=%s", process.pid)
                    else:
                        try:
                            process.wait(timeout=self.SHUTDOWN_WAIT)
                        except subprocess.TimeoutExpired:
                            try:
                                process.kill()
                            except OSError:
                                _debug_cleanup("Failed to kill OpenVR helper process after timeout: pid=%s", process.pid)
                            try:
                                process.wait(timeout=self.KILL_WAIT)
                            except subprocess.TimeoutExpired:
                                logger.warning("OpenVR helper still alive after timeout kill: pid=%s", process.pid)

            self._cleanup_stray_processes(port)

    def set_disabled(self, disabled: bool):
        with self._lock:
            self._disabled = bool(disabled)


class Manager:
    _client = _OpenVRProcessClient()
    system: _VRSystemType

    @classmethod
    def openvr(cls):
        cls._client.start()
        cls._client.request("initialize")

    @classmethod
    def request(cls, command: str, **payload):
        return cls._client.request(command, **payload)

    @classmethod
    def call_many(cls, calls):
        return cls._client.request("call_vrsystem_many", calls=calls)

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


class _VRSystemProxy:
    def __init__(self):
        self._methods = {}

    def __getattr__(self, name: str):
        caller = self._methods.get(name)
        if caller is not None:
            return caller

        def caller(*args, **kwargs):
            return Manager.request("call_vrsystem", method=name, args=args, kwargs=kwargs)

        self._methods[name] = caller
        return caller


Manager.system = cast(_VRSystemType, _VRSystemProxy())


class _OpenVRServer:
    def __init__(self):
        self.openvr = None
        self.vrSystem = None

    def _initialize(self):
        if self.vrSystem is not None:
            return

        global openvr
        if self.openvr is None:
            import openvr as _openvr

            self.openvr = _openvr
            openvr = _openvr

        self.vrSystem = self.openvr.init(self.openvr.VRApplication_Background)

    def _shutdown(self):
        if self.vrSystem is None or self.openvr is None:
            self.vrSystem = None
            return

        try:
            self.openvr.shutdown()
        except Exception:
            _debug_cleanup("Failed to shut down OpenVR runtime")
        finally:
            self.vrSystem = None

    def initialize(self):
        self._initialize()
        return True

    def call_vrsystem(self, method: str, args=None, kwargs=None):
        self._initialize()
        function = getattr(self.vrSystem, method)
        return function(*(args or ()), **(kwargs or {}))

    def call_vrsystem_many(self, calls):
        self._initialize()
        results = []
        for method, args, kwargs in calls:
            try:
                function = getattr(self.vrSystem, method)
                results.append(function(*(args or ()), **(kwargs or {})))
            except Exception:
                results.append(None)
        return results

    def serve(self, port: int):
        listener = Listener(("127.0.0.1", port))
        commands = {
            "initialize": self.initialize,
            "call_vrsystem": self.call_vrsystem,
            "call_vrsystem_many": self.call_vrsystem_many,
        }
        try:
            connection = listener.accept()
            with connection:
                while True:
                    try:
                        request = connection.recv()
                    except EOFError:
                        break

                    if request["command"] == "shutdown":
                        connection.send({"ok": True, "result": None})
                        break

                    try:
                        command = commands[request["command"]]
                        result = command(**{k: v for k, v in request.items() if k != "command"})
                    except Exception as exc:
                        connection.send({"ok": False, "error": str(exc)})
                    else:
                        connection.send({"ok": True, "result": result})
        finally:
            listener.close()
            self._shutdown()


def run_openvr_helper(port: int):
    return _OpenVRServer().serve(port)
