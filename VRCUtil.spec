name = "VRCUtil"

target = [
    {
        "name":"VRCUtil",
        "file":"VRCUtil.py",
        "icon":"VRCUtil.ico",
    },
    {
        "name":"ModuleInstaller",
        "file":"ModuleInstaller.py",
        "icon":"VRCUtil.ico",
    }
]

file = [
    "manifest.vrmanifest",
    "manifest.vrmanifest",
    "Dashboard.xaml",
    "Settings.xaml",
    "VRCUtil.ico",
]

data = []
binary = [
    (".venv\Scripts\pip.exe",".")
]
module = []

collectAllModule = [
    "PIL",
    "glfw",
    "customtkinter",
    "pywebwinui3",
    "openvr",
]

exclude = [
   "PySide6.Qt3DAnimation",
   "PySide6.Qt3DCore",
   "PySide6.Qt3DExtras",
   "PySide6.Qt3DInput",
   "PySide6.Qt3DLogic",
   "PySide6.Qt3DRender",
   "PySide6.QtAxContainer",
   "PySide6.QtBluetooth",
   "PySide6.QtCharts",
   "PySide6.QtConcurrent",
   "PySide6.QtDataVisualization",
   "PySide6.QtDesigner",
   "PySide6.QtHelp",
   "PySide6.QtHttpServer",
   "PySide6.QtLocation",
   "PySide6.QtMultimedia",
   "PySide6.QtMultimediaWidgets",
   "PySide6.QtNfc",
   "PySide6.QtPdf",
   "PySide6.QtPdfWidgets",
   "PySide6.QtPositioning",
   "PySide6.QtQml",
   "PySide6.QtQuick",
   "PySide6.QtQuick3D",
   "PySide6.QtQuickControls2",
   "PySide6.QtQuickWidgets",
   "PySide6.QtRemoteObjects",
   "PySide6.QtScxml",
   "PySide6.QtSensors",
   "PySide6.QtSerialBus",
   "PySide6.QtSerialPort",
   "PySide6.QtSpatialAudio",
   "PySide6.QtSql",
   "PySide6.QtStateMachine",
   "PySide6.QtSvg",
   "PySide6.QtSvgWidgets",
   "PySide6.QtTest",
   "PySide6.QtTextToSpeech",
   "PySide6.QtUiTools",
   "PySide6.QtWebSockets",
   "PySide6.QtXml",
]

UNUSED_FILES = {
    "opengl32sw.dll",
    "pyside6qml.abi3.dll",
    "Qt63DAnimation.dll",
    "Qt63DCore.dll",
    "Qt63DExtras.dll",
    "Qt63DInput.dll",
    "Qt63DLogic.dll",
    "Qt63DQuick.dll",
    "Qt63DQuickAnimation.dll",
    "Qt63DQuickExtras.dll",
    "Qt63DQuickInput.dll",
    "Qt63DQuickLogic.dll",
    "Qt63DQuickRender.dll",
    "Qt63DQuickScene2D.dll",
    "Qt63DQuickScene3D.dll",
    "Qt63DRender.dll",
    "Qt6Charts.dll",
    "Qt6ChartsQml.dll",
    "Qt6Concurrent.dll",
    "Qt6DataVisualization.dll",
    "Qt6DataVisualizationQml.dll",
    "Qt6Graphs.dll",
    "Qt6LabsAnimation.dll",
    "Qt6LabsFolderListModel.dll",
    "Qt6LabsPlatform.dll",
    "Qt6LabsQmlModels.dll",
    "Qt6LabsSettings.dll",
    "Qt6LabsSharedImage.dll",
    "Qt6LabsWavefrontMesh.dll",
    "Qt6Location.dll",
    "Qt6Multimedia.dll",
    "Qt6MultimediaQuick.dll",
    "Qt6OpenGLWidgets.dll",
    "Qt6Pdf.dll",
    "Qt6PdfQuick.dll",
    "Qt6PositioningQuick.dll",
    "Qt6QmlCore.dll",
    "Qt6QmlLocalStorage.dll",
    "Qt6QmlNetwork.dll",
    "Qt6QmlXmlListModel.dll",
    "Qt6Quick3D.dll",
    "Qt6Quick3DAssetImport.dll",
    "Qt6Quick3DAssetUtils.dll",
    "Qt6Quick3DEffects.dll",
    "Qt6Quick3DHelpers.dll",
    "Qt6Quick3DHelpersImpl.dll",
    "Qt6Quick3DParticleEffects.dll",
    "Qt6Quick3DParticles.dll",
    "Qt6Quick3DRuntimeRender.dll",
    "Qt6Quick3DSpatialAudio.dll",
    "Qt6Quick3DUtils.dll",
    "Qt6Quick3DXr.dll",
    "Qt6QuickControls2.dll",
    "Qt6QuickControls2Basic.dll",
    "Qt6QuickControls2BasicStyleImpl.dll",
    "Qt6QuickControls2FluentWinUI3StyleImpl.dll",
    "Qt6QuickControls2Fusion.dll",
    "Qt6QuickControls2FusionStyleImpl.dll",
    "Qt6QuickControls2Imagine.dll",
    "Qt6QuickControls2ImagineStyleImpl.dll",
    "Qt6QuickControls2Impl.dll",
    "Qt6QuickControls2Material.dll",
    "Qt6QuickControls2MaterialStyleImpl.dll",
    "Qt6QuickControls2Universal.dll",
    "Qt6QuickControls2UniversalStyleImpl.dll",
    "Qt6QuickControls2WindowsStyleImpl.dll",
    "Qt6QuickDialogs2.dll",
    "Qt6QuickDialogs2QuickImpl.dll",
    "Qt6QuickDialogs2Utils.dll",
    "Qt6QuickEffects.dll",
    "Qt6QuickLayouts.dll",
    "Qt6QuickParticles.dll",
    "Qt6QuickShapes.dll",
    "Qt6QuickTemplates2.dll",
    "Qt6QuickTest.dll",
    "Qt6QuickTimeline.dll",
    "Qt6QuickTimelineBlendTrees.dll",
    "Qt6QuickVectorImage.dll",
    "Qt6QuickVectorImageGenerator.dll",
    "Qt6QuickVectorImageHelpers.dll",
    "Qt6RemoteObjects.dll",
    "Qt6RemoteObjectsQml.dll",
    "Qt6Scxml.dll",
    "Qt6ScxmlQml.dll",
    "Qt6Sensors.dll",
    "Qt6SensorsQuick.dll",
    "Qt6SerialPort.dll",
    "Qt6ShaderTools.dll",
    "Qt6SpatialAudio.dll",
    "Qt6Sql.dll",
    "Qt6StateMachine.dll",
    "Qt6StateMachineQml.dll",
    "Qt6Svg.dll",
    "Qt6Test.dll",
    "Qt6TextToSpeech.dll",
    "Qt6VirtualKeyboard.dll",
    "Qt6VirtualKeyboardQml.dll",
    "Qt6VirtualKeyboardSettings.dll",
    "Qt6WebChannelQuick.dll",
    "Qt6WebEngineQuick.dll",
    "Qt6WebEngineQuickDelegatesQml.dll",
    "Qt6WebSockets.dll",
    "Qt6WebView.dll",
    "Qt6WebViewQuick.dll",
    "QtOpenGL.pyd",
    "QtPositioning.pyd",
    "QtQml.pyd",
    "QtQuick.pyd",
    "QtQuickWidgets.pyd",
    "qtwebengine_devtools_resources.debug.pak",
    "qtwebengine_resources.debug.pak",
    "qtwebengine_resources_100p.debug.pak",
    "qtwebengine_resources_200p.debug.pak",
    "v8_context_snapshot.debug.bin",
}

