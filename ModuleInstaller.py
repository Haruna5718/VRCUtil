import pathlib
import zipfile
import json
import sys

from vrcutil import pip, MODULES_PATH
from vrcutil.file import SafeRead

if len(sys.argv) > 1:
    modulePath = pathlib.Path(sys.argv[1])

    with zipfile.ZipFile(modulePath, 'r') as zip_ref:
        with zip_ref.open("install.json") as f:
            installData = json.load(f)
            moduleName = installData["name"]
            zip_ref.extractall(path=MODULES_PATH/moduleName, members=[f for f in zip_ref.namelist() if f!="install.json"])

    for packageName in SafeRead(MODULES_PATH/moduleName/"requirments.txt").split("\n"):
        try:
            pip.install_module(packageName)
        except:
            pass