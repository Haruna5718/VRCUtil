from __future__ import annotations

import re
import os
import sys
import enum
import subprocess
import importlib.util
import time
from pathlib import Path
import shutil
import tarfile
import zipfile
import zstandard as zstd


def _rmtree_with_retry(path: Path | str, retries: int = 10, delay: float = 0.25, required: bool = False) -> bool:
	path = Path(path)
	if not path.exists():
		return True

	def _onexc(func, target, excinfo):
		try:
			os.chmod(target, 0o777)
			func(target)
		except Exception:
			pass

	last_error = None
	for _ in range(retries):
		try:
			shutil.rmtree(path, onexc=_onexc)
			return True
		except FileNotFoundError:
			return True
		except OSError as exc:
			last_error = exc
			time.sleep(delay)

	if required and last_error is not None:
		raise last_error

	print(f"Warning: failed to remove directory '{path}', keeping it.")
	return False

MINIMAL_LIB_ROOTS = (
	"__future__.py",
	"_collections_abc.py",
	"_colorize.py",
	"_compat_pickle.py",
	"_markupbase.py",
	"_opcode_metadata.py",
	"_py_warnings.py",
	"_sitebuiltins.py",
	"_weakrefset.py",
	"abc.py",
	"annotationlib.py",
	"ast.py",
	"base64.py",
	"bisect.py",
	"bz2.py",
	"calendar.py",
	"codecs.py",
	"codeop.py",
	"collections",
	"colorsys.py",
	"compileall.py",
	"compression",
	"configparser.py",
	"contextlib.py",
	"copy.py",
	"copyreg.py",
	"csv.py",
	"ctypes",
	"dataclasses.py",
	"datetime.py",
	"decimal.py",
	"dis.py",
	"email",
	"encodings",
	"enum.py",
	"filecmp.py",
	"fnmatch.py",
	"fractions.py",
	"functools.py",
	"genericpath.py",
	"getpass.py",
	"gettext.py",
	"getopt.py",
	"glob.py",
	"gzip.py",
	"hashlib.py",
	"heapq.py",
	"hmac.py",
	"html",
	"http",
	"importlib",
	"inspect.py",
	"io.py",
	"ipaddress.py",
	"json",
	"keyword.py",
	"linecache.py",
	"locale.py",
	"logging",
	"lzma.py",
	"mimetypes.py",
	"netrc.py",
	"ntpath.py",
	"numbers.py",
	"opcode.py",
	"operator.py",
	"optparse.py",
	"os.py",
	"pathlib",
	"pickle.py",
	"pkgutil.py",
	"platform.py",
	"posixpath.py",
	"py_compile.py",
	"queue.py",
	"quopri.py",
	"random.py",
	"re",
	"reprlib.py",
	"runpy.py",
	"selectors.py",
	"shlex.py",
	"shutil.py",
	"signal.py",
	"site.py",
	"socket.py",
	"socketserver.py",
	"ssl.py",
	"stat.py",
	"string",
	"stringprep.py",
	"struct.py",
	"subprocess.py",
	"sysconfig",
	"tarfile.py",
	"tempfile.py",
	"textwrap.py",
	"threading.py",
	"token.py",
	"tokenize.py",
	"tomllib",
	"traceback.py",
	"types.py",
	"typing.py",
	"urllib",
	"uuid.py",
	"warnings.py",
	"weakref.py",
	"xml",
	"xmlrpc",
	"zipfile",
	"zipimport.py",
)

