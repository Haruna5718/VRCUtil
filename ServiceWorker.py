import sys
import win32event
import win32service
import servicemanager
import win32serviceutil
from Extention import Steam, ProcessWatcher

EVENT_ID = 5718

# ----------------------------

class VRCUtilServiceWorker(win32serviceutil.ServiceFramework):
	_svc_name_ = "VRCUtilServiceWorker"
	_svc_display_name_ = "VRCUtil Service Worker"
	_svc_description_ = "Detects the launch of VRChat and automatically runs VRCUtil"

	def __init__(self, args):
		win32serviceutil.ServiceFramework.__init__(self, args)
		self.exitEvent = win32event.CreateEvent(None,False,False,None)
		self.processWatcher = ProcessWatcher().addTarget(Steam().findSteamAppPath("438100","UnityCrashHandler64.exe"),self._launchVRCUtil)

	def _launchVRCUtil(self, *_):
		servicemanager.LogMsg(
			servicemanager.EVENTLOG_INFORMATION_TYPE,
			EVENT_ID,
			("Try to launch VRCUtil",)
		)

	def SvcStop(self):
		servicemanager.LogInfoMsg("Service stop requested")
		self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
		win32event.SetEvent(self.exitEvent)

	def SvcDoRun(self):
		self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
		servicemanager.LogInfoMsg("VRChat Watcher Service starting")

		self.processWatcher.start(deletion=False)
		
		self.ReportServiceStatus(win32service.SERVICE_RUNNING)

		win32event.WaitForSingleObject(self.exitEvent, win32event.INFINITE)

		self.processWatcher.stop()
		
		servicemanager.LogInfoMsg("Service stopped")
		self.ReportServiceStatus(win32service.SERVICE_STOPPED)

# ----------------------------

if __name__ == '__main__':
	if len(sys.argv) == 1:
		servicemanager.Initialize()
		servicemanager.PrepareToHostSingle(VRCUtilServiceWorker)
		servicemanager.StartServiceCtrlDispatcher()

	else:
		import ctypes
		def isAdmin():
			try:
				return ctypes.windll.shell32.IsUserAnAdmin()
			except:
				return False
	
		if not isAdmin():
			ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
			sys.exit(0)

		import subprocess

		if '--install' in sys.argv:
			
			import os
			import winreg
			import tempfile
			from pathlib import Path
					
			try:
				win32serviceutil.InstallService(
					pythonClassString=f"{__name__}.{VRCUtilServiceWorker.__name__}",
					serviceName=VRCUtilServiceWorker._svc_name_,
					displayName=VRCUtilServiceWorker._svc_display_name_,
					description=VRCUtilServiceWorker._svc_description_,
					startType=win32service.SERVICE_AUTO_START
				)
				print("Service installed successfully.")

				with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\VRCUtil") as key:
					VRCUtilPath = str(Path(winreg.QueryValueEx(key, "InstallLocation")[0])/"VRCUtil.exe")

				with tempfile.NamedTemporaryFile(delete=False, suffix=".xml", mode="w", encoding="utf-16") as f:
					f.write(f'''<?xml version="1.0" encoding="UTF-16"?>
						<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
							<Triggers>
								<EventTrigger>
									<Enabled>true</Enabled>
									<Subscription>&lt;QueryList&gt;&lt;Query Path="Application"&gt;&lt;Select Path="Application"&gt;*[System[Provider[@Name='{VRCUtilServiceWorker._svc_name_}'] and EventID={EVENT_ID}]]&lt;/Select&gt;&lt;/Query&gt;&lt;/QueryList&gt;</Subscription>
								</EventTrigger>
							</Triggers>
							<Actions>
								<Exec>
									<Command>{VRCUtilPath} --vrchat</Command>
								</Exec>
							</Actions>
							<Settings>
								<MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
								<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
								<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
								<AllowHardTerminate>true</AllowHardTerminate>
								<StartWhenAvailable>true</StartWhenAvailable>
								<RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
								<Enabled>true</Enabled>
								<Hidden>false</Hidden>
								<RunOnlyIfIdle>false</RunOnlyIfIdle>
								<WakeToRun>false</WakeToRun>
							</Settings>
						</Task>
					''')
					tempXml = f.name
				
				result = subprocess.run(['schtasks', '/create', '/tn', "VRCUtilAutoStart", '/xml', tempXml, '/f'], check=True)
				os.remove(tempXml)
				print("Task created successfully.")
				
				win32serviceutil.StartService(VRCUtilServiceWorker._svc_name_)
				print("Service started successfully.")
				
			except Exception as e:
				print(f"Installation failed: {e}")

		elif '--remove' in sys.argv:
			try:
				try:
					win32serviceutil.StopService(VRCUtilServiceWorker._svc_name_)
					print("Service stopped.")
				except Exception:
					pass
					
				win32serviceutil.RemoveService(VRCUtilServiceWorker._svc_name_)
				print("Service removed successfully.")

				subprocess.run(['schtasks', '/delete', '/tn', "VRCUtilAutoStart", '/f'], check=True)
				print("Task deleted successfully.")

			except Exception as e:
				print(f"Removal failed: {e}")

		else:
			print("Use --install to install or --remove to uninstall the service.")
			print("Run without arguments to start as a service.")

# ----------------------------

# pyinstaller --onefile ServiceWorker.py