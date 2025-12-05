import os
import sys
import pathlib

__all__ = ["event", "file", "osc", "registry", "steam", "wmi", "tkinter", "core"]

__version__ = '3.0.0-dev'

IS_DEBUG = not getattr(sys, 'frozen', False)

if IS_DEBUG:
    INSTALL_PATH = pathlib.Path(__file__).resolve().parent.parent
    DATA_PATH = INSTALL_PATH
else:
    INSTALL_PATH = pathlib.Path(sys.executable).resolve().parent
    DATA_PATH = pathlib.Path(os.environ["APPDATA"])/"VRCUtil"

MODULES_PATH = DATA_PATH/"Modules"