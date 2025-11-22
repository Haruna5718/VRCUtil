import pathlib
import zipfile
import json
import threading
import win32con
import webbrowser
import sys
import ctypes
import enum
import subprocess

if len(sys.argv) < 2:
    sys.exit(1)

if "debug" in sys.argv:
    ctypes.windll.kernel32.AllocConsole()
    sys.stdout = open("CONOUT$", "w")
    sys.stderr = open("CONOUT$", "w")
    sys.stdin  = open("CONIN$", "r")

modulePath = pathlib.Path(sys.argv[1])

import customtkinter

from pywebwinui3 import getSystemAccentColor, systemMessageListener

from vrcutil import MODULES_PATH, INSTALL_PATH

def darken(hex:str, factor:float = 0.1) -> str:
    hex = hex.lstrip("#")

    r = max(0, int(int(hex[0:2], 16) * (1 - factor)))
    g = max(0, int(int(hex[2:4], 16) * (1 - factor)))
    b = max(0, int(int(hex[4:6], 16) * (1 - factor)))

    return f"#{r:02X}{g:02X}{b:02X}"

class Colors(enum.Enum):
    Accent = [[],[],["#ffffff","#000000"]]
    Default = [["#fefefe","#3e3e3e"],["#fbfbfb","#444444"],["#000000","#ffffff"]]
    Success = [["#0F7B0F","#6ccb5f"],["#0D6E0D","#61B655"],["#ffffff","#000000"]]
    Caution = [["#9D5D00","#fce100"],["#8D5300","#E2CA00"],["#ffffff","#000000"]]
    Critical = [["#C42B1C","#ff99a4"],["#B02619","#E58993"],["#ffffff","#000000"]]

class UrlButtonColors(enum.Enum):
    X = ["#000000","#131313","#ffffff"]
    Booth = ["#FC4D50","#E24548","#ffffff"]
    Github = ["#001C4D","#001945","#ffffff"]
    Twitter = ["#00ACEE","#009AD6","#ffffff"]
    Discord = ["#5865F2","#4F5AD9","#ffffff"]

