import os
import sys
import pathlib

__all__ = ["event", "file", "osc", "registry", "steam", "wmi", "tkinter", "core", "process"]

__version__ = '3.3.0'

WINDOW_NAME = "VRCUtil"
APP_ID = "Haruna5718.VRCUtil"

IS_COMPILED = "__compiled__" in globals()

if IS_COMPILED:
    INSTALL_PATH = pathlib.Path(sys.argv[0]).resolve().parent
    DATA_PATH = pathlib.Path(os.environ["APPDATA"]) / "VRCUtil"
    PACKAGES_PATH = DATA_PATH / "Packages"
    EXECUTABLE = str(INSTALL_PATH / "VRCUtil.exe")
else:
    INSTALL_PATH = pathlib.Path(__file__).resolve().parent.parent
    DATA_PATH = INSTALL_PATH
    PACKAGES_PATH = pathlib.Path(sys.prefix) / "Lib/site-packages"
    EXECUTABLE = f"{sys.executable} {INSTALL_PATH / 'VRCUtil.py'}"

MODULES_PATH = DATA_PATH / "Modules"