#============================================

import sys
import pathlib
import shutil
import threading
from PyInstaller.utils.hooks import collect_all, collect_submodules
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

datas = []

def is_unused_file(path: str) -> bool:
    return pathlib.Path(path).name in UNUSED_FILES

def is_excluded(path: str) -> bool:
    return any(kw in path.replace("\\", "/") for kw in exclude)

def collect(moduleName):
    global data, binary, module
    collectData = collect_all(moduleName, include_py_files=False)
    data   += [x for x in collectData[0] if not is_excluded(x[0]) and not is_unused_file(x[0])]
    binary += [x for x in collectData[1] if not is_excluded(x[0]) and not is_unused_file(x[0])]
    module += collectData[2]

def runThreadWorks(iterable, callback):
    threads:list[threading.Thread] = []
    for item in iterable:
        thread = threading.Thread(target=callback,args=(item,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

def buildExe(info:dict):
    global datas
    a = Analysis(
        [info.get("file")],
        pathex=[],
        binaries=binary,
        datas=data,
        hiddenimports=module,
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        noarchive=True,
        optimize=0,
    )
    exe = EXE(
        PYZ(a.pure),
        a.scripts,
        [],
        exclude_binaries=True,
        name=info.get("name"),
        icon=[info.get("icon")],
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    datas+=[exe,a.binaries,a.datas]

collectAllModule += list(sys.stdlib_module_names)
collectAllModule.remove("antigravity")
collectAllModule.remove("this")
collectAllModule.append("pip")

runThreadWorks(collectAllModule, collect)

runThreadWorks(target, buildExe)

result = COLLECT(
    *datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=name,
)

distPath = pathlib.Path(DISTPATH) / name

for f in distPath.rglob("*"):
    if f.is_file() and f.name in UNUSED_FILES:
        f.unlink()

for f in distPath.rglob("*.pyi"):
    f.unlink()

for f in distPath.rglob("*.pxd"):
    f.unlink()

qmlPath = distPath / "_internal" / "PySide6" / "qml"
if qmlPath.exists():
    shutil.rmtree(qmlPath)

localesPath = distPath / "_internal" / "PySide6" / "translations" / "qtwebengine_locales"
if localesPath.exists():
    for pak in localesPath.glob("*.pak"):
        if pak.name != "en-US.pak":
            pak.unlink()

for path in file:
    sourcePath = pathlib.Path(SPECPATH)/path
    targetPath = distPath/path
    if sourcePath.is_dir():
        shutil.copytree(sourcePath, targetPath, dirs_exist_ok=True, copy_function=shutil.copy)
    else:
        shutil.copy(sourcePath, targetPath)