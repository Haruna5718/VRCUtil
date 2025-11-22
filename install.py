import pathlib
import datetime
import subprocess
import os
import threading
import win32con
import webbrowser
import sys
import ctypes
import shutil
import enum
import customtkinter
from PIL import Image

from pywebwinui3 import getSystemAccentColor, systemMessageListener

from vrcutil import registry, __version__

if "debug" in sys.argv:
    ctypes.windll.kernel32.AllocConsole()
    sys.stdout = open("CONOUT$", "w")
    sys.stderr = open("CONOUT$", "w")
    sys.stdin  = open("CONIN$", "r")

def createShortcut(target:str|pathlib.Path,outPath:str|pathlib.Path):
    target = pathlib.Path(target).resolve()
    subprocess.run((
        f'powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut(\\"{pathlib.Path(outPath).resolve()}\\");'
        f'$s.TargetPath=\\"{target}\\";'
        f'$s.WorkingDirectory=\\"{target.parent}\\";'
        f'$s.IconLocation=\\"{target}\\";'
        '$s.Save()"'
    ), shell=True, check=True)

class Colors(enum.Enum):
    Accent = [[],[],["#ffffff","#000000"]]
    Default = [["#fefefe","#3e3e3e"],["#fbfbfb","#444444"],["#000000","#ffffff"]]
    Success = [["#0F7B0F","#6ccb5f"],["#0D6E0D","#61B655"],["#ffffff","#000000"]]
    Caution = [["#9D5D00","#fce100"],["#8D5300","#E2CA00"],["#ffffff","#000000"]]
    Critical = [["#C42B1C","#ff99a4"],["#B02619","#E58993"],["#ffffff","#000000"]]

class UrlButtonColors(enum.Enum):
    X = ["#000000","#131313","#ffffff"]
    Booth = ["#FC4D50","#E24548","#ffffff"]
    Github = ["#000000","#131313","#ffffff"]
    Twitter = ["#00ACEE","#009AD6","#ffffff"]
    Discord = ["#5865F2","#4F5AD9","#ffffff"]

class AccentColorManager:
    def __init__(self, root:customtkinter.CTk):
        self.root = root
        self.elements = []
        self.accentColor = getSystemAccentColor()
        self.accentDarken = list(map(self.darken,self.accentColor))
        threading.Thread(target=systemMessageListener, args=(self.systemMessageHandler,), daemon=True).start()

    @staticmethod
    def darken(hex:str, factor:float = 0.1) -> str:
        r = max(0, int(int(hex[1:3], 16) * (1 - factor)))
        g = max(0, int(int(hex[3:5], 16) * (1 - factor)))
        b = max(0, int(int(hex[5:7], 16) * (1 - factor)))
        return f"#{r:02X}{g:02X}{b:02X}"

    def append(self, element):
        self.elements.append(element)
        self.root.after(0, element.onAccentChange)

    def remove(self, element):
        self.elements.remove(element)

    def syncColor(self):
        for element in self.elements:
            self.root.after(0, element.onAccentChange)

    def systemMessageHandler(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_SETTINGCHANGE:
            if self.accentColor!=(color:=getSystemAccentColor()):
                self.accentColor = color
                self.accentDarken = list(map(self.darken,self.accentColor))
                self.syncColor()

class VRCUtilButton(customtkinter.CTkButton):
    def __init__(self, master:customtkinter.CTk, acm:AccentColorManager, text:str, callback=None, color:Colors=Colors.Default, **kwargs):
        super().__init__(master, text=text, command=self.onClick, text_color=color.value[2], **kwargs)
        self.callback = callback
        self.acm = acm
        if color==Colors.Accent:
            self.acm.append(self)
        elif color:
            self.configure(fg_color=color.value[0], hover_color=color.value[1])

    def onClick(self):
        if self.callback:
            self.callback(self)

    def config(self, state:bool, text=None):
        self.configure(text=text or self._text, state="normal" if state else "disabled", fg_color=(self.acm.accentColor[4],self.acm.accentColor[1]) if state else ("#fefefe","#3e3e3e"))

    def onAccentChange(self):
        self.configure(fg_color=[self.acm.accentColor[4],self.acm.accentColor[1]], hover_color=[self.acm.accentDarken[4],self.acm.accentDarken[1]])

class VRCUtilProgressBar(customtkinter.CTkProgressBar):
    def __init__(self, master:customtkinter.CTk, acm:AccentColorManager, **kwargs):
        super().__init__(master, **kwargs)
        self.acm = acm
        self.acm.append(self)

    def onAccentChange(self):
        self.configure(progress_color=[self.acm.accentColor[4],self.acm.accentColor[1]])

class VRCUtilCheckBox(customtkinter.CTkCheckBox):
    def __init__(self, master:customtkinter.CTk, acm:AccentColorManager, text:str, callback=None, **kwargs):
        self.variable=customtkinter.IntVar(value=0)
        super().__init__(master, text=text, variable=self.variable, command=self.onClick, checkmark_color=["#ffffff","#000000"], height=24, **kwargs)
        self.callback = callback
        self.acm = acm
        self.acm.append(self)
    
    @property
    def value(self):
        return self.variable.get()

    def onClick(self, isCallback=True):
        self.configure(hover_color=[self.acm.accentDarken[4],self.acm.accentDarken[1]] if self.value else ["#fbfbfb","#444444"])
        if isCallback and self.callback:
            self.callback(self)

    def onAccentChange(self):
        self.configure(fg_color=[self.acm.accentColor[4],self.acm.accentColor[1]])
        self.onClick(isCallback=False)

class VRCUtilTextbox(customtkinter.CTkTextbox):
    def __init__(self, master:customtkinter.CTk, readonly=False, **kwargs):
        super().__init__(master, **kwargs)
        self.isReadonly = readonly

    def read(self, start="1.0", end="end"):
        return self.get(start, end).strip()

    def write(self, content:str, position="end"):
        if self.isReadonly:
            self.configure(state="normal")
        self.insert(position, content)
        self.see("end")
        if self.isReadonly:
            self.configure(state="disabled")

    def delete(self, start="1.0", end="end"):
        if self.isReadonly:
            self.configure(state="normal")
        super().delete(start, end)
        self.see("end")
        if self.isReadonly:
            self.configure(state="disabled")

    def readonly(self, state=True):
        self.isReadonly = state
        if self.isReadonly:
            self.configure(state="disabled")
        else:
            self.configure(state="normal")

class VRCUtilCTkApp(customtkinter.CTk):
    def __init__(self, title:str, size:str, icon:str|pathlib.Path, resize:bool=True):
        super().__init__(fg_color=["#f3f3f3","#202020"])
        customtkinter.set_appearance_mode("system")
        if not resize:
            self.after(0, lambda: self._setWinStyle())
            self.resizable(False, False)
        self.acm = AccentColorManager(self)
        self.iconbitmap(icon)
        self.geometry(size)
        self.title(title)

    def _setWinStyle(self):
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, -16)
        ctypes.windll.user32.SetWindowLongPtrW(hwnd, -16, style & ~ 65536 & ~ 131072)
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 2 | 1 | 4 | 32)

    def start(self):
        super().mainloop()

