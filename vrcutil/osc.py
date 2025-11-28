import http.server
import json
import threading
import socket
import datetime
from pythonosc import osc_server, udp_client, dispatcher
import zeroconf
import pathlib
import logging

logger = logging.getLogger("vrcutil.osc")

class VRChatOSCEvent:
    @staticmethod
    def _setHandler(path):
        def decorator(func):
            if not hasattr(func, "__VRCUtil_OSCListen__"):
                func.__VRCUtil_OSCListen__ = []
            func.__VRCUtil_OSCListen__.append(path)
            
            return func
        return decorator
	
    @classmethod
    def onChange(cls, Path):
        return cls._setHandler(Path)
    
    @classmethod
    def onAvatarParameterChange(cls, Parameter):
        return cls._setHandler((pathlib.Path("/avatar/parameters")/Parameter).as_posix())
    
    @classmethod
    def onAvatarChange(cls):
        return cls._setHandler("/avatar/change")

def getUnusedPort():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]
            
class EasyOSCUDPServer(osc_server.ThreadingOSCUDPServer):
    def __init__(self, server_address: tuple[str, int], dispatcher: dispatcher.Dispatcher, bind_and_activate: bool = True):
        super().__init__(server_address, dispatcher, bind_and_activate)
        self.isactive: bool = bind_and_activate

    def serveWithBind(self, poll_interval:float=0.5, background=True):
        self.server_bind()
        self.server_activate()
        if background:
            threading.Thread(target=self.serve_forever, args=(poll_interval,), daemon=True).start()
        else:
            self.serve_forever(poll_interval)

    def serve_forever(self, poll_interval:float=0.5):
        try:
            self.isactive = True
            super().serve_forever(poll_interval)
        finally:
            self.isactive = False

class OSCQueryHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        key = (self.client_address[0], self.path)
        now = datetime.datetime.now().timestamp()
        if now - self.server.lastReq.get(key,0) < 1.0:
            return
        self.server.lastReq[key] = now
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "NAME": self.server.info.name.split(".")[0],
            "OSC_IP": socket.inet_ntoa(self.server.info.addresses[0]),
            "OSC_PORT": self.server.info.port,
            "OSC_TRANSPORT": "UDP"
        } if self.path.endswith("?HOST_INFO") else {
            "CONTENTS": {
                "avatar": {"FULL_PATH": "/avatar"},
                "tracking": {"FULL_PATH": "/tracking"},
            }
        }).encode())

class EasyOSCQueryServer(http.server.HTTPServer):
    def __init__(self, server_address: tuple[str, int], name:str, host:str, port:int=None, bind_and_activate: bool = True):
        super().__init__(server_address, OSCQueryHandler, bind_and_activate)
        self.isactive: bool = bind_and_activate
        self.zeroconf = zeroconf.Zeroconf()
        self.info = zeroconf.ServiceInfo(
            "_oscjson._tcp.local.",
            f"{name}._oscjson._tcp.local.",
            addresses = [socket.inet_pton(socket.AF_INET, host)],
            port = port or server_address[1],
        )
        self.lastReq = {}

    def shutdown(self):
        threading.Thread(target=self.zeroconf.unregister_service, args=(self.info,), daemon=True).start()
        self.zeroconf.close()
        super().shutdown()

    def serveWithBind(self, poll_interval:float=0.5, background=True):
        self.server_bind()
        self.server_activate()
        threading.Thread(target=self.zeroconf.register_service, args=(self.info,), daemon=True).start()
        if background:
            threading.Thread(target=self.serve_forever, args=(poll_interval,), daemon=True).start()
        else:
            self.serve_forever(poll_interval)

    def serve_forever(self, poll_interval: float = 0.5):
        try:
            self.isactive = True
            super().serve_forever(poll_interval)
        finally:
            self.isactive = False

class EasyOSC:
    def __init__(self, name:str, host:str=None, clientPort:int=None, serverPort:int=None, init=True):
        self.client:udp_client.SimpleUDPClient = None
        self.server:EasyOSCUDPServer = None
        self.oscquery:EasyOSCQueryServer = None
        self._dispatcher = dispatcher.Dispatcher()
        if init:
            threading.Thread(target=self._initClient, args=(host,clientPort,), daemon=True).start()
            threading.Thread(target=self._initServer, args=(name,host,serverPort,), daemon=True).start()

    def _initClient(self, host:str, port:int):
        self.client = udp_client.SimpleUDPClient(host, port)
        logger.info(f"OSC Client configured {self.client._address}:{self.client._port}")

    def _initServer(self, name:str, host:str, port:int):
        self._stopServers()
        while not getattr(self.server,'isactive',False) or not getattr(self.oscquery,'isactive',False):
            port = port or getUnusedPort()
            try:
                self.server = EasyOSCUDPServer((host, port), self._dispatcher, bind_and_activate=False)
                self.server.serveWithBind()
            except Exception as e:
                logger.warning(f"failed to launch OSC server: {e}")
                self._stopServers()
                port = None
                continue
            try:
                self.oscquery = EasyOSCQueryServer(("0.0.0.0", port), name=name, host=host, port=port, bind_and_activate=False)
                self.oscquery.serveWithBind()
            except Exception as e:
                logger.warning(f"failed to launch OSCQuery server: {e}")
                self._stopServers()
                port = None
                continue
        logger.info(f"OSC with OSCQuery server listening {self.server.server_address[0]}:{self.server.server_address[1]}")

    def _stopServers(self):
        if getattr(self.server,'isactive',False):
            self.server.shutdown()
        if getattr(self.oscquery,'isactive',False):
            self.oscquery.shutdown()

    def stop(self):
        self._stopServers()
        logger.info("OSC with OSCQuery server shutdown")

    def send(self, path, value):
        self.client.send_message(path, value)

    def addHandler(self, path:str, callback, *args: list, needs_reply_address: bool = False):
        self._dispatcher.map(path, callback, *args, needs_reply_address)

    def removeHandler(self, path:str, callback):
        self._dispatcher.unmap(path, callback)

    def getHandlers(self, path:str=None, callback=None):
        m = self._dispatcher._map

        if not path and not callback:
            return m

        paths = [path] if path else list(m.keys())

        return {
            p: filtered for p in paths
            if (handlers := m.get(p)) and (
                filtered := (
                    handlers if not callback else [h for h in handlers if h[0] == callback]
                )
            )
        }