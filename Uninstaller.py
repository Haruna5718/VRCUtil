import sys

if "debug" in sys.argv:
	import ctypes
	ctypes.windll.kernel32.AllocConsole()
	sys.stdout = open("CONOUT$", "w")
	sys.stderr = open("CONOUT$", "w")
	sys.stdin = open("CONIN$", "r")

import os
import pathlib
import shutil
import subprocess
import tempfile
import threading

import customtkinter
from PIL import Image

from pywebwinui3.type import Status

from vrcutil import DATA_PATH, INSTALL_PATH, IS_DEBUG, __version__, registry, steam, tkinter

UNINSTALL_ARG = "-uninstall"
CURRENT_EXECUTABLE = pathlib.Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve()
TARGET_APP_ROOT = pathlib.Path(sys.argv[sys.argv.index(UNINSTALL_ARG) + 1]).resolve() if UNINSTALL_ARG in sys.argv and len(sys.argv) > sys.argv.index(UNINSTALL_ARG) + 1 else (pathlib.Path(__file__).resolve().parent if IS_DEBUG else INSTALL_PATH)


def process_exists(image_name: str) -> bool:
	flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
	result = subprocess.run(
		["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/FO", "CSV", "/NH"],
		capture_output=True,
		text=True,
		creationflags=flags,
	)
	if result.returncode != 0:
		return False
	return image_name.casefold() in result.stdout.casefold()

def remove_steamvr_registration():
	manifest = TARGET_APP_ROOT / "manifest.vrmanifest"
	if not manifest.exists():
		return False

	try:
		steam.VR(manifest).uninstall()
		return True
	except Exception:
		return False

def remove_target_files(remove_data: bool = False) -> list[str]:
	logs: list[str] = []
	if TARGET_APP_ROOT.exists():
		if not IS_DEBUG:
			shutil.rmtree(TARGET_APP_ROOT)
		logs.append("Application files removed")
	if remove_data and DATA_PATH.exists():
		if not IS_DEBUG:
			shutil.rmtree(DATA_PATH)
		logs.append("User data removed")
	return logs


class MainWindow(tkinter.App):
	def __init__(self, title: str, size: list[int], icon: str|pathlib.Path, resize: bool = True):
		super().__init__(title, size, icon, resize)

		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(0, weight=1)

		self.installPath = TARGET_APP_ROOT
		self.removeData = tkinter.CheckBox(self, self.acm, text="Remove VRCUtil data")
		self.removeData.grid(row=1, padx=20, pady=20, sticky="w")
		self.removeDataValue = False

		self.page = WelcomePage(self, self.acm, icon)
		self.page.grid(row=0, sticky="snew")

		tkinter.Button(self, self.acm, text="Uninstall", color=Status.Critical, callback=self.uninstall).grid(row=1, padx=20, pady=20, sticky="e")

	def uninstall(self, target: tkinter.Button):
		self.removeDataValue = bool(self.removeData.value)
		self.removeData.destroy()
		self.page.destroy()
		target.config(False, "Uninstalling", Status.Attention)
		self.page = UninstallPage(self, self.acm, target)
		self.page.grid(row=0, sticky="snew")


class WelcomePage(tkinter.Page):
	def __init__(self, master: MainWindow, acm, icon: str|pathlib.Path):
		super().__init__(master, acm)

		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(3, weight=1)

		customtkinter.CTkLabel(
			self,
			image=customtkinter.CTkImage(light_image=Image.open(icon), size=(84, 84)),
			text="",
		).grid(row=0, padx=20, pady=20, sticky="ne", rowspan=3)

		customtkinter.CTkLabel(self, text="VRCUtil", font=customtkinter.CTkFont(size=24, weight="bold")).grid(row=0, padx=20, pady=(20, 0), sticky="nw")
		customtkinter.CTkLabel(self, text=f"Version: {__version__}").grid(row=1, padx=23, pady=(0, 28), sticky="nw")


