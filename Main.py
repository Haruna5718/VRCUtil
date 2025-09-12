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

from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import msvcrt

from Metadata import *

try:
	LockFile = open(APPROOT_PATH/'VRCUtil.lock', "w")
	msvcrt.locking(LockFile.fileno(), msvcrt.LK_NBLCK, 1)
except OSError:
	sys.exit(1)

import socket
import json
import webview
import threading
import requests
import traceback
import subprocess
import mimetypes
import shutil
import time
from pythonosc import dispatcher, osc_server, udp_client
from typing import *
from dataclasses import dataclass
import gc
import importlib.util
import xml.etree.ElementTree
import tempfile
import atexit

@dataclass
class ModuleDataType:
	DisplayName: str
	DisplayIcon: str
	Version: str
	Author: str
	Description: str
	Url: list[dict[str,str]]
	ModulePath: str
	Layout: Any
	Widget: Any
	Function: Any

def deleteFile(Path):
	time.sleep(1)
	shutil.rmtree(Path, onerror=deleteFile)

def XamlToJson(Element: xml.etree.ElementTree.Element):
	if Element.tag not in VAILD_DATAS:
		raise Exception(f"Unknown Tag: {Element.tag}")
	
	Text = Element.text.strip() if Element.text else ""
	if Text and not VAILD_DATAS[Element.tag]['Text']:
		raise Exception(f"Text Not Allowed: {Element.tag}")
	
	Childs = list(Element)
	if Childs and not VAILD_DATAS[Element.tag]["Child"]:
		raise Exception(f"Children Not Allowed: {Element.tag}")
	
	if WrongAttr:=set(Element.attrib.keys())-set(VAILD_DATAS[Element.tag]['Attr']):
		raise Exception(f"Unknown Attr in {Element.tag}: {', '.join(WrongAttr)}")
	
	return {
		"Type":Element.tag,
		"Attr":Element.attrib,
		"Text":Text,
		"Children":[XamlToJson(Child) for Child in Childs]
	}

def LoadXaml(FilePath: Path, FileName: str):
	try:
		return XamlToJson(xml.etree.ElementTree.parse(FilePath / FileName).getroot())
	except FileNotFoundError as e:
		return None

def CheckUpdate():
	response = requests.get(REPO_URL)
	if response.json()["tag_name"] == VERSION:
		return
	os.makedirs(UPDATE_PATH:=APPROOT_PATH/"Download", exist_ok=True)
	FileName = response.json()["assets"][0]["name"]
	Fileresponse = requests.get(response.json()["assets"][0]["browser_download_url"], stream=True)
	with open(UPDATE_PATH/FileName, "wb") as f:
		for chunk in Fileresponse.iter_content(chunk_size=8192):
			f.write(chunk)
	time.sleep(0.5)  # Give some time for the file to be written completely
	subprocess.Popen([UPDATE_PATH/FileName])

def PostExit():
	msvcrt.locking(LockFile.fileno(), msvcrt.LK_UNLCK, 1)
	with open(APPROOT_PATH/"Setting.json", "r", encoding="utf-8") as f:
		if json.load(f)["AutoUpdate"]:
			CheckUpdate()
	sys.exit()

def UpdateData(Name, ValueName, Value):
	window.evaluate_js(f'window.SetValue("{Name}", "{ValueName}", {json.dumps(Value)})')

def SaveSetting():
	with open(APPROOT_PATH/"Setting.json", "w", encoding="utf-8") as f:
		json.dump(SettingData, f, ensure_ascii=False, indent="\t")

def ExecModule(name:str, funcName:str, *args):
	def Function():
		try:
			getattr(Modules[name].Function, funcName)(*args)
		except Exception as e:
			ErrorMessage = json.dumps(f"Error raised in {name}\n{e}")
			window.evaluate_js(f'window.Notice({ErrorMessage},3)')
			print(f"{''.join(traceback.format_tb(e.__traceback__))}\n{type(e).__name__}: {e}")
	threading.Thread(target=Function, daemon=True).start()

def ExecTryModule(name:str, funcName:str, *args):
	def Function():
		try:
			getattr(Modules[name].Function, funcName)(*args)
		except:
			pass
	threading.Thread(target=Function, daemon=True).start()

