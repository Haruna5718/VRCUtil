import openvr
from PIL import Image
import ctypes
import enum
import numpy as np
from queue import Queue
from OpenGL.GL import glDeleteTextures, glGenTextures, glBindTexture, glTexParameteri, glTexImage2D, glTexSubImage2D, glFlush, GL_TEXTURE_2D, GL_LINEAR, GL_CLAMP_TO_EDGE, GL_RGBA, GL_UNSIGNED_BYTE, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER, GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T
import glfw
import threading

class OpenGLManager:
    def __init__(self):
        self.queue = Queue()
        self.thread = threading.Thread(target=self._init, daemon=True)
        self.thread.start()

        self.cache:dict[tuple[int,int],int] = {}

    def _init(self):
        glfw.init()
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        glfw.make_context_current(glfw.create_window(1, 1, "Hidden", None, None))
        while True:
            name, image, overlay, overlay_handle = self.queue.get()
            self.create_texture(name, image)
            self.update_texture(name, image, overlay, overlay_handle)

    def create_texture(self, name:str, image:Image.Image):
        if name in self.cache:
            return
        
        self.cache[name] = glGenTextures(1)
        
        glBindTexture(GL_TEXTURE_2D, self.cache[name])
        
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, *image.size, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)

    def update_texture(self, name:str, image: Image.Image, overlay:openvr.IVROverlay, overlay_handle:int):
        width, height = image.size
        
        img_data = np.array(image, dtype=np.uint8)
        
        glBindTexture(GL_TEXTURE_2D, self.cache[name])
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        
        texture = openvr.Texture_t()
        texture.handle = ctypes.c_void_p(int(self.cache[name]))
        texture.eType = openvr.TextureType_OpenGL
        texture.eColorSpace = openvr.ColorSpace_Auto
        
        overlay.setOverlayTexture(overlay_handle, texture)

    def submit(self, image, overlay:openvr.IVROverlay, overlay_handle:int, name:str="Default"):
        self.queue.put((name, image, overlay, overlay_handle))

class Manager():
    def openvr():
        openvr.init(openvr.VRApplication_Overlay)

    def stop():
        glfw.terminate()
        openvr.shutdown()

class VROverlay:
    class Align(enum.IntEnum):
        LEFT = 0
        RIGHT = 1
        TOP = 2
        BOTTOM = 3
        CENTER = 4

    def __init__(self, name: str):
        self.name = name
        self.overlay_handle: int = None
        self.overlay: openvr.IVROverlay = None
        
    def __enter__(self):
        return self.init()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        
    def init(self):
        self.vr = openvr.VRSystem()
        self.overlay = openvr.VROverlay()
        self.overlay_handle = self.overlay.createOverlay(f"vrcutil.overlay.{self.name}", self.name)
        self.overlay.setOverlayWidthInMeters(self.overlay_handle, 0.3)
        # self.overlay.setOverlaySortOrder(self.overlay_handle, 1000)
        bounds = openvr.VRTextureBounds_t()
        bounds.uMin = 0
        bounds.uMax = 1
        bounds.vMin = 1
        bounds.vMax = 0
        self.overlay.setOverlayTextureBounds(self.overlay_handle, bounds)

        return self
        
    def transform(self, vertical:Align=Align.LEFT, horizontal:Align=Align.BOTTOM, x:float=0.0, y:float=0.0, z:float=1.2):

        l1, r1, b1, t1 = self.vr.getProjectionRaw(openvr.Eye_Left)
        l2, r2, b2, t2 = self.vr.getProjectionRaw(openvr.Eye_Right)
        
        transform = openvr.HmdMatrix34_t()
        
        for i in range(3):
            for j in range(4):
                transform.m[i][j] = 1.0 if i == j else 0.0

        transform.m[2][3] = -z

        match vertical:
            case self.Align.LEFT:
                transform.m[0][3] = (max(l1, l2) + x)*z
            case self.Align.RIGHT:
                transform.m[0][3] = (min(r1, r2) - x)*z
            case _:
                transform.m[0][3] = x*z
        match horizontal:
            case self.Align.TOP:
                transform.m[1][3] = (min(t1, t2) - y)*z
            case self.Align.BOTTOM:
                transform.m[1][3] = (max(b1, b2) + y)*z
            case _:
                transform.m[1][3] = y*z
        
        self.overlay.setOverlayTransformTrackedDeviceRelative(
            self.overlay_handle,
            openvr.k_unTrackedDeviceIndex_Hmd,
            transform
        )
        return self
        
    def show(self):
        self.overlay.showOverlay(self.overlay_handle)
        
    def hide(self):
        self.overlay.hideOverlay(self.overlay_handle)
        
    def stop(self):
        if self.overlay_handle is not None:
            self.overlay.destroyOverlay(self.overlay_handle)