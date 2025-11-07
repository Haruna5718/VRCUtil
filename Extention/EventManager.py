import logging

logger = logging.getLogger('vrcutil.eventmanager')

class Event:
	@staticmethod
	def _setEvent(*eventdata):
		def decorator(func):
			if not hasattr(func, "__VRCUtil_Events__"):
				func.__VRCUtil_Events__ = []
			func.__VRCUtil_Events__.append(eventdata)
			
			return func
		return decorator
	
	@classmethod
	def onSetup(cls):
		return cls._setEvent("setup")

	@classmethod
	def onExit(cls):
		return cls._setEvent("exit")

	@classmethod
	def onValueChange(cls, key):
		return cls._setEvent("setValue", key)

	@classmethod
	def onSteamVRStart(cls):
		return cls._setEvent("steamVRStart")

	@classmethod
	def onSteamVRStop(cls):
		return cls._setEvent("steamVRStop")
	
	@classmethod
	def onVRChatStart(cls):
		return cls._setEvent("vrchatStart")

	@classmethod
	def onVRChatStop(cls):
		return cls._setEvent("vrchatStop")