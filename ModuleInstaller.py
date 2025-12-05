import sys

if len(sys.argv) < 2:
    sys.exit(1)

if "debug" in sys.argv:
	import ctypes
	ctypes.windll.kernel32.AllocConsole()
	sys.stdout = open("CONOUT$", "w")
	sys.stderr = open("CONOUT$", "w")
	sys.stdin  = open("CONIN$", "r")

import json
import pathlib
import zipfile
import threading
import webbrowser
import subprocess
import customtkinter

from pywebwinui3.type import Status

from vrcutil import tkinter, MODULES_PATH, INSTALL_PATH

modulePath = pathlib.Path(sys.argv[1])

class MainWindow(tkinter.App):
    def __init__(self, title:str, size:str, icon:str, resize:bool=True):
        super().__init__(title, size, icon, resize)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.page = Infopage(self, self.acm)
        self.page.grid(row=0, padx=10, pady=(10, 0), sticky="sew")

        tkinter.Button(self, self.acm, text="Install Module", color=Status.Attention, callback=self.install).grid(row=1, padx=10, pady=10, sticky="ews")

    def install(self, target:tkinter.Button):
        self.page.destroy()
        target.config(False,"Installing")
        self.page = InstallPage(self, self.acm, target)
        self.page.grid(row=0, padx=10, pady=(10, 0), sticky="sew")

class Infopage(tkinter.Page):
    def __init__(self, master:MainWindow, acm):
        super().__init__(master, acm, round=None)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        customtkinter.CTkLabel(self, text=installData["name"], font=customtkinter.CTkFont(size=24, weight="bold")).grid(row=0, padx=10, pady=(10, 0), sticky="nw")
        customtkinter.CTkLabel(self, text=installData["version"], font=customtkinter.CTkFont(size=12)).grid(row=0, padx=15, pady=(7, 0), sticky="ne")
        customtkinter.CTkLabel(self, text=installData["author"], height=24).grid(row=1, padx=13, pady=(4, 0), sticky="sw")
        
        self.frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.frame.grid(row=1, padx=10, sticky="se")
        
        for data in installData["urls"]:
            name, url = list(data.items())[0]
            tkinter.Button(self.frame, self.acm, text=name, width=0, callback=lambda: webbrowser.open(url), color=Status.Attention).pack(padx=(5, 0), side="right")

        self.description = tkinter.Textbox(self, font=customtkinter.CTkFont(size=14), readonly=True)
        self.description.grid(row=2, padx=10, pady=10, sticky="nsew")
        self.description.write(installData["description"])

class InstallPage(tkinter.Page):
    def __init__(self, master:MainWindow, acm, button:tkinter.Button):
        super().__init__(master, acm, round=None)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.button = button

        self.message = customtkinter.CTkLabel(self, text=f'Installing {installData["name"]} {installData["version"]}', height=16)
        self.message.grid(row=0, padx=10, pady=(10, 5), sticky="nw")

        self.progress = tkinter.ProgressBar(self, self.acm)
        self.progress.grid(row=1, padx=10, sticky="ew")

        self.installLog = tkinter.Textbox(self, readonly=True)
        self.installLog.grid(row=2, padx=10, pady=10, sticky="nsew")

        threading.Thread(target=self.install,daemon=True).start()

    def install(self):
        try:
            installPath = MODULES_PATH/f'{installData["path"]}'
            self.installLog.write(f"Install path: {installPath}")
            try:
                with zip_ref.open("requirements.txt") as f:
                    requirements = [line.strip() for line in f.read().decode("utf-8").splitlines() if line.strip()]
            except:
                requirements=[]
            fileList = zip_ref.infolist()
            totalProgress = len(fileList)+len(requirements)
            currentProgress = 0

            for info in fileList:
                self.installLog.write(f"\nExtract: {info.filename}")
                if not info.is_dir():
                    zip_ref.extract(info, installPath)
                currentProgress += 1
                self.progress.set(currentProgress/totalProgress)

            for moduleName in requirements:
                self.installLog.write(f"\nPackage install: {moduleName}")
                subprocess.run([str(INSTALL_PATH/"_internal/pip.exe"), "install", "--no-cache-dir", moduleName, "--target", str(INSTALL_PATH / "_internal")],creationflags=subprocess.CREATE_NO_WINDOW)
                currentProgress += 1
                self.progress.set(currentProgress/totalProgress)

            self.progress.config(Status.Success)
            self.button.config(True,"Launch VRCUtil")
            self.button.callback=self.close
        except Exception as e:
            self.installLog.write(f"\n\nAn error occurred during module initialization\n\n{e}")
            self.progress.config(Status.Critical)
            self.button.config(True,"Close")
            self.button.callback=lambda _: sys.exit(1)

    def close(self, _):
        subprocess.Popen([INSTALL_PATH/"VRCUtil.exe"], cwd=INSTALL_PATH)
        sys.exit(0)

with zipfile.ZipFile(modulePath, 'r') as zip_ref:
    with zip_ref.open("module.json") as f:
        installData = json.load(f)

        MainWindow(title="VRCUtil Module Installer", size="400x200", icon=INSTALL_PATH/"VRCUtil.ico").start()