class VRCUtilCTkPage(customtkinter.CTkFrame):
    def __init__(self, master, acm:AccentColorManager):
        super().__init__(master, fg_color=["#f9f9f9","#272727"], corner_radius=0)
        self.master = master
        self.acm = acm

# ========================================================

class MainWindow(VRCUtilCTkApp):
    def __init__(self, title:str, size:str, icon:str|pathlib.Path, resize:bool=True):
        super().__init__(title, size, icon, resize)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.installPath = pathlib.Path(os.environ["LOCALAPPDATA"])/"Programs/VRCUtil"

        self.page = WelcomPage(self, self.acm)
        self.page.grid(row=0, sticky="snew")

        self.autoLaunch = VRCUtilCheckBox(self, self.acm, text="Launch VRCUtil after installed")
        self.autoLaunch.grid(row=1, padx=20, pady=20, sticky="w")


        VRCUtilButton(self, self.acm, text="Install", color=Colors.Accent, callback=self.install).grid(row=1, padx=20, pady=20, sticky="e")

    def install(self, target:VRCUtilButton):
        self.installPath = pathlib.Path(self.page.installPath.read())
        self.page.destroy()
        target.config(False,"Installing")
        self.page = InstallPage(self, self.acm, target)
        self.page.grid(row=0, sticky="snew")

class WelcomPage(VRCUtilCTkPage):
    def __init__(self, master:MainWindow, acm):
        super().__init__(master, acm)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        customtkinter.CTkLabel(self, image=customtkinter.CTkImage(light_image=Image.open(pathlib.Path(sys._MEIPASS)/"VRCUtil.ico"),size=(84, 84)), text="").grid(row=0, padx=20, pady=20, sticky="ne", rowspan=3)

        customtkinter.CTkLabel(self, text="VRCUtil", font=customtkinter.CTkFont(size=24, weight="bold")).grid(row=0, padx=20, pady=(20,0), sticky="nw")
        customtkinter.CTkLabel(self, text=f"Version: {__version__}").grid(row=1, padx=23, pady=(0, 28), sticky="nw")
        
        self.frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.frame.grid(row=2, padx=20, sticky="nw")
        
        VRCUtilButton(self.frame, self.acm, text="Booth", width=0, callback=lambda: webbrowser.open("https://haruna5718.booth.pm/items/6516021"), color=UrlButtonColors.Booth).pack(padx=(5, 0), side="left")
        VRCUtilButton(self.frame, self.acm, text="Github", width=0, callback=lambda: webbrowser.open("https://github.com/Haruna5718/VRCUtil"), color=UrlButtonColors.Github).pack(padx=(5, 0), side="left")

        customtkinter.CTkLabel(self, text="Install path", height=18, font=customtkinter.CTkFont(size=12)).grid(row=4, padx=23, sticky="nw")
        self.installPath = VRCUtilTextbox(self, font=customtkinter.CTkFont(size=14), height=28)
        self.installPath.grid(row=5, padx=20, pady=(0, 20), sticky="ew")
        self.installPath.write(self.master.installPath)

