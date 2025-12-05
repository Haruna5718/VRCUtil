def _setEvent(*eventData):
	def decorator(func):
		if not hasattr(func, "__VRCUtil_Events__"):
			func.__VRCUtil_Events__ = []
		func.__VRCUtil_Events__.append(eventData)
		
		return func
	return decorator

def onExit():
	return _setEvent("closed")

def onValueChange(key):
	return _setEvent("valueChange", key)

def onSteamVRStateChange():
	return _setEvent("valueChange", "steamvr_state")

def onVRChatStateChange():
	return _setEvent("valueChange", "vrchat_state")