class Nuitka:
	class BuildType(enum.StrEnum):
		ONE_DIR = "standalone"
		ONE_FILE = "onefile"
		MODULE = "module"
		PACKAGE = "package"

	class Plugin(enum.StrEnum):
		PYSIDE6 = "pyside6"
		PYSIDE2 = "pyside2"
		PYQT6 = "pyqt6"
		PYQT5 = "pyqt5"
		TKINTER = "tk-inter"
		WX = "wx"

		NUMPY = "numpy"
		SCIPY = "scipy"
		MATPLOTLIB = "matplotlib"

		MULTIPROCESSING = "multiprocessing"
		IMPLICIT_IMPORTS = "implicit-imports"
		PKG_RESOURCES = "pkg-resources"

		UPX = "upx"

		DATA_FILES = "data-files"

		DILL = "dill"
		GEVENT = "gevent"
		EVENTLET = "eventlet"

	def __init__(self,
		file:Path|str,
		name:str=None,
		icon:Path|str=None,
		buildType:BuildType=BuildType.ONE_DIR,
		console=False,
		needAdmin=False,
		cache=True,
	):
		self.option:list[str] = []
		self.plugin:list[Nuitka.Plugin] = []
		self.file = Path(file).resolve()
		self.name = name or self.file.stem
		self.icon = Path(icon).resolve() if icon else None
		self.buildType = buildType
		self.console = console
		self.needAdmin = needAdmin
		self.cache = cache

		if self.icon:
			self.IncludeFile(self.icon)

		self.SetInformation(None)

	@property
	def command(self) -> list[str]:
		command = [sys.executable, "-m", "nuitka", f"{self.file}"]
		option = []

		option.append(f"--jobs={os.cpu_count():.0f}")
		option.append(f"--assume-yes-for-downloads")
		if not self.cache:
			option.append("--remove-output")

		option.append(f"--mode={self.buildType.value}")
		if self.buildType == self.BuildType.ONE_FILE:
			option.append("--onefile-no-compression")
			option.append(f"--onefile-tempdir-spec={{TEMP}}\\{self.name}")

		if self.buildType not in [Nuitka.BuildType.MODULE , Nuitka.BuildType.PACKAGE]:
			option.append(f"--output-filename={self.name}.exe")
			option.append("--windows-console-mode=force" if self.console else "--windows-console-mode=disable")
			if self.icon:
				option.append(f"--windows-icon-from-ico={self.icon}")
			if self.needAdmin:
				option.append("--windows-uac-admin")
			if self.product:
				option.append(f"--product-name={self.product}")
			if self.company:
				option.append(f"--company-name={self.company}")
			if self.copyright:
				option.append(f"--copyright={self.copyright}")
			if self.description:
				option.append(f"--file-description={self.description}")
			if self.version:
				option.append(f"--file-version={self.version}")
		
		for name in self.plugin:
			option.append(f"--enable-plugin={name.value}")
			match name:
				case Nuitka.Plugin.PYSIDE6:
					if "--include-package=pyside6" not in self.option:
						option.append("--include-qt-plugins=sensible")
				case Nuitka.Plugin.UPX:
					option.append("--onefile-no-compression")
					option.append(f"--upx-binary={Path(__file__).parent/"upx.exe"}")

		return command + option + self.option

	def IncludeModule(self, module:str):
		try:
			self.option.append(f"--include-{'package' if importlib.util.find_spec(module).submodule_search_locations else 'module'}={module}")
		except:
			print(f"Module not found: {module}")

	def IncludeModuleData(self, module:str):
		self.IncludeModule(module)
		self.option.append(f"--include-package-data={module}")

	def ExcludeModule(self, module:str):
		self.option.append(f"--nofollow-import-to={module}")

	def IncludeFile(self, file:Path|str, path:str=None):
		file = Path(file).resolve()
		self.option.append(f"--include-{'data-files' if file.is_file() else 'raw-dir'}={file}={path or file.name}")

	def AddPlugin(self, name:Plugin):
		self.plugin.append(name)

	def RemovePlugin(self, name:Plugin):
		self.plugin.remove(name)

	def SetInformation(self, version:str, name:str=None, company:str=None, copyright:str=None, description:str=None):
		if version:
			self.version = self.normalize_version(version)
			self.product = name
			self.company = company
			self.copyright = copyright
			self.description = description

	@staticmethod
	def normalize_version(version: str) -> str:
		cleaned = re.sub(r"[^0-9.]", "", version)
		parts = [p for p in cleaned.split(".") if p != ""]
		nums = []
		for p in parts:
			try:
				nums.append(str(int(p)))
			except:
				nums.append("0")
		nums = nums[:4]
		nums += ["0"] * (4 - len(nums))
		return ".".join(nums)

	def Build(self, output:Path|str, buildPath:Path|str=None) -> Path:
		output = Path(output).resolve()
		build = Path(buildPath or output.parent) / ".build"
		command = self.command + [f"--output-dir={build}"]
		subprocess.run(command, check=True)
		output.parent.mkdir(parents=True, exist_ok=True)
		result = build/f"{self.file.stem}.dist"
		if self.buildType == Nuitka.BuildType.ONE_DIR:
			if not output.exists():
				shutil.move(str(result), str(output))
			else:
				shutil.copytree(result, output, dirs_exist_ok=True)
				_rmtree_with_retry(result, required=False)
		elif self.buildType == Nuitka.BuildType.ONE_FILE:
			onefile = build/f"{self.name}.exe"
			output.mkdir(exist_ok=True)
			output = output/onefile.name
			shutil.copy2(onefile, output)
			onefile.unlink()
		return output