class InstallPage(VRCUtilCTkPage):
    def __init__(self, master:MainWindow, acm, button:VRCUtilButton):
        super().__init__(master, acm)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.button = button

        self.message = customtkinter.CTkLabel(self, text=f'Installing VRCUtil {__version__}', height=16)
        self.message.grid(row=0, padx=10, pady=(10, 5), sticky="nw")

        self.progress = VRCUtilProgressBar(self, self.acm)
        self.progress.set(0)
        self.progress.grid(row=1, padx=10, sticky="ew")

        self.installLog = VRCUtilTextbox(self, readonly=True)
        self.installLog.grid(row=2, padx=10, pady=10, sticky="nsew")

        threading.Thread(target=self.install,daemon=True).start()

    def install(self):
        self.after(0, lambda: self.installLog.write(f"Install path: {self.master.installPath}"))
        sourcePath = pathlib.Path(sys._MEIPASS)/"data"
        totalProgress = sum([len(files) for _, _, files in os.walk(sourcePath)])+6
        currentProgress = 0

        for filePath, _, fileNames in os.walk(sourcePath):
            filePath = pathlib.Path(filePath)
            realPath = filePath.relative_to(sourcePath)
            targetPath = self.master.installPath/realPath
            targetPath.mkdir(parents=True,exist_ok=True)
            for filename in fileNames:
                self.after(0, lambda d=realPath/filename: self.installLog.write(f"\nExtract: {d}"))
                shutil.copy(filePath/filename, targetPath/filename)
                currentProgress += 1
                self.after(0, lambda: self.progress.set(currentProgress/totalProgress))

        registry.Program.install(
            id = "VRCUtil",
            name = "VRCUtil",
            icon = self.master.installPath/"VRCUtil.exe",
            version = __version__,
            author = "Haruna5718",
            uninstaller = self.master.installPath/"Uninstall.exe",
            installDir = self.master.installPath,
            installDate = datetime.datetime.now()
        )
        currentProgress += 1
        self.after(0, lambda: self.progress.set(currentProgress/totalProgress))
        self.after(0, lambda: self.installLog.write("\nRegistry configured: Software\\Microsoft\\\Windows\\CurrentVersion\\Uninstall\\VRCUtil"))

        registry.ExtConnector.connect(
            id = "VRCUtilModuleFile",
            ext = "vrcutilmodule",
            target = self.master.installPath/"ModuleInstaller.exe",
            description = "VRCUtil Module File",
            icon = self.master.installPath/"ModuleInstaller.exe"
        )
        currentProgress += 1
        self.after(0, lambda: self.progress.set(currentProgress/totalProgress))
        self.after(0, lambda: self.installLog.write(f"\next connected: .vrcutilmodule > {self.master.installPath/'ModuleInstaller.exe'}"))

        registry.Program.setAutostart(
            name = "VRCUtil Service Worker",
            path = self.master.installPath/"ServiceWorker.exe"
        )
        currentProgress += 1
        self.after(0, lambda: self.progress.set(currentProgress/totalProgress))
        self.after(0, lambda: self.installLog.write(f"\nStartup program registed: {self.master.installPath/'ServiceWorker.exe'}"))

        subprocess.Popen([self.master.installPath/"ServiceWorker.exe"], cwd=self.master.installPath)
        currentProgress += 1
        self.after(0, lambda: self.progress.set(currentProgress/totalProgress))
        self.after(0, lambda: self.installLog.write(f"\nServiceWorker launched"))

        createShortcut(self.master.installPath/"VRCUtil.exe",pathlib.Path(os.environ["APPDATA"])/"Microsoft/Windows/Start Menu/Programs/VRCUtil.lnk")
        currentProgress += 1
        self.after(0, lambda: self.progress.set(currentProgress/totalProgress))
        self.after(0, lambda: self.installLog.write(f"\nStart menu shortcut created: VRCUtil.lnk"))

        createShortcut(self.master.installPath/"VRCUtil.exe",pathlib.Path(os.environ["USERPROFILE"])/"Desktop/VRCUtil.lnk")
        currentProgress += 1
        self.after(0, lambda: self.progress.set(currentProgress/totalProgress))
        self.after(0, lambda: self.installLog.write(f"\nDesktop shortcut created: VRCUtil.lnk"))

        self.after(0, lambda: self.message.configure(text=f'Installed VRCUtil {__version__}'))

        if self.master.autoLaunch.value:
            subprocess.Popen([self.master.installPath/"VRCUtil.exe"], cwd=self.master.installPath)
            self.master.autoLaunch.configure(state="disabled")
        else:
            self.master.autoLaunch.configure(text="Launch VRCUtil")

        self.button.config(True,"Done")
        self.button.callback=((lambda _: sys.exit(0)) if self.master.autoLaunch.value else self.close)

    def close(self, _):
        if self.master.autoLaunch.value:
            subprocess.Popen([self.master.installPath/"VRCUtil.exe"], cwd=self.master.installPath)
        sys.exit(0)

app = MainWindow("VRCUtil Installer", "500x300", pathlib.Path(sys._MEIPASS)/"VRCUtil.ico", False).start()