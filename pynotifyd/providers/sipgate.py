#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xmlrpclib
import urllib
import pynotifyd
import pynotifyd.providers

__all__ = ["ProviderSipgate"]


class ProviderSipgate(pynotifyd.providers.SMSProviderBase):
	"""Send a sms using http://www.sipgate.de/ via xmlrpc.

	Required configuration options:
		- username
		- password
	Optional configuration options:
		- api (values: basic, plus or team, default: basic)

	See also L{SMSProviderBase}.
	"""
	# Provider documentation can be found at:
	# http://www.sipgate.de/img/sipgate_api_documentation.pdf
	basicurl = "https://%(username)s:%(password)s@samurai.sipgate.net/RPC2"
	teamurl = "https://%(username)s:%(password)s@api.sipgate.net/RPC2"
	identify_client_name = "PyNotifyD"

	def __init__(self, config):
		"""
		@type config: dict-like
		@param config: required keys are username and password.
		@raises PyNotifyDConfigurationError:
		"""
		pynotifyd.providers.SMSProviderBase.__init__(self, config)
		api = config.get("api", "basic").strip().lower()
		if api not in ("basic", "plus", "team"):
			raise pynotifyd.PyNotifyDConfigurationError("invalid value for api")
		baseurl = self.teamurl if api == "team" else self.basicurl
		try:
			url = baseurl % dict(username=urllib.quote(config["username"], ""), password=urllib.quote(config["password"], ""))
		except KeyError:
			raise pynotifyd.PyNotifyDConfigurationError("username and password required")
		self.rpc = xmlrpclib.Server(url)

	def client_identify(self):
		"""
		@raises PyNotifyDTemporaryError:
		"""
		try:
			result = self.rpc.samurai.ClientIdentify(dict(ClientName=self.identify_client_name))
		except xmlrpclib.Error, exc:
			raise pynotifyd.PyNotifyDTemporaryError("xmlrpclib error during sipgate identify: %s" % str(exc))
		else:
			if result.get("StatusCode") != 200:
				raise pynotifyd.PyNotifyDTemporaryError("Sending SMS via sipgate failed with status %s" % repr(result.get("StatusCode")))

	def initiate_send(self, phone, message):
		"""
		@type phone: str
		@param phone: fully expanded phone number including country code, but
				excluding the leading plus sign.
		@type message: str
		@raises PyNotifyDTemporaryError:
		"""
		try:
			result = self.rpc.samurai.SessionInitiate(dict(RemoteUri="sip:%s@sipgate.net" % phone, TOS="text", Content=message))
		except xmlrpclib.Error, exc:
			raise pynotifyd.PyNotifyDTemporaryError("xmlrpclib error during sipgate send: %s" % str(exc))
		else:
			if result.get("StatusCode") != 200:
				raise pynotifyd.PyNotifyDTemporaryError("Sending SMS via sipgate failed with status %s" % repr(result.get("StatusCode")))

	def get_balance(self):
		"""
		@raises PyNotifyDTemporaryError:
		"""
		try:
			result = self.rpc.samurai.BalanceGet()
		except xmlrpclib.Error, exc:
			raise pynotifyd.PyNotifyDTemporaryError("xmlrpclib error during sipgate getbalance: %s" % str(exc))
		else:
			if result.get("StatusCode") != 200:
				raise pynotifyd.PyNotifyDTemporaryError("Getting balance via sipgate failed with status %s" % repr(result.get("StatusCode")))
			try:
				return result["CurrentBalance"]
			except KeyError:
				raise pynotifyd.PyNotifyDTemporaryError("Answer to BalanceGet is lacking balance")

	def sendsms(self, phone, message):
		assert phone.startswith('+')
		# TODO: preprocess phone and message
		self.client_identify()
		self.initiate_send(phone[1:], message)
