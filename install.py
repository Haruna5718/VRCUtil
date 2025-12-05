import sys

if "debug" in sys.argv:
	import ctypes
	ctypes.windll.kernel32.AllocConsole()
	sys.stdout = open("CONOUT$", "w")
	sys.stderr = open("CONOUT$", "w")
	sys.stdin  = open("CONIN$", "r")

import os
import shutil
import pathlib
import datetime
import threading
import subprocess
import webbrowser
import customtkinter
from PIL import Image

from pywebwinui3.type import Status

from vrcutil import registry, __version__, IS_DEBUG, tkinter

rootPath = pathlib.Path("./" if IS_DEBUG else sys._MEIPASS)

def createShortcut(target:str|pathlib.Path,outPath:str|pathlib.Path):
    target = pathlib.Path(target).resolve()
    subprocess.run((
        f'powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut(\\"{pathlib.Path(outPath).resolve()}\\");'
        f'$s.TargetPath=\\"{target}\\";'
        f'$s.WorkingDirectory=\\"{target.parent}\\";'
        f'$s.IconLocation=\\"{target}\\";'
        '$s.Save()"'
    ), shell=True, check=True)

class MainWindow(tkinter.App):
    def __init__(self, title:str, size:list[int], icon:str, resize:bool=True):
        super().__init__(title, size, icon, resize)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.installPath = pathlib.Path(os.environ["LOCALAPPDATA"])/"Programs/VRCUtil"

        self.page = WelcomPage(self, self.acm)
        self.page.grid(row=0, sticky="snew")

        self.autoLaunch = tkinter.CheckBox(self, self.acm, text="Launch VRCUtil after installed")
        self.autoLaunch.grid(row=1, padx=20, pady=20, sticky="w")


        tkinter.Button(self, self.acm, text="Install", color=Status.Attention, callback=self.install).grid(row=1, padx=20, pady=20, sticky="e")

    def install(self, target:tkinter.Button):
        self.installPath = pathlib.Path(self.page.installPath.read())
        self.page.destroy()
        target.config(False,"Installing")
        self.page = InstallPage(self, self.acm, target)
        self.page.grid(row=0, sticky="snew")

class WelcomPage(tkinter.Page):
    def __init__(self, master:MainWindow, acm):
        super().__init__(master, acm)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        customtkinter.CTkLabel(self, image=customtkinter.CTkImage(light_image=Image.open(rootPath/"VRCUtil.ico"),size=(84, 84)), text="").grid(row=0, padx=20, pady=20, sticky="ne", rowspan=3)

        customtkinter.CTkLabel(self, text="VRCUtil", font=customtkinter.CTkFont(size=24, weight="bold")).grid(row=0, padx=20, pady=(20,0), sticky="nw")
        customtkinter.CTkLabel(self, text=f"Version: {__version__}").grid(row=1, padx=23, pady=(0, 28), sticky="nw")
        
        self.frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.frame.grid(row=2, padx=20, sticky="nw")
        
        tkinter.Button(self.frame, self.acm, text="Booth", width=0, callback=lambda _: webbrowser.open("https://haruna5718.booth.pm/items/6516021"), color=Status.Attention).pack(padx=(5, 0), side="left")
        tkinter.Button(self.frame, self.acm, text="Github", width=0, callback=lambda _: webbrowser.open("https://github.com/Haruna5718/VRCUtil"), color=Status.Attention).pack(padx=(5, 0), side="left")

        customtkinter.CTkLabel(self, text="Install path", height=18, font=customtkinter.CTkFont(size=12)).grid(row=4, padx=23, sticky="nw")
        self.installPath = tkinter.Textbox(self, font=customtkinter.CTkFont(size=14), height=28)
        self.installPath.grid(row=5, padx=20, pady=(0, 20), sticky="ew")
        self.installPath.write(self.master.installPath)

