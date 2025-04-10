# Copyright 2025 Haruna5718
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

import os
import msvcrt
from pathlib import Path

isDebug = not getattr(sys, 'frozen', False)

APPROOT_PATH = Path(__file__).parent.resolve() if isDebug else Path(os.getenv('LOCALAPPDATA'))/'Haruna5718'/'VRCUtil'

try:
	f = open(APPROOT_PATH/'VRCUtil.lock', "w")
	msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
except OSError:
    exit(0)

MODULES_PATH = APPROOT_PATH/'Modules'

VERSION = "2.0.0"

import socket
import ModuleLoader
import json
import webview
import threading
import requests
import traceback
import subprocess
import mimetypes
import shutil
from pythonosc import dispatcher, osc_server, udp_client
from dataclasses import asdict
import gc

def CheckUpdate():
	if isDebug:
		return
	with open(APPROOT_PATH/"Setting.json", "r", encoding="utf-8") as f:
		if not json.load(f)["AutoUpdate"]:
			return
	response = requests.get("https://api.github.com/repos/Haruna5718/VRCUtil/releases/latest")
	if response.json()["tag_name"] == VERSION:
		return
	UPDATE_PATH = APPROOT_PATH/"Download"
	os.makedirs(UPDATE_PATH, exist_ok=True)
	FileName = response.json()["assets"][0]["name"]
	Fileresponse = requests.get(response.json()["assets"][0]["browser_download_url"], stream=True)
	with open(UPDATE_PATH/FileName, "wb") as f:
		for chunk in Fileresponse.iter_content(chunk_size=8192):
			f.write(chunk)
	subprocess.Popen([UPDATE_PATH/FileName])
	
