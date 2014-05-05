#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .. import errors


class ProviderBase(object):
	def send_message(self, recipient, message):
		"""This virtual function is to be overridden by provider
		implementations.

		@type recipient: {str: str}
		@type message: str
		@raises PyNotifyDError:
		"""
		raise NotImplementedError

	def terminate(self):
		"""This virtual function is called during shutdown and can be
		overridden by provider instances to free up resources."""
		pass


class SMSProviderBase(ProviderBase):
	"""Somehow send the message as sms.

	Required contact configuration options:
		- phone: A phone number including country code and a leading
			plus sign.

	Note that sms are usually limited in length, so the message gets
	truncated. The truncation length is specified by the implementer
	and defaults to 160.
	"""
	maxsmslength = 160

	def __init__(self, config):
		try:
			maxsmslength = config["maxsmslength"]
			self.maxsmslength = int(maxsmslength)
		except KeyError:
			pass
		except ValueError:
			raise errors.PyNotifyDConfigurationError("maxsmslength config option  requires an integer parameter")

	def send_sms(self, phone, message):
		"""This virtual function is to be overridden by sms proivder
		implementations.

		@type phone: str
		@type message: str
		@raises PyNotifyDError:
		"""
		raise NotImplementedError

	def send_message(self, recipient, message):
		try:
			phone = recipient["phone"]
		except KeyError:
			raise errors.PyNotifyDConfigurationError("missing phone on contact")
		message = message[:self.maxsmslength]
		self.send_sms(phone, message)