class UninstallPage(tkinter.Page):
	def __init__(self, master: MainWindow, acm, button: tkinter.Button):
		super().__init__(master, acm)

		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(2, weight=1)

		self.button = button
		self.message = customtkinter.CTkLabel(self, text=f"Uninstalling VRCUtil {__version__}", height=16)
		self.message.grid(row=0, padx=10, pady=(10, 5), sticky="nw")

		self.progress = tkinter.ProgressBar(self, self.acm)
		self.progress.grid(row=1, padx=10, sticky="ew")

		self.uninstallLog = tkinter.Textbox(self, readonly=True)
		self.uninstallLog.grid(row=2, padx=10, pady=10, sticky="nsew")

		threading.Thread(target=self.uninstall, daemon=True).start()

	def uninstall(self):
		try:
			total_progress = 8 if self.master.removeDataValue else 7
			current_progress = 0

			self.uninstallLog.write("Starting uninstallation")

			for image_name in ("VRCUtil.exe", "ModuleInstaller.exe"):
				if process_exists(image_name):
					for command in (
						["taskkill", "/IM", image_name, "/T"],
						["taskkill", "/IM", image_name, "/T", "/F"],
					):
						result = subprocess.run(command, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
						if result.returncode == 0:
							self.uninstallLog.write(f"\nClosed process: {image_name}")
							break
					else:
						if process_exists(image_name):
							raise RuntimeError(f"Failed to close {image_name}")
			
			current_progress += 1
			self.progress.set(current_progress / total_progress)

			if TARGET_APP_ROOT.exists() and not IS_DEBUG:
				shutil.rmtree(TARGET_APP_ROOT)
			self.uninstallLog.write(f"\nRemoved: Application files")
			current_progress += 1
			self.progress.set(current_progress / total_progress)

			if self.master.removeDataValue:
				if DATA_PATH.exists() and not IS_DEBUG:
					shutil.rmtree(DATA_PATH)
				self.uninstallLog.write(f"\nRemoved: User data")
				current_progress += 1
				self.progress.set(current_progress / total_progress)

			manifest = TARGET_APP_ROOT / "manifest.vrmanifest"
			if manifest.exists():
				try:
					steam.VR(manifest).uninstall()
					self.uninstallLog.write("\nSteamVR manifest removed")
				except Exception:
					pass
			current_progress += 1
			self.progress.set(current_progress / total_progress)

			registry.Program.unsetAutostart("VRCUtil")
			self.uninstallLog.write("\nStartup entry removed")
			current_progress += 1
			self.progress.set(current_progress / total_progress)

			registry.ExtConnector.disconnect("vrcutilmodule", "VRCUtilModuleFile")
			self.uninstallLog.write("\next Disconnected")
			current_progress += 1
			self.progress.set(current_progress / total_progress)

			registry.Program.uninstall("VRCUtil")
			self.uninstallLog.write("\nRegistry entries removed")
			current_progress += 1
			self.progress.set(current_progress / total_progress)

			(pathlib.Path(os.environ["APPDATA"])/"Microsoft/Windows/Start Menu/Programs/VRCUtil.lnk").unlink(missing_ok=True)
			self.uninstallLog.write(f"\nStart menu shortcut removed")
			(pathlib.Path(os.environ["USERPROFILE"])/"Desktop/VRCUtil.lnk").unlink(missing_ok=True)
			self.uninstallLog.write(f"\nDesktop shortcut removed")
			current_progress += 1
			self.progress.set(current_progress / total_progress)

			self.message.configure(text=f"Uninstalled VRCUtil {__version__}")
			self.progress.config(Status.Success)
			self.button.config(True, "Done")
			self.button.callback = self.close
		except Exception as e:
			self.uninstallLog.write(f"\n\nAn error occurred during uninstallation\n\n{e}")
			self.progress.config(Status.Critical)
			self.button.config(True, "Close")
			self.button.callback = lambda _: sys.exit(1)

	def close(self, _):
		if not IS_DEBUG:
			subprocess.Popen(["cmd", "/c", f"timeout /T 5 >nul & rmdir /S /Q {CURRENT_EXECUTABLE.parent}"], creationflags=subprocess.CREATE_NO_WINDOW)
		sys.exit(0)


if not UNINSTALL_ARG in sys.argv and getattr(sys, "frozen", False):
	tempUninstaller = pathlib.Path(tempfile.mkdtemp()) / CURRENT_EXECUTABLE.name
	shutil.copy2(CURRENT_EXECUTABLE, tempUninstaller)
	subprocess.Popen([str(tempUninstaller), UNINSTALL_ARG, str(TARGET_APP_ROOT)], creationflags=subprocess.CREATE_NO_WINDOW)
	sys.exit(0)

app = MainWindow("VRCUtil Uninstaller", [500, 300], pathlib.Path("./" if IS_DEBUG else sys._MEIPASS)/"VRCUtil.ico", False)
app.start()
