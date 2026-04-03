import csv
import subprocess


def hasProcessImage(imageName: str) -> bool:
	result = subprocess.run(
		["tasklist", "/FI", f"IMAGENAME eq {imageName}", "/FO", "CSV", "/NH"],
		capture_output=True,
		text=True,
		creationflags=subprocess.CREATE_NO_WINDOW,
	)
	if result.returncode != 0:
		return False
	for line in result.stdout.splitlines():
		if not line or line.startswith("INFO:"):
			continue
		row = next(csv.reader([line]), None)
		if row and row[0].lower() == imageName.lower():
			return True
	return False


def closeProcessImage(imageName: str) -> tuple[bool, bool]:
	if not hasProcessImage(imageName):
		return False, False

	for forced in (False, True):
		command = ["taskkill", "/IM", imageName, "/T"]
		if forced:
			command.append("/F")
		subprocess.run(
			command,
			capture_output=True,
			text=True,
			creationflags=subprocess.CREATE_NO_WINDOW,
		)
		if not hasProcessImage(imageName):
			return True, forced

	raise RuntimeError(f"Failed to close {imageName}")
