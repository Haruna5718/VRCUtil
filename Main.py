#  Copyright 2025 Haruna5718
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.dont_write_bytecode = True

import msvcrt
from pathlib import Path
import os

APPROOT_PATH = Path(os.getenv('LOCALAPPDATA'))/'Haruna5718'/'VRCUtil'
if not getattr(sys, 'frozen', False):
	APPROOT_PATH = Path(__file__).parent.resolve()

LOCKING_PATH = APPROOT_PATH/'VRCUtil.lock'
MODULES_PATH = APPROOT_PATH/'Modules'

try:
	f=open(LOCKING_PATH, "w")
	msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
except OSError:
    exit(0)

import ModuleLoader
import winreg
import json
import webview
import threading
from dataclasses import dataclass, field, asdict, is_dataclass, replace

class VRInfoAPI:
	def __init__(self):
		self.Modules:dict[str,ModuleLoader.ModuleDataType] = {}
		with open(APPROOT_PATH/"Setting.json", "r", encoding="utf-8") as f:
			self.SettingData = json.load(f)

	def SaveSetting(self):
		with open(APPROOT_PATH/"Setting.json", "w", encoding="utf-8") as f:
			json.dump(self.SettingData, f, ensure_ascii=False, indent="\t")

	def UpdateData(self,Name,ValueName,Value):
		window.evaluate_js(f'window.SetValue("{Name}","{ValueName}",{json.dumps(Value)})')

	def destroy(self):
		window.destroy()

	def minimize(self):
		window.minimize()

	def ontop(self, State:bool):
		threading.Thread(target=lambda s: setattr(window,"on_top",s),args=(State,)).start()
		return window.on_top
	
	def LoadModule(self):
		ModuleFolders = os.listdir("Modules")
		for ModuleFolder in ModuleFolders:
			self.Modules[ModuleFolder] = ModuleLoader.LoadModule(MODULES_PATH/ModuleFolder,window)
		return {
			"LayoutData":{k:asdict(v.Layout) for k,v in self.Modules.items()},
			"ModuleData":{
				k:{
					"DisplayName": Module.DisplayName,
					"DisplayIcon": Module.DisplayIcon,
					"Version": Module.Version,
					"Author": Module.Author,
					"Description": Module.Description,
					"Url": Module.Url
				}
				for k,Module in self.Modules.items()
			}
		}
	
	def InitModule(self):
		[getattr(i.Function,"init")() for i in self.Modules.values()]
		
	def GetValue(self,ModuleName:str,ValueName:str,Value=None):
		if(ModuleName=="Settings"):
			if Value!=None:
				self.SettingData[ValueName] = Value
				self.SaveSetting()
			self.UpdateData("Settings",ValueName,self.SettingData[ValueName])
		else:
			getattr(self.Modules[ModuleName].Function,"DataHandler")(ValueName,Value)

	def SetAutoStart(self, State:bool):
		key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Valve\\Steam")
		SteamPath, _ = winreg.QueryValueEx(key, "InstallPath")
		winreg.CloseKey(key)

		if not SteamPath:
			raise Exception("Steam is not installed or the registry key is missing.")

		SteamVRPath = Path(SteamPath)/"config"
		SteamVRAppConfig = SteamVRPath/"vrappconfig"/"Haruna5718.VRCUtil.vrappconfig"
		vrmanifestPath = APPROOT_PATH/'manifest.vrmanifest'
		SteamVRConfig = SteamVRPath/"appconfig.json"

		if not os.path.exists(SteamVRPath):
			raise Exception("SteamVR is not installed or has never been run")
		
		if State:
			with open(SteamVRAppConfig, "w") as file:
				json.dump({"autolaunch":True,"last_launch_time":"0"}, file, indent=4)
		else:
			os.remove(SteamVRAppConfig)

		with open(SteamVRConfig, "r") as file:
			data = json.load(file)
			getattr(data["manifest_paths"],"remove" if (vrmanifestPath in data["manifest_paths"]) and not State else "append")(vrmanifestPath)

		with open(SteamVRConfig, "w") as file:
			json.dump(data, file, indent=4)

		return State
		
api = VRInfoAPI()
window = webview.create_window("VRCUtil", (APPROOT_PATH/"FrontEnd"/"index.html" if getattr(sys, 'frozen', False) else "http://localhost:3000/"), js_api=api, background_color="#202020", resizable=False, frameless=True, easy_drag=False, draggable=True, text_select=True, width=900, height=600)

webview.start(debug=not getattr(sys, 'frozen', False))