import sys

import argparse

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--debug", action="store_true")
parser.add_argument("--direct", action="store_true")
parser.add_argument("--path", dest="install_path")
args, _ = parser.parse_known_args()

if args.debug:
	import ctypes
	ctypes.windll.kernel32.AllocConsole()
	sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
	sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
	sys.stdin  = open("CONIN$", "r", encoding="utf-8", errors="replace")

import os
import time
import shutil
import tempfile
import datetime
import threading
import subprocess
import webbrowser
import tarfile
import zstandard as zstd
from pathlib import Path
import customtkinter
from PIL import Image

from pywebwinui3.type import Status

from vrcutil import registry, steam, __version__, IS_COMPILED, tkinter
from vrcutil.process import closeProcessImage

rootPath = Path(__file__).resolve().parent

def closeRunningVRCUtil() -> tuple[bool, bool]:
    return closeProcessImage("VRCUtil.exe")

def launchVRCUtil(installPath:Path):
    subprocess.Popen(
        [installPath/"VRCUtil.exe"],
        cwd=installPath,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def schedule_cleanup(path: str | Path | None = None):
    target = Path(path).resolve() if path else rootPath
    if not target.is_absolute():
        return

    subprocess.Popen(
        [
            "cmd",
            "/c",
            f'timeout /T 5 >nul & if exist "{target}" rmdir /S /Q "{target}"',
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

class MainWindow(tkinter.App):
    def __init__(
        self,
        title:str,
        size:list[int],
        icon: str|Path,
        resize:bool=True,
        *,
        install_path: str | None = None,
        auto_install: bool = False,
        direct_mode: bool = False,
    ):
        super().__init__(title, size, icon, resize)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.directMode = bool(direct_mode)
        self.autoInstall = bool(auto_install or direct_mode)
        self.installPath = Path(install_path).expanduser() if install_path else Path(os.environ["LOCALAPPDATA"])/"VRCUtil"

        self.page = WelcomPage(self, self.acm, icon)
        self.page.grid(row=0, sticky="snew")

        self.autoLaunch = tkinter.CheckBox(self, self.acm, text="Launch VRCUtil after installed")
        self.autoLaunch.variable.set(1 if self.directMode else 0)
        if not self.directMode:
            self.autoLaunch.grid(row=1, padx=20, pady=20, sticky="w")

        self.installButton = tkinter.Button(self, self.acm, text="Install", color=Status.Attention, callback=self.install)
        self.installButton.grid(row=1, padx=20, pady=20, sticky="e")

        if self.autoInstall:
            self.after(0, lambda: self.install(self.installButton))

    def install(self, target:tkinter.Button):
        self.installPath = Path(self.page.installPath.read())
        self.page.destroy()
        target.config(False,"Installing")
        self.setClosable(False)
        self.page = InstallPage(self, self.acm, target)
        self.page.grid(row=0, sticky="snew")

    def exit(self, code: int = 0):
        if self.directMode:
            schedule_cleanup()
        sys.exit(code)

    def destroy(self):
        if self.directMode:
            schedule_cleanup()
        super().destroy()

class WelcomPage(tkinter.Page):
    def __init__(self, master:MainWindow, acm, icon: str|Path):
        super().__init__(master, acm)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        customtkinter.CTkLabel(self, image=customtkinter.CTkImage(light_image=Image.open(icon), size=(84, 84)), text="").grid(row=0, padx=20, pady=20, sticky="ne", rowspan=3)

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

    def logWithProgress(self,message:str):
        self.currentProgress += 1
        self.installLog.write(message)
        self.progress.set(self.currentProgress/self.totalProgress)


    def install(self):
        stagePath = None
        backupPath = None
        installSwapped = False
        steamvrRegistered = False
        createdFreshInstall = not self.master.installPath.exists()
        try:
            self.installLog.write(f"Install path: {self.master.installPath}")
            steamvrInstalled = (IS_COMPILED and steam.hasSteamVR())
            
            closed, forced = closeRunningVRCUtil()
            if closed:
                self.installLog.write("\nClosed running VRCUtil" + (" (forced)" if forced else ""))

            self.sourceArchive = rootPath / "VRCUtil.tar.zst"

            with self.sourceArchive.open("rb") as f:
                dctx = zstd.ZstdDecompressor()
                with dctx.stream_reader(f) as reader:
                    with tarfile.open(fileobj=reader, mode="r|") as tar:
                        archiveInfos = [m for m in tar if m.isfile()]

            self.totalProgress = len(archiveInfos) + 6 + int(steamvrInstalled)
            self.currentProgress = 0

            stagePath = Path(tempfile.mkdtemp(prefix="VRCUtil-Install-"))/"VRCUtil"
            stagePath.mkdir(parents=True, exist_ok=True)

            with self.sourceArchive.open("rb") as f:
                dctx = zstd.ZstdDecompressor()
                with dctx.stream_reader(f) as reader:
                    with tarfile.open(fileobj=reader, mode="r|") as tar:
                        logs = []
                        last_update = -1

                        for member in tar:
                            if not member.isfile():
                                continue

                            logs.append(f"Extract: {member.name}")
                            self.currentProgress += 1

                            if (now:=time.monotonic()) - last_update >= 0.1:
                                if logs:
                                    self.progress.set(self.currentProgress / self.totalProgress)
                                    self.installLog.write("\n" + "\n".join(logs))
                                    logs.clear()
                                last_update = now
                            if IS_COMPILED:
                                tar.extract(member, stagePath)

                        if logs:
                            self.progress.set(self.currentProgress / self.totalProgress)
                            self.installLog.write("\n" + "\n".join(logs))

            if IS_COMPILED:
                if self.master.installPath.exists():
                    backupPath = Path(tempfile.mkdtemp(prefix="VRCUtil-Backup-"))/"VRCUtil"
                    shutil.move(str(self.master.installPath), str(backupPath))
                shutil.move(str(stagePath), str(self.master.installPath))
                installSwapped = True

            self.logWithProgress("\nExtract complete")

            if IS_COMPILED:
                registry.ExtConnector.connect(
                    id = "VRCUtilModuleFile",
                    ext = "vrcutilmodule",
                    target = self.master.installPath/"ModuleInstaller.exe",
                    description = "VRCUtil Module File",
                    icon = self.master.installPath/"ModuleInstaller.exe"
                )
            self.logWithProgress(f"\next connected: .vrcutilmodule > {self.master.installPath/'ModuleInstaller.exe'}")

            if IS_COMPILED:
                registry.createShortcut(
                    Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/VRCUtil.lnk",
                    self.master.installPath / "VRCUtil.exe",
                )
            self.logWithProgress(f"\nStart menu shortcut created: VRCUtil.lnk")

            if IS_COMPILED:
                registry.createShortcut(
                    Path(os.environ["USERPROFILE"]) / "Desktop/VRCUtil.lnk",
                    self.master.installPath / "VRCUtil.exe",
                )
            self.logWithProgress(f"\nDesktop shortcut created: VRCUtil.lnk")

            if steamvrInstalled:
                vr = steam.VR(self.master.installPath/"manifest.vrmanifest")
                if not vr.installed or not vr.config.exists():
                    vr.install()
                    steamvrRegistered = True
                    self.logWithProgress(f"\nSteamVR app registered")
                else:
                    self.logWithProgress(f"\nSteamVR app already registered")

            if IS_COMPILED:
                registry.Program.unsetAutostart("VRCUtil")
                registry.Program.unsetAutostartState("VRCUtil")
                registry.Program.setStartupShortcut(
                    "VRCUtil",
                    self.master.installPath/"VRCUtil.exe",
                    "--minimize",
                    icon=self.master.installPath/"VRCUtil.exe",
                )
                if registry.Program.startupShortcutState("VRCUtil") is None:
                    registry.Program.setStartupShortcutState("VRCUtil", False)
            self.logWithProgress(f"\nStartup shortcut prepared: VRCUtil.lnk")

            if IS_COMPILED:
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
            self.logWithProgress("\nRegistry configured: Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\VRCUtil")

            self.message.configure(text=f'Installed VRCUtil {__version__}')
            
            if self.master.autoLaunch.value and IS_COMPILED:
                launchVRCUtil(self.master.installPath)
                if not self.master.directMode:
                    self.master.autoLaunch.configure(state="disabled")
            else:
                if not self.master.directMode:
                    self.master.autoLaunch.configure(text="Launch VRCUtil")

            self.progress.config(Status.Success)
            if self.master.directMode:
                self.master.exit(0)
                return
            self.button.config(True,"Done")
            self.master.setClosable(True)
            self.button.callback=((lambda _: self.master.exit(0)) if self.master.autoLaunch.value else self.close)
        except Exception as e:
            self.installLog.write("\n\nInstallation failed. Rolling back...")
            try:
                if IS_COMPILED and steamvrRegistered and self.master.installPath.exists():
                    steam.VR(self.master.installPath/"manifest.vrmanifest").uninstall()
                    self.installLog.write("\nSteamVR registration rollback complete")
            except Exception as rollback_error:
                self.installLog.write(f"\nSteamVR rollback failed: {rollback_error}")

            try:
                if IS_COMPILED and installSwapped and self.master.installPath.exists():
                    shutil.rmtree(self.master.installPath, ignore_errors=True)
                if IS_COMPILED and backupPath and backupPath.exists():
                    shutil.move(str(backupPath), str(self.master.installPath))
                    self.installLog.write("\nApplication files restored")
                elif IS_COMPILED and createdFreshInstall:
                    shutil.rmtree(self.master.installPath, ignore_errors=True)
            except Exception as rollback_error:
                self.installLog.write(f"\nFile rollback failed: {rollback_error}")

            if createdFreshInstall:
                try:
                    registry.Program.uninstall("VRCUtil")
                    registry.ExtConnector.disconnect("vrcutilmodule", "VRCUtilModuleFile")
                    registry.Program.unsetAutostart("VRCUtil")
                    registry.Program.unsetAutostartState("VRCUtil")
                    registry.Program.unsetStartupShortcut("VRCUtil")
                    registry.Program.unsetStartupShortcutState("VRCUtil")
                    (Path(os.environ["APPDATA"])/"Microsoft/Windows/Start Menu/Programs/VRCUtil.lnk").unlink(missing_ok=True)
                    (Path(os.environ["USERPROFILE"])/"Desktop/VRCUtil.lnk").unlink(missing_ok=True)
                    self.installLog.write("\nInstaller side effects rolled back")
                except Exception as rollback_error:
                    self.installLog.write(f"\nRegistry/shortcut rollback failed: {rollback_error}")

            self.installLog.write(f"\n\nAn error occurred during initialization\n\n{e}")
            self.master.autoLaunch.configure(state="disabled")
            self.progress.config(Status.Critical)
            self.button.config(True,"Close")
            self.master.setClosable(True)
            self.button.callback=lambda _: self.master.exit(1)
        finally:
            if stagePath:
                shutil.rmtree(stagePath.parent, ignore_errors=True)
            if backupPath:
                shutil.rmtree(backupPath.parent, ignore_errors=True)

    def close(self, _):
        if self.master.autoLaunch.value and IS_COMPILED:
            launchVRCUtil(self.master.installPath)
        self.master.exit(0)

app = MainWindow(
    "VRCUtil Installer",
    [500, 300],
    rootPath/"VRCUtil.ico",
    False,
    install_path=args.install_path,
    auto_install=bool(args.direct),
    direct_mode=args.direct,
)
app.start()
