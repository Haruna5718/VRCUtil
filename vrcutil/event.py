def _setEvent(*eventData):
	def decorator(func):
		if not hasattr(func, "__VRCUtil_Events__"):
			func.__VRCUtil_Events__ = []
		func.__VRCUtil_Events__.append(eventData)
		
		return func
	return decorator

def onSetup():
	return _setEvent("setup")

def onExit():
	return _setEvent("exit")

def onValueChange(key):
	return _setEvent("setValue", key)

def onSteamVRStart():
	return _setEvent("steamVRStart")

def onSteamVRStop():
	return _setEvent("steamVRStop")

def onVRChatStart():
	return _setEvent("vrchatStart")

def onVRChatStop():
	return _setEvent("vrchatStop")