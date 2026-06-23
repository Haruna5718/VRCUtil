@echo off
setlocal

cd /d "%~dp0"

if not exist "%~dp0VRCUtil.exe" (
	exit /b 1
)

start "" "%~dp0VRCUtil.exe" %*
exit /b 0
