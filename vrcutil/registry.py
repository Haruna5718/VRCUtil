import enum
import winreg
import pathlib
import datetime
import logging
import os
import base64
import subprocess

from . import APP_ID

logger = logging.getLogger("vrcutil.registry")


_CREATE_SHORTCUT_SCRIPT = r"""
$ErrorActionPreference = 'Stop'

$shortcutPath = [System.IO.Path]::GetFullPath($env:VRCUTIL_SHORTCUT_PATH)
$targetPath = [System.IO.Path]::GetFullPath($env:VRCUTIL_SHORTCUT_TARGET)
$arguments = $env:VRCUTIL_SHORTCUT_ARGUMENTS
$iconPath = $env:VRCUTIL_SHORTCUT_ICON

if ([string]::IsNullOrWhiteSpace($iconPath)) {
    $iconPath = $targetPath
} else {
    $iconPath = [System.IO.Path]::GetFullPath($iconPath)
}

$parent = [System.IO.Path]::GetDirectoryName($shortcutPath)
if (-not [string]::IsNullOrWhiteSpace($parent)) {
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
}

$shell = $null
$shortcut = $null

try {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $targetPath
    $shortcut.Arguments = $arguments
    $shortcut.WorkingDirectory = [System.IO.Path]::GetDirectoryName($targetPath)
    $shortcut.IconLocation = $iconPath
    $shortcut.Save()
}
finally {
    if ($shortcut -ne $null) {
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($shortcut)
    }
    if ($shell -ne $null) {
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell)
    }
}
"""


_SET_SHORTCUT_APPID_SCRIPT = r"""
$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential, Pack = 4)]
public struct PROPERTYKEY
{
    public Guid fmtid;
    public uint pid;

    public PROPERTYKEY(Guid formatId, uint propertyId)
    {
        fmtid = formatId;
        pid = propertyId;
    }
}

[StructLayout(LayoutKind.Explicit)]
public struct PROPVARIANTUNION
{
    [FieldOffset(0)]
    public IntPtr pwszVal;
}

[StructLayout(LayoutKind.Sequential)]
public struct PROPVARIANT
{
    public ushort vt;
    public ushort wReserved1;
    public ushort wReserved2;
    public ushort wReserved3;
    public PROPVARIANTUNION data;

    public static PROPVARIANT FromString(string value)
    {
        var variant = new PROPVARIANT();
        variant.vt = 31;
        variant.data.pwszVal = Marshal.StringToCoTaskMemUni(value);
        return variant;
    }

    public void Clear()
    {
        PropVariantClear(ref this);
    }

    [DllImport("ole32.dll")]
    private static extern int PropVariantClear(ref PROPVARIANT pvar);
}

[ComImport]
[Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPropertyStore
{
    uint GetCount(out uint cProps);
    uint GetAt(uint iProp, out PROPERTYKEY pkey);
    uint GetValue(ref PROPERTYKEY key, out PROPVARIANT pv);
    uint SetValue(ref PROPERTYKEY key, ref PROPVARIANT pv);
    uint Commit();
}

public static class ShortcutPropertyStore
{
    [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
    private static extern void SHGetPropertyStoreFromParsingName(
        string pszPath,
        IntPtr zero,
        uint flags,
        ref Guid riid,
        [Out, MarshalAs(UnmanagedType.Interface)] out IPropertyStore propertyStore
    );

    public static void SetAppUserModelId(string shortcutPath, string appId)
    {
        var iid = new Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99");
        IPropertyStore store;
        SHGetPropertyStoreFromParsingName(shortcutPath, IntPtr.Zero, 2, ref iid, out store);

        var key = new PROPERTYKEY(new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5);
        var value = PROPVARIANT.FromString(appId);

        try
        {
            store.SetValue(ref key, ref value);
            store.Commit();
        }
        finally
        {
            value.Clear();
            if (store != null)
            {
                Marshal.ReleaseComObject(store);
            }
        }
    }
}
"@

$shortcutPath = [System.IO.Path]::GetFullPath($env:VRCUTIL_SHORTCUT_PATH)
$appId = $env:VRCUTIL_SHORTCUT_APPID

if (Test-Path -LiteralPath $shortcutPath) {
    [ShortcutPropertyStore]::SetAppUserModelId($shortcutPath, $appId)
}
"""


def _run_powershell(script: str, env_updates: dict[str, str | pathlib.Path | None]):
    env = os.environ.copy()
    for key, value in env_updates.items():
        env[key] = "" if value is None else str(value)

    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded,
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if result.returncode == 0:
        return

    message = (result.stderr or result.stdout).strip() or f"PowerShell exited with code {result.returncode}"
    raise RuntimeError(message)


def createShortcut(
    shortcutPath: str | pathlib.Path,
    target: str | pathlib.Path,
    arguments: str = "",
    icon: str | pathlib.Path | None = None,
    appId: str | None = APP_ID,
):
    shortcutPath = pathlib.Path(shortcutPath)
    target = pathlib.Path(target).resolve()
    shortcutPath.parent.mkdir(parents=True, exist_ok=True)

    _run_powershell(
        _CREATE_SHORTCUT_SCRIPT,
        {
            "VRCUTIL_SHORTCUT_PATH": shortcutPath,
            "VRCUTIL_SHORTCUT_TARGET": target,
            "VRCUTIL_SHORTCUT_ARGUMENTS": arguments or "",
            "VRCUTIL_SHORTCUT_ICON": icon or target,
        },
    )

    if appId:
        setShortcutAppId(shortcutPath, appId)