class VRInfoAPI:
	def __init__(self):		
		with open(APPROOT_PATH/"Setting.json", "r", encoding="utf-8") as f:
			self.SettingData = json.load(f)
		self.Modules: dict[str, ModuleLoader.ModuleDataType] = {}
		self.OSCServer = osc_server.ThreadingOSCUDPServer((self.SettingData["OSCHost"], int(self.SettingData["OSCOut"])), dispatcher.Dispatcher(), bind_and_activate=False)
		self.OSCSender = udp_client.SimpleUDPClient(self.SettingData["OSCHost"], int(self.SettingData["OSCIn"]))

	def SaveSetting(self):
		with open(APPROOT_PATH/"Setting.json", "w", encoding="utf-8") as f:
			json.dump(self.SettingData, f, ensure_ascii=False, indent="\t")

	def UpdateData(self, Name, ValueName, Value):
		window.evaluate_js(f'window.SetValue("{Name}", "{ValueName}", {json.dumps(Value)})')

	def ontop(self, State:bool):
		threading.Thread(target=lambda s: setattr(window, "on_top", s), args=(State,), daemon=True).start()
		return window.on_top
	
	def LoadModule(self):
		ModuleFolders = os.listdir(MODULES_PATH)
		for ModuleFolder in ModuleFolders:
			if ModuleFolder.startswith("_"):
				continue
			try:
				self.Modules[ModuleFolder] = ModuleLoader.LoadModule(MODULES_PATH/ModuleFolder, window, self.OSCServer, self.OSCSender)
			except Exception as e:
				ErrorMessage = json.dumps(f"Load Failed {ModuleFolder}\n{e}")
				window.evaluate_js(f'window.Notice({ErrorMessage}, 3)')
		return {
			"LayoutData": {k: asdict(v.Layout) for k, v in self.Modules.items()},
			"WidgetData": {k: asdict(v.Widget) for k, v in self.Modules.items() if v.Widget},
			"ModuleData": {
				k: {
					"DisplayName": Module.DisplayName,
					"DisplayIcon": Module.DisplayIcon,
					"Version": Module.Version,
					"Author": Module.Author,
					"Description": Module.Description,
					"Url": Module.Url
				}
				for k, Module in self.Modules.items()
			}
		}
	
	def _ExecModule(self, name:str, funcName:str, *args):
		def Function():
			try:
				getattr(self.Modules[name].Function, funcName)(*args)
			except Exception as e:
				ErrorMessage = json.dumps(f"Error raised in {name}\n{e}")
				window.evaluate_js(f'window.Notice({ErrorMessage},3)')
				print(f"{''.join(traceback.format_tb(e.__traceback__))}\n{type(e).__name__}: {e}")
		threading.Thread(target=Function, daemon=True).start()

	def _ExecTryModule(self, name:str, funcName:str, *args):
		def Function():
			try:
				getattr(self.Modules[name].Function, funcName)(*args)
			except:
				pass
		threading.Thread(target=Function, daemon=True).start()

	def InitModule(self):
		self.InitOSCServer()
		for name in self.Modules.keys():
			self._ExecModule(name, "init")

	def InitOSCServer(self):
		try:
			if getattr(self.OSCServer,"isactive",False):
				self.OSCServer.shutdown()
				self.OSCServer.server_close()
			self.OSCServer.server_address = (self.SettingData["OSCHost"], int(self.SettingData["OSCOut"]))
			self.OSCServer.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.OSCServer.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.OSCServer.server_bind()
			threading.Thread(target=self.OSCServer.serve_forever, daemon=True).start()
			self.OSCServer.isactive = True
		except Exception as e:
			self.OSCServer.isactive = False
			window.evaluate_js(f'window.Notice("{e}",3)')
		
	def GetValue(self, ModuleName:str, ValueName:str, Value=None):
		if ModuleName == "Settings":
			if ValueName == "version":
				return self.UpdateData("Settings", ValueName, VERSION)
			if ValueName == "newversion":
				return self.UpdateData("Settings", ValueName, VERSION if isDebug else requests.get("https://api.github.com/repos/Haruna5718/VRCUtil/releases/latest").json()["tag_name"])
			if Value != None:
				self.SettingData[ValueName] = Value
				self.SaveSetting()
				if isPortChanged:=(ValueName in ["OSCIn", "OSCOut"]):
					BeforePort = (self.OSCSender._port, self.OSCServer.server_address[1])
				if ValueName in ["OSCHost", "OSCOut"]:
					self.InitOSCServer()
				if ValueName in ["OSCHost", "OSCIn"]:
					self.OSCSender._address = self.SettingData["OSCHost"]
					self.OSCSender._port = int(self.SettingData["OSCIn"])
				if isPortChanged:
					for name in self.Modules.keys():
						self._ExecTryModule(name, "onPortChange", BeforePort, (self.OSCSender._port, self.OSCServer.server_address[1]))
			return self.UpdateData("Settings", ValueName, self.SettingData[ValueName])
		elif ValueName=="VRCUtil_Remove_This_Module":
			if isDebug:
				return
			del self.Modules[ModuleName]
			gc.collect()
			def deleteFile(*_):
				shutil.rmtree(MODULES_PATH/ModuleName, onerror=deleteFile)
			threading.Thread(target=deleteFile, daemon=True).start()
		else:
			Paths = ValueName.split(".")
			if Data := getattr(self.Modules[ModuleName].Function, "Data", None):
				for key in Paths[:-1]:
					if isinstance(Data, list):
						if not key.isdigit():
							break
						key = int(key)
						if len(Data) <= key:
							break
					elif not isinstance(Data, dict) or key not in Data:
						break
					Data = Data[key]
				else:
					if (isinstance(Data, dict) and (lastKey := Paths[-1]) in Data) or (isinstance(Data, list) and len(Data) > (lastKey := int(Paths[-1]))):
						if Value is not None:
							Data[lastKey] = Value
			if getattr(self.Modules[ModuleName].Function, Paths[0], None):
				self._ExecModule(ModuleName, Paths[0], Value, *Paths[1:])
			if getattr(self.Modules[ModuleName].Function, "SaveData", None):
				self._ExecModule(ModuleName, "SaveData")
			try:
				self.UpdateData(ModuleName, ValueName, Data[lastKey])
			except:
				pass

	def SetAutoStart(self, State: bool):
		if not os.path.exists(OpenVRPaths:=Path(os.getenv('LOCALAPPDATA'))/"openvr"/"openvrpaths.vrpath"):
			raise Exception("SteamVR is not installed")
		
		with open(OpenVRPaths, "r") as file:
			SteamVRPath = [i for i in json.load(file)["config"]if "Steam" in i][0]

		vrmanifestPath = APPROOT_PATH/'manifest.vrmanifest'
		SteamVRConfig = SteamVRPath/"appconfig.json"

		with open(SteamVRPath/"vrappconfig"/"Haruna5718.VRCUtil.vrappconfig", "w") as file:
			json.dump({"autolaunch": State, "last_launch_time": "0"}, file, indent=4)

		with open(SteamVRConfig, "r") as file:
			data = json.load(file)
			if vrmanifestPath not in data["manifest_paths"]:
				data["manifest_paths"].append(vrmanifestPath)
				with open(SteamVRConfig, "w") as file2:
					json.dump(data, file2, indent=4)

		return State

api = VRInfoAPI()
window = webview.create_window("VRCUtil", ("http://localhost:3000/" if isDebug else APPROOT_PATH/"FrontEnd"/"index.html"), js_api=api, background_color="#202020", resizable=False, frameless=True, easy_drag=False, draggable=True, text_select=isDebug, width=900, height=600)

mimetypes.add_type("application/javascript", ".js") # for MIME Error Fix

window.events.closed += CheckUpdate
api.destroy = window.destroy
api.minimize = window.minimize

webview.start(debug=isDebug)