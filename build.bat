cd "C:\Users\haruna5718\OneDrive\file\code\Project\VRCUtil"

rmdir /s /q "build"
rmdir /s /q "dist"
rmdir /s /q "FrontEnd/dist"

cd FrontEnd
call npm run build
cd ..

rmdir /s /q "FrontEnd/dist/.git"

pyinstaller "VRCUtil.spec"
pyinstaller "Uninstaller.spec" --distpath "dist/VRCUtil"
pyinstaller "Installer.spec"

rmdir /s /q "dist/VRCUtil

python setup.py build_ext --inplace

pyinstaller "BSManager-Installer.spec"
pyinstaller "HeartRate2OSC-Installer.spec"
pyinstaller "OSC2Discord-Installer.spec"
pyinstaller "OSCRouter-Installer.spec"
pyinstaller "VRBattery2OSC-Installer.spec"

rmdir /s /q "build"

@REM pyinstaller -w --noupx -n "VRCUtil" --icon="FrontEnd/dist/favicon.ico" --add-data="C:\Users\haruna5718\AppData\Local\Programs\Python\Python311\Lib\site-packages\openvr\libopenvr_api_32.dll;openvr" --add-data="C:\Users\haruna5718\AppData\Local\Programs\Python\Python311\Lib\site-packages\openvr\libopenvr_api_64.dll;openvr" Main.py
@REM pyinstaller -w --noupx -F -n "Uninstaller" --distpath "C:\Users\haruna5718\OneDrive\file\code\Project\VRCUtil\dist\VRCUtil" --icon="FrontEnd/dist/favicon.ico" VRCUtilUninstaller.py
@REM pyinstaller -w --noupx -F -n "VRCUtil-Installer" --icon="FrontEnd/dist/favicon.ico" --add-data="FrontEnd/dist/favicon.ico;." --add-data="FrontEnd/dist;data/FrontEnd/dist" --add-data="dist/VRCUtil;data" --add-data="manifest.vrmanifest;data" VRCUtilInstaller.py
@REM pyinstaller -w --noupx -F -n "BSManager-Installer" --icon="FrontEnd/dist/favicon.ico" --add-data="FrontEnd/dist/favicon.ico;." --add-data="build/BSManager;data/BSManager" ModuleInstaller.py
@REM pyinstaller -w --noupx -F -n "HeartRate2OSC-Installer" --icon="FrontEnd/dist/favicon.ico" --add-data="FrontEnd/dist/favicon.ico;." --add-data="build/HeartRate2OSC;data/HeartRate2OSC" ModuleInstaller.py
@REM pyinstaller -w --noupx -F -n "OSC2Discord-Installer" --icon="FrontEnd/dist/favicon.ico" --add-data="FrontEnd/dist/favicon.ico;." --add-data="build/OSC2Discord;data/OSC2Discord" ModuleInstaller.py
@REM pyinstaller -w --noupx -F -n "OSCRouter-Installer" --icon="FrontEnd/dist/favicon.ico" --add-data="FrontEnd/dist/favicon.ico;." --add-data="build/OSCRouter;data/OSCRouter" ModuleInstaller.py
@REM pyinstaller -w --noupx -F -n "VRBattery2OSC-Installer" --icon="FrontEnd/dist/favicon.ico" --add-data="FrontEnd/dist/favicon.ico;." --add-data="build/VRBattery2OSC;data/VRBattery2OSC" ModuleInstaller.py
@REM pause