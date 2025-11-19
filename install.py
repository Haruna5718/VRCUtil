import pathlib
import datetime
import subprocess

from vrcutil import registry, __version__, INSTALL_PATH

def createShortcut(target:str|pathlib.Path,outPath:str|pathlib.Path):
    target = pathlib.Path(outPath).resolve()
    subprocess.run((
        f'powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut(\\"{pathlib.Path(outPath).resolve()}\\");'
        f'$s.TargetPath=\\"{target}\\";'
        f'$s.WorkingDirectory=\\"{target.parent}\\";'
        f'$s.IconLocation=\\"{target}\\";'
        '$s.Save()"'
    ), shell=True, check=True)

registry.ExtConnector.connect(
    id = "VRCUtilModuleFile",
    ext = "vrcutilmodule",
    target = INSTALL_PATH/"ModuleInstaller.exe",
    description = "VRCUtil Module File",
    icon = INSTALL_PATH/"app.ico"
)

# registry.ExtConnector.connect(
#     id = "VRCUtilModuleFile",
#     ext = "vrcutilmodule",
#     target = INSTALL_PATH/"ModuleInstaller.exe",
#     description = "VRCUtil Module File",
#     icon = INSTALL_PATH/"ModuleInstaller.exe"
# )

# registry.Program.install(
#     id = "VRCUtil",
#     name = "VRCUtil",
#     icon = INSTALL_PATH/"VRCUtil.exe",
#     version = __version__,
#     author = "Haruna5718",
#     uninstaller = INSTALL_PATH/"Uninstall.exe",
#     installDir = INSTALL_PATH,
#     installDate = datetime.datetime.now()
# )

# registry.Program.setAutostart(
#     name = "VRCUtil Service Worker",
#     path = INSTALL_PATH/"ServiceWorker.exe"
# )
# createShortcut(INSTALL_PATH/"VRCUtil.exe",pathlib.Path.home()/"AppData"/"Roaming"/"Microsoft"/"Windows"/"Start Menu"/"Programs"/"VRCUtil.lnk")

# createShortcut(INSTALL_PATH/"VRCUtil.exe",pathlib.Path.home()/"Desktop"/"VRCUtil.lnk")