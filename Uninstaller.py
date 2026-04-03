import sys
import os
import pathlib
import shutil
import subprocess
import tempfile
import threading

import customtkinter
from PIL import Image

from pywebwinui3.type import Status

import vrcutil
from vrcutil import DATA_PATH, IS_COMPILED, registry, steam, tkinter
from vrcutil.process import closeProcessImage

__version__ = "2.0.0"

TARGET_APP_ROOT = pathlib.Path(sys.argv[0] if IS_COMPILED else __file__).resolve().parent

if IS_COMPILED:
	try:
		if pathlib.Path.cwd().resolve().is_relative_to(TARGET_APP_ROOT):
			os.chdir(tempfile.gettempdir())
	except Exception:
		pass

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
		if IS_COMPILED:
			shutil.rmtree(TARGET_APP_ROOT)
		logs.append("Application files removed")
	if remove_data and DATA_PATH.exists():
		if IS_COMPILED:
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
		self.setClosable(False)
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
		customtkinter.CTkLabel(self, text=f"Version: {vrcutil.__version__}").grid(row=1, padx=23, pady=(0, 28), sticky="nw")


class UninstallPage(tkinter.Page):
	def __init__(self, master: MainWindow, acm, button: tkinter.Button):
		super().__init__(master, acm)

		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(2, weight=1)

		self.button = button
		self.message = customtkinter.CTkLabel(self, text=f"Uninstalling VRCUtil {vrcutil.__version__}", height=16)
		self.message.grid(row=0, padx=10, pady=(10, 5), sticky="nw")

		self.progress = tkinter.ProgressBar(self, self.acm)
		self.progress.grid(row=1, padx=10, sticky="ew")

		self.uninstallLog = tkinter.Textbox(self, readonly=True)
		self.uninstallLog.grid(row=2, padx=10, pady=10, sticky="nsew")

		threading.Thread(target=self.uninstall, daemon=True).start()

	def uninstall(self):
		try:
			total_progress = 7 if self.master.removeDataValue else 6
			current_progress = 0

			self.uninstallLog.write("Starting uninstallation")

			target_processes = [
				"VRCUtil.exe",
				"ModuleInstaller.exe",
			]
			for image_name in target_processes:
				closed, forced = closeProcessImage(image_name)
				if closed:
					self.uninstallLog.write(f"\nClosed process: {image_name}" + (" (forced)" if forced else ""))
			
			current_progress += 1
			self.progress.set(current_progress / total_progress)

			if self.master.removeDataValue:
				if DATA_PATH.exists() and IS_COMPILED:
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
			registry.Program.unsetAutostartState("VRCUtil")
			registry.Program.unsetStartupShortcut("VRCUtil")
			registry.Program.unsetStartupShortcutState("VRCUtil")
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

			self.message.configure(text=f"Uninstalled VRCUtil {vrcutil.__version__}")
			self.progress.config(Status.Success)
			self.button.config(True, "Done")
			self.master.setClosable(True)
			self.button.callback = self.close
		except Exception as e:
			self.uninstallLog.write(f"\n\nAn error occurred during uninstallation\n\n{e}")
			self.progress.config(Status.Critical)
			self.button.config(True, "Close")
			self.master.setClosable(True)
			self.button.callback = lambda _: sys.exit(1)

	def close(self, _):
		if IS_COMPILED:
			subprocess.Popen(["cmd", "/c", f"timeout /T 5 >nul & rmdir /S /Q {pathlib.Path(__file__).resolve().parent}"], creationflags=subprocess.CREATE_NO_WINDOW)
		sys.exit(0)

if __name__ == "__main__":
	
	if "debug" in sys.argv:
		import ctypes
		ctypes.windll.kernel32.AllocConsole()
		sys.stdout = open("CONOUT$", "w")
		sys.stderr = open("CONOUT$", "w")
		sys.stdin = open("CONIN$", "r")

	app = MainWindow("VRCUtil Uninstaller", [500, 300], pathlib.Path(__file__).resolve().parent/"VRCUtil.ico", False)
	app.start()
