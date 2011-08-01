import pynotifyd

__all__ = []

__all__.append("ProviderBase")
class ProviderBase:
	def sendmessage(self, recipient, message):
		"""This virtual function is to be overriden by provider
		implementations.

		@type recipient: {str: str}
		@type message: str
		@raises PyNotifyDError:
		"""
		raise NotImplementedError

class SMSProviderBase(ProviderBase):
	"""Somehow send the message as sms.

	Required contact configuration options:
		- phone: A phone number including country code and a leading
			plus sign.

	Note that sms are usually limited in length, so the message gets
	truncated. The truncation length is specified by the implementer
	and defaults to 140.
	"""
	maxsmslength = 140

	def __init__(self, config):
		try:
			maxsmslength = config["maxsmslength"]
			self.maxsmslength = int(maxsmslength)
		except KeyError:
			pass
		except ValueError:
			raise pynotifyd.PyNotifyDConfigurationError("maxsmslength config " +
					"option  requires an integer parameter")

	def sendsms(self, phone, message):
		"""This virtual function is to be overriden by sms proivder
		implementations.

		@type phone: str
		@type message: str
		@raises PyNotifyDError:
		"""
		raise NotImplementedError

	def sendmessage(self, recipient, message):
		try:
			phone = recipient["phone"]
		except KeyError:
			raise pynotifyd.PyNotifyDConfigurationError(
					"missing phone on contact")
		message = message[:self.maxsmslength]
		self.sendsms(phone, message)
