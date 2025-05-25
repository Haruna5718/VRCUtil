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

import winreg
import subprocess
import json
import psutil

from Metadata import *

def TurnOffVRCUtil():
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if proc.info['exe'] and os.path.abspath(proc.info['exe']) == str(APPROOT_PATH/'VRCUtil.exe'):
                proc.terminate()
                proc.wait()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def Deleteshortcut():
    ShortcutPath = Path(os.getenv('APPDATA'))/'Microsoft'/'Windows'/'Start Menu'/'Programs'/'VRCUtil.lnk'
    if os.path.exists(ShortcutPath):
        os.remove(ShortcutPath)

def RemoveRegistry():
    RegKey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\VRCUtil"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RegKey, 0, winreg.KEY_SET_VALUE) as _:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, RegKey)

def SetSteamVR():
    try:
        if not os.path.exists(OpenVRPaths:=Path(os.getenv('LOCALAPPDATA'))/"openvr"/"openvrpaths.vrpath"):
            return
        
        with open(OpenVRPaths, "r") as file:
            SteamVRPath = Path([i for i in json.load(file)["config"]if "Steam" in i][0])

        vrmanifestPath = APPROOT_PATH/'manifest.vrmanifest'
        SteamVRConfig = SteamVRPath/"appconfig.json"
        
        os.remove(SteamVRPath/"vrappconfig"/"Haruna5718.VRCUtil.vrappconfig")

        with open(SteamVRConfig, "r") as file:
            data = json.load(file)
            data["manifest_paths"].remove(vrmanifestPath)
            with open(SteamVRConfig, "w") as file2:
                json.dump(data, file2, indent=4)
    except:
        pass


TurnOffVRCUtil()
Deleteshortcut()
RemoveRegistry()
SetSteamVR()

subprocess.Popen(
    ["cmd", "/c", f"timeout /T 5 >nul & rmdir /S /Q {APPROOT_PATH}"],
)