class CodeSign:
	_signtool_path = None
	_timestamp_url = "http://timestamp.digicert.com"
	def __init__(self, name:str):
		self.thumbprint = subprocess.run(
			[
				"C:\\Program Files\\PowerShell\\7\\pwsh.exe",
				"-NoProfile",
				"-ExecutionPolicy",
				"Bypass",
				"-Command",
				f"""
					$subject = 'CN={name}'
					$now = Get-Date
					$desiredNotAfter = $now.AddYears(100)
					$minimumAcceptableNotAfter = $now.AddYears(50)
					$cert = Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert |
						Where-Object {{ $_.Subject -eq $subject }} |
						Sort-Object NotAfter -Descending |
						Select-Object -First 1
					if (-not $cert -or $cert.NotAfter -lt $minimumAcceptableNotAfter) {{
						$cert = New-SelfSignedCertificate -Subject $subject -Type CodeSigning -CertStoreLocation 'Cert:\\CurrentUser\\My' -HashAlgorithm 'SHA256' -NotAfter $desiredNotAfter
						$cerPath = Join-Path $env:TEMP 'VRCUtil.cer'
						Export-Certificate -Cert $cert -FilePath $cerPath -Force | Out-Null
						Import-Certificate -FilePath $cerPath -CertStoreLocation 'Cert:\\CurrentUser\\TrustedPublisher' | Out-Null
						Import-Certificate -FilePath $cerPath -CertStoreLocation 'Cert:\\CurrentUser\\Root' | Out-Null
						Remove-Item $cerPath -Force -ErrorAction SilentlyContinue
					}}
					$cert.Thumbprint
				""".strip(),
			],
			check=True,
			capture_output=True,
		).stdout.strip()

	@staticmethod
	def _FindSignTool() -> Path:
		if CodeSign._signtool_path and CodeSign._signtool_path.exists():
			return CodeSign._signtool_path

		if path := shutil.which("signtool.exe"):
			CodeSign._signtool_path = Path(path)
			return CodeSign._signtool_path

		kits_root = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
		if kits_root.exists():
			candidates = sorted(kits_root.glob(r"**/x64/signtool.exe"), reverse=True)
			if candidates:
				CodeSign._signtool_path = candidates[0]
				return CodeSign._signtool_path

		vs_root = Path(r"C:\Program Files\Microsoft Visual Studio")
		if vs_root.exists():
			candidates = sorted(vs_root.glob(r"**/signtool.exe"), reverse=True)
			if candidates:
				CodeSign._signtool_path = candidates[0]
				return CodeSign._signtool_path

		raise FileNotFoundError("signtool.exe not found. Install Windows SDK or Visual Studio build tools.")

	def Sign(self, path: Path|str) -> None:
		subprocess.run(
			[
				str(self._FindSignTool()),
				"sign",
				"/tr",
				self._timestamp_url,
				"/td",
				"SHA256",
				"/fd",
				"SHA256",
				"/sha1",
				self.thumbprint,
				"/s",
				"My",
				str(path),
			],
			check=True,
		)