class InstallPage(tkinter.Page):
    def __init__(self, master:MainWindow, acm, button:tkinter.Button):
        super().__init__(master, acm)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.button = button

        self.message = customtkinter.CTkLabel(self, text=f'Installing VRCUtil {__version__}', height=16)
        self.message.grid(row=0, padx=10, pady=(10, 5), sticky="nw")

        self.progress = tkinter.ProgressBar(self, self.acm)
        self.progress.grid(row=1, padx=10, sticky="ew")

        self.installLog = tkinter.Textbox(self, readonly=True)
        self.installLog.grid(row=2, padx=10, pady=10, sticky="nsew")

        threading.Thread(target=self.install,daemon=True).start()

    def install(self):
        try:
            self.installLog.write(f"Install path: {self.master.installPath}")
            sourcePath = rootPath/"data"
            totalProgress = sum([len(files) for _, _, files in os.walk(sourcePath)])+6
            currentProgress = 0

            for filePath, _, fileNames in os.walk(sourcePath):
                filePath = pathlib.Path(filePath)
                realPath = filePath.relative_to(sourcePath)
                targetPath = self.master.installPath/realPath
                targetPath.mkdir(parents=True,exist_ok=True)
                for filename in fileNames:
                    self.installLog.write(f"\nExtract: {realPath/filename}")
                    shutil.copy(filePath/filename, targetPath/filename)
                    currentProgress += 1
                    self.progress.set(currentProgress/totalProgress)

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
            self.progress.set(currentProgress/totalProgress)
            self.installLog.write("\nRegistry configured: Software\\Microsoft\\\Windows\\CurrentVersion\\Uninstall\\VRCUtil")

            registry.ExtConnector.connect(
                id = "VRCUtilModuleFile",
                ext = "vrcutilmodule",
                target = self.master.installPath/"ModuleInstaller.exe",
                description = "VRCUtil Module File",
                icon = self.master.installPath/"ModuleInstaller.exe"
            )
            currentProgress += 1
            self.progress.set(currentProgress/totalProgress)
            self.installLog.write(f"\next connected: .vrcutilmodule > {self.master.installPath/'ModuleInstaller.exe'}")

            registry.Program.setAutostart(
                name = "VRCUtil Service Worker",
                path = self.master.installPath/"ServiceWorker.exe"
            )
            currentProgress += 1
            self.progress.set(currentProgress/totalProgress)
            self.installLog.write(f"\nStartup program registed: {self.master.installPath/'ServiceWorker.exe'}")

            subprocess.Popen([self.master.installPath/"ServiceWorker.exe"], cwd=self.master.installPath)
            currentProgress += 1
            self.progress.set(currentProgress/totalProgress)
            self.installLog.write(f"\nServiceWorker launched")

            createShortcut(self.master.installPath/"VRCUtil.exe",pathlib.Path(os.environ["APPDATA"])/"Microsoft/Windows/Start Menu/Programs/VRCUtil.lnk")
            currentProgress += 1
            self.progress.set(currentProgress/totalProgress)
            self.installLog.write(f"\nStart menu shortcut created: VRCUtil.lnk")

            createShortcut(self.master.installPath/"VRCUtil.exe",pathlib.Path(os.environ["USERPROFILE"])/"Desktop/VRCUtil.lnk")
            currentProgress += 1
            self.progress.set(currentProgress/totalProgress)
            self.installLog.write(f"\nDesktop shortcut created: VRCUtil.lnk")

            self.message.configure(text=f'Installed VRCUtil {__version__}')
            
            if self.master.autoLaunch.value:
                subprocess.Popen([self.master.installPath/"VRCUtil.exe"], cwd=self.master.installPath)
                self.master.autoLaunch.configure(state="disabled")
            else:
                self.master.autoLaunch.configure(text="Launch VRCUtil")

            self.progress.config(Status.Success)
            self.button.config(True,"Done")
            self.button.callback=((lambda _: sys.exit(0)) if self.master.autoLaunch.value else self.close)
        except Exception as e:
            self.installLog.write(f"\n\nAn error occurred during initialization\n\n{e}")
            self.master.autoLaunch.configure(state="disabled")
            self.progress.config(Status.Critical)
            self.button.config(True,"Close")
            self.button.callback=lambda _: sys.exit(1)

    def close(self, _):
        if self.master.autoLaunch.value:
            subprocess.Popen([self.master.installPath/"VRCUtil.exe"], cwd=self.master.installPath)
        sys.exit(0)

app = MainWindow("VRCUtil Installer", [500, 300], rootPath/"VRCUtil.ico", False)

if not IS_DEBUG:
    import pyi_splash
    pyi_splash.close()

app.start()