class ModuleInstaller(customtkinter.CTk):
    def __init__(self, title="VRCUtil Module Installer", size="400x200", icon=INSTALL_PATH/"VRCUtil.ico"):
        super().__init__()
        self.title(title)
        self.geometry(size)
        self.iconbitmap(icon)
        self.accentItems:list[customtkinter.CTkButton] = []
        self.init()
        self._applyAccentColor(getSystemAccentColor())

    def init(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.screen = ModuleInfoFrame(self)
        self.screen.grid(row=0, padx=10, pady=(10, 0), sticky="sew")

        self.mainButton = VRCUtilButton(self, text="Install Module", color=Colors.Accent, callback=self.installModule)
        self.mainButton.grid(row=1, padx=10, pady=10, sticky="ews")

    def installModule(self):
        self.screen.destroy()
        self.mainButton.setStatus(False)
        self.mainButton.configure(command=lambda: sys.exit(1))
        self.screen = ModuleInstallPage(self)
        self.screen.grid(row=0, padx=10, pady=(10, 0), sticky="sew")

    def _setWinStyle(self):
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, -16)
        ctypes.windll.user32.SetWindowLongPtrW(hwnd, -16, style & ~ 65536 & ~ 131072)
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 2 | 1 | 4 | 32)

    def _applyAccentColor(self, color=None):
        self.accentColor = color or self.accentColor

        fg_color = (self.accentColor[4],self.accentColor[1])
        hover_color = (darken(self.accentColor[4]),darken(self.accentColor[1]))

        for item in self.accentItems:
            if hasattr(item, "_progress_color"):
                item.configure(progress_color=fg_color)
            else:
                item.configure(fg_color=fg_color, hover_color=hover_color)

    def _systemMessageHandler(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_SETTINGCHANGE:
            if self.accentColor!=(color:=getSystemAccentColor()):
                self.after(0, lambda: self._applyAccentColor(color))

    def start(self):
        customtkinter.set_appearance_mode("system")
        threading.Thread(target=systemMessageListener, args=(self._systemMessageHandler,), daemon=True).start()
        self.resizable(False, False)
        self.after(10, lambda: self._setWinStyle())
        super().mainloop()

class VRCUtilButton(customtkinter.CTkButton):
    def __init__(self, master:ModuleInstaller, text:str, callback=None, color:Colors=Colors.Default, **kwargs):
        super().__init__(master, text=text, command=callback, **kwargs)
        if color==Colors.Accent:
            self.configure(text_color=color.value[2])
            self.master.accentItems.append(self)
        elif color:
            self.configure(fg_color=color.value[0], hover_color=color.value[1], text_color=color.value[2])

    def setStatus(self, state:bool, text=None):
        self.configure(text=text or self._text, state="normal" if state else "disabled", fg_color=(self.master.accentColor[4],self.master.accentColor[1]) if state else ("#fefefe","#3e3e3e"))

class ModuleInstallPage(customtkinter.CTkFrame):
    def __init__(self, master:ModuleInstaller):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.message = customtkinter.CTkLabel(self, text=f'Installing {installData["name"]} {installData["version"]}', height=16)
        self.message.grid(row=0, padx=10, pady=(10, 5), sticky="nw")
        self.progress = customtkinter.CTkProgressBar(self, progress_color=(self.master.accentColor[4],self.master.accentColor[1]))
        self.progress.set(0)
        self.progress.grid(row=1, padx=10, sticky="ew")
        self.master.accentItems.append(self.progress)
        self.logFrame = customtkinter.CTkTextbox(self)
        self.logFrame.grid(row=2, padx=10, pady=10, sticky="nsew")

        self.count = 0

        threading.Thread(target=self.install,daemon=True).start()

    def install(self):
        try:
            with zip_ref.open("requirements.txt") as f:
                requirements = [line.strip() for line in f.read().decode("utf-8").splitlines() if line.strip()]
        except:
            requirements=[]

        file_list = zip_ref.infolist()
            
        self.max = len(file_list)+len(requirements)

        path = MODULES_PATH/f'{installData["path"]}'
        self.after(0, lambda: self.log(f"Install path: {path}"))

        if not path.exists():
            self.max += 1
            path.mkdir(parents=True)
            self.after(0, lambda: self.work())

        for info in file_list:
            if info.is_dir():
                self.after(0, lambda name=info.filename: self.log(f"\nExtract: {name}"))
                self.after(0, lambda: self.work())
            else:
                self.after(0, lambda name=info.filename: self.log(f"\nExtract: {name}"))
                zip_ref.extract(info, path)
                self.after(0, lambda: self.work())

        for moduleName in requirements:
            self.after(0, lambda name=moduleName: self.log(f"\nPackage install: {name}"))
            subprocess.run([str(INSTALL_PATH/"_internal/pip.exe"), "install", "--no-cache-dir", moduleName, "--target", str(INSTALL_PATH / "_internal")],creationflags=subprocess.CREATE_NO_WINDOW)
            self.after(0, lambda: self.work())

    def work(self):
        self.count+=1
        self.progress.set(self.count/self.max)
        if self.count>=self.max:
            self.master.mainButton.setStatus(True, "Close")
            self.state(f'Installed {installData["name"]} {installData["version"]}')

    def state(self, message):
        self.message.configure(text=message)

    def log(self, message):
        self.logFrame.configure(state="normal")
        self.logFrame.insert("end", message)
        self.logFrame.see("end")
        self.logFrame.configure(state="disabled")

class ModuleInfoFrame(customtkinter.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        customtkinter.CTkLabel(self, text=installData["name"], font=customtkinter.CTkFont(size=24, weight="bold")).grid(row=0, padx=10, pady=(10, 0), sticky="nw")
        customtkinter.CTkLabel(self, text=installData["version"], font=customtkinter.CTkFont(size=12)).grid(row=0, padx=15, pady=(7, 0), sticky="ne")
        customtkinter.CTkLabel(self, text=installData["author"], height=24).grid(row=1, padx=13, pady=(4, 0), sticky="sw")
        
        self.frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.frame.grid(row=1, padx=10, sticky="se")
        
        for data in installData["urls"]:
            name, url = list(data.items())[0]
            VRCUtilButton(self.frame, text=name, width=0, callback=lambda: webbrowser.open(url), color=UrlButtonColors[name] if name in UrlButtonColors.__members__ else Colors.Default).pack(padx=(5, 0), side="right")
        self.des = customtkinter.CTkTextbox(self, font=customtkinter.CTkFont(size=14))
        self.des.grid(row=2, padx=10, pady=10, sticky="nsew")
        self.des.insert("0.0", installData["description"])
        self.des.configure(state="disabled")

with zipfile.ZipFile(modulePath, 'r') as zip_ref:
    with zip_ref.open("module.json") as f:
        installData = json.load(f)

        ModuleInstaller().start()