def setShortcutAppId(shortcutPath:str|pathlib.Path, appId:str=APP_ID):
    shortcutPath = pathlib.Path(shortcutPath)
    if not shortcutPath.exists():
        return
    try:
        _run_powershell(
            _SET_SHORTCUT_APPID_SCRIPT,
            {
                "VRCUTIL_SHORTCUT_PATH": shortcutPath,
                "VRCUTIL_SHORTCUT_APPID": appId,
            },
        )
    except Exception:
        logger.debug("Failed to set AppUserModelID for shortcut %s", shortcutPath, exc_info=True)

class valueType(enum.IntEnum):
    str = winreg.REG_SZ
    strPATH = winreg.REG_EXPAND_SZ
    int32 = winreg.REG_DWORD
    int = winreg.REG_QWORD
    list = winreg.REG_MULTI_SZ
    bytes = winreg.REG_BINARY
    none = winreg.REG_NONE

class targetType(enum.IntEnum):
    currentUser = winreg.HKEY_CURRENT_USER
    localMachine = winreg.HKEY_LOCAL_MACHINE

def create(target:targetType, path:str, name:str, type:valueType, value):
    with winreg.CreateKey(target, path) as key:
        winreg.SetValueEx(key, name, 0, type, value)

def delete(target:targetType, path:str, name:str=None):
    try:
        with winreg.OpenKey(target, path, 0, winreg.KEY_SET_VALUE|winreg.KEY_READ) as key:
            if name:
                winreg.DeleteValue(key, name)
            else:
                for i in range(winreg.QueryInfoKey(key)[0] - 1, -1, -1):
                    delete(target, fr"{path}\{winreg.EnumKey(key, i)}")
        winreg.DeleteKeyEx(target, path)
    except FileNotFoundError:
        pass

def read(target:targetType, path:str, name:str):
    with winreg.OpenKey(target, path) as key:
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
    def startupShortcutApprovedPath() -> str:
        return r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder"

    @staticmethod
    def autostartApprovedPath() -> str:
        return r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"

    @staticmethod
    def startupShortcutPath(name:str) -> pathlib.Path:
        return pathlib.Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup" / f"{name}.lnk"

    @staticmethod
    def startupShortcutValueName(name:str) -> str:
        return Program.startupShortcutPath(name).name

    @staticmethod
    def startupApprovedValue(state:bool) -> bytes:
        if state:
            return bytes([2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

        epoch = datetime.datetime(1601, 1, 1, tzinfo=datetime.UTC)
        now = datetime.datetime.now(datetime.UTC)
        filetime = int((now - epoch).total_seconds() * 10_000_000)
        return bytes([3, 0, 0, 0]) + filetime.to_bytes(8, "little", signed=False)

    @staticmethod
    def setStartupApproved(path:str, name:str, state:bool):
        create(targetType.currentUser, path, name, valueType.bytes, Program.startupApprovedValue(state))

    @staticmethod
    def unsetStartupApproved(path:str, name:str):
        delete(targetType.currentUser, path, name)

    @staticmethod
    def startupApprovedState(path:str, name:str) -> bool|None:
        try:
            value = read(targetType.currentUser, path, name)[0]
        except FileNotFoundError:
            return None

        if not value:
            return None
        if value[0] == 2:
            return True
        if value[0] == 3:
            return False
        return None

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
    def autostartState(name:str) -> bool|None:
        return Program.startupApprovedState(Program.autostartApprovedPath(), name)

    @staticmethod
    def unsetAutostartState(name:str):
        Program.unsetStartupApproved(Program.autostartApprovedPath(), name)
        logger.info(f"Autostart startup-approved state removed: {name}")

    @staticmethod
    def setStartupShortcut(name:str, target:str|pathlib.Path, arguments:str="", icon:str|pathlib.Path=None):
        target = pathlib.Path(target).resolve()
        shortcut_path = Program.startupShortcutPath(name)
        createShortcut(shortcut_path, target, arguments=str(arguments or ""), icon=icon or target)

        logger.info(f"Startup shortcut registed: {name} {target} {arguments}")

    @staticmethod
    def unsetStartupShortcut(name:str):
        Program.startupShortcutPath(name).unlink(missing_ok=True)
        logger.info(f"Startup shortcut unregisted: {name}")

    @staticmethod
    def startupShortcutState(name:str) -> bool|None:
        return Program.startupApprovedState(Program.startupShortcutApprovedPath(), Program.startupShortcutValueName(name))

    @staticmethod
    def setStartupShortcutState(name:str, state:bool):
        Program.setStartupApproved(Program.startupShortcutApprovedPath(), Program.startupShortcutValueName(name), state)
        logger.info(f"Startup shortcut state setted: {name} {state}")

    @staticmethod
    def unsetStartupShortcutState(name:str):
        Program.unsetStartupApproved(Program.startupShortcutApprovedPath(), Program.startupShortcutValueName(name))
        logger.info(f"Startup shortcut startup-approved state removed: {name}")

    @staticmethod
    def uninstall(id:str):
        delete(targetType.currentUser, fr"Software\Microsoft\Windows\CurrentVersion\Uninstall\{id}")