def InitOSCServer():
	try:
		if getattr(OSCServer,"isactive",False):
			OSCServer.shutdown()
			OSCServer.server_close()
		OSCServer.server_address = (SettingData["OSCHost"], int(SettingData["OSCOut"]))
		OSCServer.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		OSCServer.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		OSCServer.server_bind()
		threading.Thread(target=OSCServer.serve_forever, daemon=True).start()
		OSCServer.isactive = True
	except Exception as e:
		OSCServer.isactive = False
		window.evaluate_js(f'window.Notice("{e}",3)')

Modules: dict[str, ModuleDataType] = {}
class VRInfoAPI:
	def __init__(self):
		global SettingData, OSCServer, OSCSender
		with open(APPROOT_PATH/"Setting.json", "r", encoding="utf-8") as f:
			SettingData = json.load(f)
		OSCServer = osc_server.ThreadingOSCUDPServer((SettingData["OSCHost"], int(SettingData["OSCOut"])), dispatcher.Dispatcher(), bind_and_activate=False)
		OSCSender = udp_client.SimpleUDPClient(SettingData["OSCHost"], int(SettingData["OSCIn"]))

	def ontop(self, State:bool):
		threading.Thread(target=lambda s: setattr(window, "on_top", s), args=(State,), daemon=True).start()
		return window.on_top
	
	def LoadModule(self):
		ModuleFolders = os.listdir(MODULES_PATH)
		for ModuleFolder in ModuleFolders:
			if ModuleFolder.startswith("_"):
				continue
			try:
				if not (MODULES_PATH/ModuleFolder/"ModuleInfo.json").exists():
					raise Exception("Missing File: ModuleInfo.json")
				
				if not (MODULES_PATH/ModuleFolder/"Layout.xaml").exists():
					raise Exception("Missing File: Layout.xaml")
				
				if not (MODULES_PATH/ModuleFolder/"Function.pyd").exists():
					if not (MODULES_PATH/ModuleFolder/"Function.py").exists():
						raise Exception("Missing File: Function.py")
					else:
						FunctionName = "Function.py"
				else:
					FunctionName = "Function.pyd"
				
				if isDebug:
					TempFolder = MODULES_PATH/ModuleFolder
				else:
					TempFolder = Path(tempfile.mkdtemp(prefix="VRCUtil_"))
					atexit.register(deleteFile, TempFolder)
					sys.path.insert(0, str(TempFolder))

					if (MODULES_PATH/ModuleFolder/"Python").exists():
						shutil.copytree(MODULES_PATH/ModuleFolder/"Python", TempFolder, dirs_exist_ok=True)
					shutil.copy(MODULES_PATH/ModuleFolder/FunctionName, TempFolder/FunctionName)

				try:
					Spec = importlib.util.spec_from_file_location("Function", TempFolder/FunctionName)
					Module = importlib.util.module_from_spec(Spec)
					Module.__file__ = str(MODULES_PATH/ModuleFolder/FunctionName)
					Spec.loader.exec_module(Module)
				except ImportError as e:
					raise Exception(f"Module Raise ImportError: {e}")

				MainClass = getattr(Module, "MainClass")()
				MainClass.window = window
				MainClass.OSCServer = OSCServer
				MainClass.OSCSender = OSCSender

				with open(MODULES_PATH/ModuleFolder/"ModuleInfo.json", "r", encoding="UTF-8") as file:
					Modules[ModuleFolder] = ModuleDataType(
						**json.load(file),
						ModulePath=str(MODULES_PATH/ModuleFolder),
						Layout=LoadXaml(MODULES_PATH/ModuleFolder, "Layout.xaml"),
						Widget=LoadXaml(MODULES_PATH/ModuleFolder, "Widget.xaml"),
						Function=MainClass
					)
			except Exception as e:
				ErrorMessage = json.dumps(f"Load Failed {ModuleFolder}\n{e}")
				window.evaluate_js(f'window.Notice({ErrorMessage}, 3)')
		return {
			"LayoutData": {k: v.Layout for k, v in Modules.items()},
			"WidgetData": {k: v.Widget for k, v in Modules.items() if v.Widget},
			"ModuleData": {
				k: {
					"DisplayName": Module.DisplayName,
					"DisplayIcon": Module.DisplayIcon,
					"Version": Module.Version,
					"Author": Module.Author,
					"Description": Module.Description,
					"Url": Module.Url
				}
				for k, Module in Modules.items()
			}
		}

	def InitModule(self):
		InitOSCServer()
		for name in Modules.keys():
			ExecModule(name, "init")
		
	def GetValue(self, ModuleName:str, ValueName:str, Value=None):
		if ModuleName == "Settings":
			if ValueName == "version":
				return UpdateData("Settings", ValueName, VERSION)
			if ValueName == "newversion":
				return UpdateData("Settings", ValueName, VERSION if isDebug else requests.get(REPO_URL).json()["tag_name"])
			if Value != None:
				if ValueName == "AutoStart":
					return UpdateData("Settings", ValueName, self.SetAutoStart(Value))
				SettingData[ValueName] = Value
				SaveSetting()
				if isPortChanged:=(ValueName in ["OSCIn", "OSCOut"]):
					BeforePort = (OSCSender._port, OSCServer.server_address[1])
				if ValueName in ["OSCHost", "OSCOut"]:
					InitOSCServer()
				if ValueName in ["OSCHost", "OSCIn"]:
					OSCSender._address = SettingData["OSCHost"]
					OSCSender._port = int(SettingData["OSCIn"])
				if isPortChanged:
					for name in Modules.keys():
						ExecTryModule(name, "onPortChange", BeforePort, (OSCSender._port, OSCServer.server_address[1]))
			return UpdateData("Settings", ValueName, SettingData[ValueName])
		elif ValueName=="VRCUtil_Remove_This_Module":
			del Modules[ModuleName]
			gc.collect()
			if not isDebug:
				threading.Thread(target=deleteFile, args=(MODULES_PATH/ModuleName,)).start()
		else:
			Paths = ValueName.split(".")
			if Data := getattr(Modules[ModuleName].Function, "Data", None):
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
			if getattr(Modules[ModuleName].Function, Paths[0], None):
				ExecModule(ModuleName, Paths[0], Value, *Paths[1:])
			if getattr(Modules[ModuleName].Function, "SaveData", None):
				ExecModule(ModuleName, "SaveData")
			try:
				UpdateData(ModuleName, ValueName, Data[lastKey])
			except:
				pass

	def SetAutoStart(self, State: bool):
		if not os.path.exists(OpenVRPaths:=Path(os.getenv('LOCALAPPDATA'))/"openvr"/"openvrpaths.vrpath"):
			return window.evaluate_js(f'window.Notice("SteamVR is not installed", 3)')
		
		with open(OpenVRPaths, "r") as file:
			SteamVRPath = Path([i for i in json.load(file)["config"]if "Steam" in i][0])

		vrmanifestPath = APPROOT_PATH/'manifest.vrmanifest'
		SteamVRConfig = SteamVRPath/"appconfig.json"

		with open(SteamVRPath/"vrappconfig"/"Haruna5718.VRCUtil.vrappconfig", "w") as file:
			json.dump({"autolaunch": State, "last_launch_time": "0"}, file, indent=4)

		with open(SteamVRConfig, "r") as file:
			data = json.load(file)

		if str(vrmanifestPath) not in data["manifest_paths"]:
			data["manifest_paths"].append(str(vrmanifestPath))
			with open(SteamVRConfig, "w") as file:
				json.dump(data, file, indent=4)

		return State

api = VRInfoAPI()
window = webview.create_window("VRCUtil", str("http://localhost:3000/" if isDebug else APPROOT_PATH/"FrontEnd"/"index.html"), js_api=api, background_color="#202020", frameless=True, easy_drag=False, draggable=True, text_select=isDebug, width=900, height=600)

mimetypes.add_type("application/javascript", ".js")

if not isDebug:
	window.events.closed += PostExit

api.destroy = window.destroy
api.minimize = window.minimize

webview.start(debug=isDebug)