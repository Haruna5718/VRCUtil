import os
import sys
import pathlib

__all__ = ["event", "file", "osc", "registry", "steam", "wmi", "tkinter", "core"]

__version__ = '3.0.0-dev'

IS_DEBUG = "__compiled__" not in globals()

if IS_DEBUG:
    INSTALL_PATH = pathlib.Path(__file__).resolve().parent.parent
    DATA_PATH = INSTALL_PATH
    PACKAGES_PATH = DATA_PATH/".venv/Lib/site-packages"
else:
    INSTALL_PATH = pathlib.Path(sys.executable).resolve().parent
    DATA_PATH = pathlib.Path(os.environ["APPDATA"])/"VRCUtil"
    PACKAGES_PATH = DATA_PATH/"Packages"

MODULES_PATH = DATA_PATH/"Modules"