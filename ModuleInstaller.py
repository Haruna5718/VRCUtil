import sys

__version__ = "1.0.0"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)

    if "--debug" in sys.argv:
        import ctypes
        ctypes.windll.kernel32.AllocConsole()
        sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
        sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
        sys.stdin  = open("CONIN$", "r", encoding="utf-8", errors="replace")

    import json
    import os
    import shutil
    import tempfile
    import pathlib
    import zipfile
    import threading
    import webbrowser
    import subprocess
    import customtkinter

    from pywebwinui3.type import Status

    from vrcutil import tkinter, MODULES_PATH, INSTALL_PATH, PACKAGES_PATH
    from vrcutil.hook import invoke_module_hook
    from vrcutil.process import closeProcessImage

    def preserve_module_setting(previous_path: pathlib.Path, current_path: pathlib.Path):
        previous_setting = previous_path / "Setting.json"
        current_setting = current_path / "Setting.json"
        if not previous_setting.exists():
            return False
        current_setting.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(previous_setting, current_setting)
        return True

    def closeRunningVRCUtil() -> tuple[bool, bool]:
        return closeProcessImage("VRCUtil.exe")

    def install_package(module_name: str, target_path: pathlib.Path, on_output=None):
        pip_executable = INSTALL_PATH / "pip.exe"
        command = [
            str(pip_executable),
            "install",
            "--disable-pip-version-check",
            "--no-cache-dir",
            module_name,
            "--upgrade",
            "--target",
            str(target_path),
        ]
        env = os.environ.copy()
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        env["PYTHONUNBUFFERED"] = "1"
        env["PATH"] = os.pathsep.join(
            [str(INSTALL_PATH), str(INSTALL_PATH / "DLLs"), env.get("PATH", "")]
        ).strip(os.pathsep)

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
            bufsize=1,
        )
        output_lines = []
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.rstrip("\r\n")
            if not line:
                continue
            output_lines.append(line)
            if on_output:
                on_output(line)
        process.stdout.close()
        result = process.wait()
        output = "\n".join(output_lines)
        if result != 0:
            raise RuntimeError(
                f"pip install failed: {module_name} (exit code {result})"
                + (f"\n{output}" if output else "")
            )
        return output

    class MainWindow(tkinter.App):
        def __init__(self, title:str, size:list[int], icon:str, resize:bool=True):
            super().__init__(title, size, icon, resize)

            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(0, weight=1)

            self.page = Infopage(self, self.acm)
            self.page.grid(row=0, padx=10, pady=(10, 0), sticky="sew")

            tkinter.Button(self, self.acm, text="Install Module", color=Status.Attention, callback=self.install).grid(row=1, padx=10, pady=10, sticky="ews")

        def install(self, target:tkinter.Button):
            self.page.destroy()
            target.config(False,"Installing")
            self.setClosable(False)
            self.page = InstallPage(self, self.acm, target)
            self.page.grid(row=0, padx=10, pady=(10, 0), sticky="sew")

    class Infopage(tkinter.Page):
        def __init__(self, master:MainWindow, acm):
            super().__init__(master, acm, round=None)

            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(2, weight=1)

            customtkinter.CTkLabel(self, text=installData["name"], font=customtkinter.CTkFont(size=24, weight="bold")).grid(row=0, padx=10, pady=(10, 0), sticky="nw")
            customtkinter.CTkLabel(self, text=installData["version"], font=customtkinter.CTkFont(size=12)).grid(row=0, padx=15, pady=(7, 0), sticky="ne")
            customtkinter.CTkLabel(self, text=installData["author"], height=24).grid(row=1, padx=13, pady=(4, 0), sticky="sw")
            
            self.frame = customtkinter.CTkFrame(self, fg_color="transparent")
            self.frame.grid(row=1, padx=10, sticky="se")
            
            for data in installData["urls"]:
                name, url = list(data.items())[0]
                tkinter.Button(self.frame, self.acm, text=name, width=0, callback=lambda _, url=url: webbrowser.open(url), color=Status.Attention).pack(padx=(5, 0), side="right")

            self.description = tkinter.Textbox(self, font=customtkinter.CTkFont(size=14), readonly=True)
            self.description.grid(row=2, padx=10, pady=10, sticky="nsew")
            self.description.write(installData["description"])

    class InstallPage(tkinter.Page):
        def __init__(self, master:MainWindow, acm, button:tkinter.Button):
            super().__init__(master, acm, round=None)

            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(2, weight=1)

            self.button = button

            self.message = customtkinter.CTkLabel(self, text=f'Installing {installData["name"]} {installData["version"]}', height=16)
            self.message.grid(row=0, padx=10, pady=(10, 5), sticky="nw")

            self.progress = tkinter.ProgressBar(self, self.acm)
            self.progress.grid(row=1, padx=10, sticky="ew")

            self.installLog = tkinter.Textbox(self, readonly=True)
            self.installLog.grid(row=2, padx=10, pady=10, sticky="nsew")

            threading.Thread(target=self.install,daemon=True).start()

        def install(self):
            stageRoot = None
            stageModulePath = None
            stagePackagePath = None
            backupModulePath = None
            backupPackagePath = None
            movedPackages = []
            moduleSwapped = False
            try:
                installPath = MODULES_PATH/f'{installData["path"]}'
                self.installLog.write(f"Install path: {installPath}")
                closed, forced = closeRunningVRCUtil()
                if closed:
                    self.installLog.write("\nClosed running VRCUtil" + (" (forced)" if forced else ""))
                stageRoot = pathlib.Path(tempfile.mkdtemp(prefix="VRCUtil-Module-"))
                stageModulePath = stageRoot / installData["path"]
                stageModulePath.mkdir(parents=True, exist_ok=True)
                stagePackagePath = stageRoot / "Packages"
                stagePackagePath.mkdir(parents=True, exist_ok=True)
                backupPackagePath = stageRoot / "PackagesBackup"
                try:
                    with zip_ref.open("requirements.txt") as f:
                        requirements = [line.strip() for line in f.read().decode("utf-8").splitlines() if line.strip()]
                except:
                    requirements=[]
                fileList = zip_ref.infolist()
                totalProgress = len(fileList)+len(requirements)
                currentProgress = 0

                for info in fileList:
                    self.installLog.write(f"\nExtract: {info.filename}")
                    if not info.is_dir():
                        zip_ref.extract(info, stageModulePath)
                    currentProgress += 1
                    self.progress.set(currentProgress/totalProgress)

                for moduleName in requirements:
                    self.installLog.write(f"\nPackage install: {moduleName}")
                    install_package(
                        moduleName,
                        stagePackagePath,
                        lambda line: self.installLog.write(f"\n{line}"),
                    )
                    currentProgress += 1
                    self.progress.set(currentProgress/totalProgress)

                if installPath.exists():
                    backupModulePath = stageRoot / "__module_backup__"
                    shutil.move(str(installPath), str(backupModulePath))
                shutil.move(str(stageModulePath), str(installPath))
                moduleSwapped = True
                if backupModulePath and backupModulePath.exists():
                    if preserve_module_setting(backupModulePath, installPath):
                        self.installLog.write("\nPreserved: Setting.json")

                for packagePath in sorted(stagePackagePath.iterdir()):
                    targetPath = PACKAGES_PATH / packagePath.name
                    if targetPath.exists():
                        backupTargetPath = backupPackagePath / packagePath.name
                        backupTargetPath.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(targetPath), str(backupTargetPath))
                    shutil.move(str(packagePath), str(targetPath))
                    movedPackages.append(packagePath.name)

                invoke_module_hook(
                    installPath,
                    "install",
                    module_name=installData["name"],
                    module_id=installData["path"],
                    install_data=installData,
                    install_root=INSTALL_PATH,
                    packages_path=PACKAGES_PATH,
                    log=lambda message: self.installLog.write(f"\n{message}") if str(message or "").strip() else None,
                )

                self.progress.config(Status.Success)
                self.button.config(True,"Launch VRCUtil")
                self.button.callback=self.close
                self.master.setClosable(True)
            except Exception as e:
                self.installLog.write("\n\nInstall failed. Rolling back...")
                for packageName in reversed(movedPackages):
                    targetPath = PACKAGES_PATH / packageName
                    if targetPath.is_dir():
                        shutil.rmtree(targetPath, ignore_errors=True)
                    else:
                        targetPath.unlink(missing_ok=True)

                if backupPackagePath and backupPackagePath.exists():
                    for packagePath in sorted(backupPackagePath.iterdir()):
                        shutil.move(str(packagePath), str(PACKAGES_PATH / packagePath.name))

                if moduleSwapped and installPath.exists():
                    shutil.rmtree(installPath, ignore_errors=True)
                if backupModulePath and backupModulePath.exists():
                    shutil.move(str(backupModulePath), str(installPath))

                self.installLog.write(f"\n\nAn error occurred during module initialization\n\n{e}")
                self.progress.config(Status.Critical)
                self.button.config(True,"Close")
                self.button.callback=lambda _: sys.exit(1)
                self.master.setClosable(True)
            finally:
                if stageRoot:
                    shutil.rmtree(stageRoot, ignore_errors=True)

        def close(self, _):
            subprocess.Popen([INSTALL_PATH/"VRCUtil.exe"], cwd=INSTALL_PATH)
            sys.exit(0)

    PACKAGES_PATH.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(PACKAGES_PATH))

    with zipfile.ZipFile(pathlib.Path(sys.argv[1]), 'r') as zip_ref:
        with zip_ref.open("module.json") as f:
            installData = json.load(f)

            MainWindow(title="VRCUtil Module Installer", size=[400,200], icon=INSTALL_PATH/"VRCUtil.ico", resize=False).start()
