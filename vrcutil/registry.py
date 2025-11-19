import winreg
import pathlib
import enum
import datetime
import logging

logger = logging.getLogger("vrcutil.registry")

class valueType(enum.Enum):
    str = winreg.REG_SZ
    strPATH = winreg.REG_EXPAND_SZ
    int32 = winreg.REG_DWORD
    int = winreg.REG_QWORD
    list = winreg.REG_MULTI_SZ
    bytes = winreg.REG_BINARY
    none = winreg.REG_NONE

class targetType(enum.Enum):
    currentUser = winreg.HKEY_CURRENT_USER
    localMachine = winreg.HKEY_LOCAL_MACHINE

def create(target:targetType, path:str, name:str, type:valueType, value):
    with winreg.CreateKey(target.value, path) as key:
        winreg.SetValueEx(key, name, 0, type.value, value)

def delete(target:targetType, path:str, name:str=None):
    try:
        with winreg.OpenKey(target.value, path, 0, winreg.KEY_SET_VALUE|winreg.KEY_READ) as key:
            if name:
                winreg.DeleteValue(key, name)
            else:
                for i in range(winreg.QueryInfoKey(key)[0] - 1, -1, -1):
                    delete(fr"{path}\{winreg.EnumKey(key, i)}")
        winreg.DeleteKeyEx(target.value, path)
    except FileNotFoundError:
        pass

def read(target:targetType, path:str, name:str):
    with winreg.OpenKey(target.value, path) as key:
        return winreg.QueryValueEx(key, name)

class ExtConnector:
    @staticmethod
    def connect(ext:str, id:str, target:str|pathlib.Path, description:str=None, icon:str|pathlib.Path=None):
        create(targetType.currentUser, fr"Software\Classes\.{ext}", "", valueType.str, id)
        create(targetType.currentUser, fr"Software\Classes\{id}\shell\open\command", "", valueType.strPATH, f"\"{target}\" \"%1\"")
        if description:
            create(targetType.currentUser, fr"Software\Classes\{id}", "", valueType.str, description)
        if icon:
            create(targetType.currentUser, fr"Software\Classes\{id}\DefaultIcon", "", valueType.strPATH, str(icon))
        logger.info(f"ext registed ({id}): *.{ext} -> {target}")

    @staticmethod
    def disconnect(ext:str, id:str):
        delete(targetType.currentUser, fr"Software\Classes\.{ext}")
        delete(targetType.currentUser, fr"Software\Classes\{id}")
        logger.info(f"ext unregisted ({id}): *.{ext}")

class Program:
    @staticmethod
    def install(id:str, name:str, uninstaller:str|pathlib.Path, version:str=None, author:str=None, installDir:str|pathlib.Path=None, installDate:datetime.datetime=None, icon:str=None, modifier:str|pathlib.Path=None, canModify:bool=False, canRepair:bool=False):
        path = fr"Software\Microsoft\Windows\CurrentVersion\Uninstall\{id}"

        create(targetType.currentUser, path, "DisplayName", valueType.str, name)
        create(targetType.currentUser, path, "UninstallString", valueType.strPATH, f"\"{uninstaller}\"")

        create(targetType.currentUser, path, "NoModify", valueType.int32, 0 if canModify else 1)
        create(targetType.currentUser, path, "NoRepair", valueType.int32, 0 if canRepair else 1)

        if version:
            create(targetType.currentUser, path, "DisplayVersion", valueType.str, version)
        if author:
            create(targetType.currentUser, path, "Publisher", valueType.str, author)
        if installDir:
            create(targetType.currentUser, path, "InstallLocation", valueType.strPATH, str(installDir))
        if installDate:
            create(targetType.currentUser, path, "InstallDate", valueType.str, installDate.strftime("%Y%m%d"))
        if icon:
            create(targetType.currentUser, path, "DisplayIcon", valueType.strPATH, str(icon))
        if modifier:
            create(targetType.currentUser, path, "ModifyPath", valueType.strPATH, str(modifier))
        logger.info(f"Software registry registed: {name} {version}")

    @staticmethod
    def setAutostart(name:str, path:str|pathlib.Path):
        create(targetType.currentUser, r"Software\Microsoft\Windows\CurrentVersion\Run", name, valueType.strPATH, str(path))
        logger.info(f"Autostart registed: {name} {path}")

    @staticmethod
    def unsetAutostart(name:str):
        delete(targetType.currentUser, r"Software\Microsoft\Windows\CurrentVersion\Run", name)
        logger.info(f"Autostart unregisted: {name}")

    @staticmethod
    def uninstall(id:str):
        delete(targetType.currentUser, fr"Software\Microsoft\Windows\CurrentVersion\Uninstall\{id}")