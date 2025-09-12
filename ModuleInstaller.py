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

import os
import sys
import shutil
import tkinter as tk
from tkinter import ttk
import threading
import psutil
import json
from pathlib import Path

from Metadata import *

def TurnOffVRCUtil():
	for proc in psutil.process_iter(['pid', 'name', 'exe']):
		try:
			if proc.info['exe'] and os.path.abspath(proc.info['exe']) == str(APPROOT_PATH/'VRCUtil.exe'):
				proc.terminate()
				proc.wait()
		except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
			pass

def CopyFiles(src, dst):
	total_files = sum([len(files) for _, _, files in os.walk(src)])
	copied_files = 0

	for dirpath, _, filenames in os.walk(src):
		TargetPath = os.path.join(dst,os.path.relpath(dirpath, src))

		os.makedirs(TargetPath,exist_ok=True)
			
		for filename in filenames:
			if filename=="Setting.json" and os.path.exists(os.path.join(TargetPath, filename)):
				with open(os.path.join(dirpath, filename), 'r', encoding='utf-8') as new_file:
					with open(os.path.join(TargetPath, filename), 'r+', encoding='utf-8') as old_file:
						new_data = json.loads(new_file.read())
						old_data = {key: value for key, value in json.loads(old_file.read()).items() if key in new_data}
						for key, value in new_data.items():
							if key not in old_data:
								old_data[key] = value
						old_file.seek(0)
						json.dump(old_data, old_file, indent=4, ensure_ascii=False)
						old_file.truncate()
			else:
				shutil.copy2(os.path.join(dirpath, filename), os.path.join(TargetPath, filename))
			copied_files += 1
			progress['value'] = (copied_files / total_files) * 100
			root.update_idletasks()

def Installation():
	progress_label.config(text="Shutting down VRCUtil...")
	TurnOffVRCUtil() 
	progress_label.config(text="Installing Module...")

	if not isDebug:
		Path = sys._MEIPASS
		CopyFiles(os.path.join(Path, "data"), MODULES_PATH)

	progress_label.config(text="Installation completed")
	root.after(2000, root.destroy)

root = tk.Tk()
root.title("VRCUtil Module Installer")
root.geometry(f"300x90+{(root.winfo_screenwidth()-300)//2}+{(root.winfo_screenheight()-90)//2}")
root.resizable(False, False)

root.iconbitmap("FrontEnd/dist/favicon.ico" if isDebug else Path(sys._MEIPASS)/"favicon.ico")

progress_label = tk.Label(root, text="Installing Module...")
progress_label.pack(pady=10)

progress = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=250, mode="determinate")
progress.pack()

thread = threading.Thread(target=Installation, daemon=True)
thread.start()

root.mainloop()