class ProgressPrinter:
    def __init__(
        self,
        total: int,
        prefix: str = "Progress",
        width: int = 26,
        display_type: str = "size",
        max_file_length: int = 44,
        max_line_width: int = 140,
        min_interval: float = 0.05,
    ):
        self.total = max(0, total)
        self.prefix = prefix
        self.width = width
        self.display_type = display_type
        self.max_file_length = min(max_file_length, max_line_width)
        self.min_interval = min_interval
        self._last_render_time = 0.0
        self._last_line = ""

    @staticmethod
    def _format_size(size: int) -> str:
        units = ("B", "KB", "MB", "GB", "TB")
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f}{unit}"
            value /= 1024
        return f"{size}B"

    def _format_value(self, value: int) -> str:
        return str(value) if self.display_type == "count" else self._format_size(value)

    def _clip(self, text: str) -> str:
        if not text or len(text) <= self.max_file_length:
            return text
        keep = self.max_file_length - 3
        head = max(12, keep // 2)
        tail = max(8, keep - head)
        return f"{text[:head]}...{text[-tail:]}"

    def _line(self, current: int, current_file: str) -> str:
        total = self.total
        ratio = 1.0 if total <= 0 else min(max(current / total, 0.0), 1.0)
        filled = min(self.width, int(ratio * self.width))
        if filled <= 0:
            bar = "." * self.width
        elif filled >= self.width:
            bar = "=" * self.width
        else:
            bar = "=" * (filled - 1) + ">" + "." * (self.width - filled)

        text = (
            f"{self.prefix} {ratio * 100:6.2f}% "
            f"[{bar}] {self._format_value(current)}/{self._format_value(total)}"
        )
        if current_file:
            text += f"  {self._clip(current_file)}"
        return text

    def print(self, current: int, current_file: str = "") -> None:
        current = max(0, min(current, self.total)) if self.total > 0 else max(0, current)
        now = time.monotonic()
        if current not in (0, self.total) and (now - self._last_render_time) < self.min_interval:
            return

        line = self._line(current, current_file)
        if line == self._last_line and current not in (0, self.total):
            return

        sys.stdout.write("\r\033[K" + line)
        sys.stdout.flush()
        self._last_render_time = now
        self._last_line = line

    def finish(self, message: str = "", current_file: str = "") -> None:
        final_current = self.total if self.total > 0 else 1
        line = self._line(final_current, current_file)
        sys.stdout.write("\r\033[K" + line)
        if message:
            sys.stdout.write("\n" + message)
        sys.stdout.write("\n")
        sys.stdout.flush()
        self._last_line = line

def CopyMinimalPythonRuntime(target:Path):
	import _distutils_hack
	import setuptools

	base = Path(sys.base_prefix)
	lib = target/"Lib"
	site = lib/"site-packages"
	python_tag = f"python{sys.version_info.major}{sys.version_info.minor}"
	stdlib_zip = target/f"{python_tag}.zip"
	pth = target/f"{python_tag}._pth"
	package_root = Path(setuptools.__file__).resolve().parent.parent

	lib.mkdir(parents=True, exist_ok=True)
	site.mkdir(parents=True, exist_ok=True)
	shutil.copy2(base/"python.exe", target/"python.exe")
	for dll in ("python3.dll", f"{python_tag}.dll"):
		source = base/dll
		if source.exists():
			shutil.copy2(source, target/dll)

	stdlib_zip.unlink(missing_ok=True)
	with zipfile.ZipFile(stdlib_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
		for name in MINIMAL_LIB_ROOTS:
			source = base/"Lib"/name
			if not source.exists():
				continue
			if source.is_dir():
				for file in source.rglob("*"):
					if file.is_file():
						archive.write(file, file.relative_to(base/"Lib").as_posix())
			else:
				archive.write(source, name)

	for source, name in (
		(Path(setuptools.__file__).resolve().parent, "setuptools"),
		(Path(_distutils_hack.__file__).resolve().parent, "_distutils_hack"),
	):
		shutil.copytree(source, site/name, dirs_exist_ok=True)

	for pattern in ("setuptools-*.dist-info", "wheel-*.dist-info"):
		for source in package_root.glob(pattern):
			shutil.copytree(source, site/source.name, dirs_exist_ok=True)

	for name in ("distutils-precedence.pth",):
		source = package_root/name
		if source.exists():
			shutil.copy2(source, site/name)

	pth.write_text(
		"\n".join(
			(
				stdlib_zip.name,
				".",
				"Lib",
				"Lib\\site-packages",
				"import site",
				"",
			)
		),
		encoding="utf-8",
	)

# ========================================

if __name__ == "__main__":
	from vrcutil import __version__ as VRCUTIL_VERSION
	from ModuleInstaller import __version__ as MODULEINSTALLER_VERSION
	from Uninstaller import __version__ as UNINSTALLER_VERSION
	
	# ========================================

	target = Path("build/VRCUtil").resolve()
	Signer = CodeSign("VRCUtil")
	shutil.rmtree(target, ignore_errors=True)

	# ========================================

	VRCUtil = Nuitka(
		file="VRCUtil.py",
		name="VRCUtil",
		icon="VRCUtil.ico",
		buildType=Nuitka.BuildType.ONE_DIR
	)

	VRCUtil.SetInformation(
		version=VRCUTIL_VERSION,
		name=VRCUtil.name,
		company="Haruna5718"
	)

	for module in sys.stdlib_module_names - {"this", "antigravity", "idlelib"}:
		VRCUtil.IncludeModule(module)

	VRCUtil.IncludeModuleData("PIL")
	VRCUtil.IncludeModuleData("glfw")
	VRCUtil.IncludeModuleData("OpenGL")
	VRCUtil.IncludeModuleData("pywebwinui3")
	VRCUtil.IncludeModuleData("customtkinter")

	VRCUtil.IncludeFile("Dashboard.xaml")
	VRCUtil.IncludeFile("Settings.xaml")
	VRCUtil.IncludeFile("manifest.vrmanifest")
	VRCUtil.IncludeFile(".venv/Lib/site-packages/openvr/libopenvr_api_32.dll", "openvr/libopenvr_api_32.dll")
	VRCUtil.IncludeFile(".venv/Lib/site-packages/openvr/libopenvr_api_64.dll", "openvr/libopenvr_api_64.dll")

	VRCUtil.AddPlugin(Nuitka.Plugin.PYSIDE6)
	VRCUtil.AddPlugin(Nuitka.Plugin.TKINTER)

	VRCUtil.Build(target)
	Signer.Sign(target/"VRCUtil.exe")

	# ========================================

	import _distutils_hack
	import pip
	import setuptools

	pip_dir = Path(pip.__file__).resolve().parent

	Pip = Nuitka(
		file="Pip.py",
		name="pip",
		buildType=Nuitka.BuildType.ONE_DIR,
		console=True,
	)

	Pip.SetInformation(
		version=VRCUTIL_VERSION,
		name=Pip.name,
		company="Haruna5718",
	)

	Pip.IncludeModule("pip")
	Pip.IncludeModule("pip._internal")
	Pip.IncludeModule("pip._vendor")
	Pip.IncludeModule("_distutils_hack")
	Pip.IncludeModule("_distutils_hack.override")
	Pip.IncludeFile(pip_dir / "__pip-runner__.py", "pip/__pip-runner__.py")
	Pip.IncludeFile(pip_dir / "_vendor" / "certifi" / "cacert.pem", "pip/_vendor/certifi/cacert.pem")
	Pip.IncludeFile(pip_dir / "_vendor" / "vendor.txt", "pip/_vendor/vendor.txt")
	Pip.IncludeFile(pip_dir / "_vendor" / "distlib", "pip/_vendor/distlib")
	Pip.IncludeFile(pip_dir / "_vendor" / "pyproject_hooks", "pip/_vendor/pyproject_hooks")
	Pip.IncludeFile(Path(setuptools.__file__).resolve().parent, "setuptools")
	Pip.IncludeFile(Path(_distutils_hack.__file__).resolve().parent, "_distutils_hack")

	Pip.Build(target)
	CopyMinimalPythonRuntime(target)
	Signer.Sign(target/"pip.exe")

	# ========================================

	ModuleInstaller = Nuitka(
		file="ModuleInstaller.py",
		name="ModuleInstaller",
		icon="VRCUtil.ico",
		buildType=Nuitka.BuildType.ONE_DIR
	)

	ModuleInstaller.SetInformation(
		version=MODULEINSTALLER_VERSION,
		name=ModuleInstaller.name,
		company="Haruna5718"
	)

	ModuleInstaller.AddPlugin(Nuitka.Plugin.TKINTER)

	ModuleInstaller.Build(target)
	Signer.Sign(target/"ModuleInstaller.exe")

	# ========================================

	Uninstaller = Nuitka(
		file="Uninstaller.py",
		name="Uninstall",
		icon="VRCUtil.ico",
		buildType=Nuitka.BuildType.ONE_DIR
	)

	Uninstaller.SetInformation(
		version=UNINSTALLER_VERSION,
		name=Uninstaller.name,
		company="Haruna5718"
	)

	Uninstaller.AddPlugin(Nuitka.Plugin.TKINTER)

	Uninstaller.Build(target)
	Signer.Sign(target/"Uninstall.exe")

	# ========================================

	for f in target.rglob("*.debug.pak"):
		f.unlink()

	for file in (target/"PySide6"/"translations").rglob("*"):
		if file.is_file() and file.name != "en-US.pak" and not file.name.endswith("en.qm"):
			file.unlink()

	InstallTarget = target.parent/".build"/"VRCUtil.tar.zst"
	InstallTarget.unlink(missing_ok=True)
	files = sorted(path for path in target.rglob("*") if path.is_file())
	sizes = {path: path.stat().st_size for path in files}
	processed_size = 0
	cctx = zstd.ZstdCompressor(level=22, threads=max(1, min(os.cpu_count() or 1, 8)))
	progress = ProgressPrinter(total=sum(sizes.values()), prefix="Compressing", display_type="size")
	with InstallTarget.open("wb") as output:
		with cctx.stream_writer(output) as compressor:
			with tarfile.open(fileobj=compressor, mode="w|") as tar:
				for file in files:
					arcname = file.relative_to(target).as_posix()
					progress.print(processed_size, arcname)
					tar.add(file, arcname=arcname)
					processed_size += sizes[file]
	progress.finish("Compression complete")

	# ========================================

	Installer = Nuitka(
		file="Installer.py",
		name="VRCUtil-Installer",
		icon="VRCUtil.ico",
		buildType=Nuitka.BuildType.ONE_FILE,
	)

	Installer.SetInformation(
		version=VRCUTIL_VERSION,
		name=Installer.name,
		company="Haruna5718"
	)

	Installer.IncludeFile(InstallTarget)

	Installer.AddPlugin(Nuitka.Plugin.TKINTER)

	Installer.Build(target.parent, target.parent)
	Signer.Sign(target.parent/"VRCUtil-Installer.exe")

	# ========================================
