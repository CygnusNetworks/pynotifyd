#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gsmsapi.sipgate_api

from .. import errors
import base


class ProviderSipgate(base.SMSProviderBase):
	"""Send a sms using http://www.sipgate.de/ via xmlrpc.

	Required configuration options:
		- username
		- password
	Optional configuration options:
		- api (values: basic, plus or team, default: basic)

	See also L{SMSProviderBase}."""
	def __init__(self, config):
		"""
		@type config: dict-like
		@param config: required keys are username and password.
		@raises PyNotifyDConfigurationError:
		"""
		base.SMSProviderBase.__init__(self, config)
		api = config.get("api", "basic").strip().lower()
		username = config.get("username", None)
		password = config.get("password", None)
		if api not in ("basic", "plus", "team"):
			raise errors.PyNotifyDConfigurationError("invalid value %s for api" % api)
		if username is None:
			raise errors.PyNotifyDConfigurationError("No username is given")
		if username is None:
			raise errors.PyNotifyDConfigurationError("No password is given")

		self.sms = gsmsapi.sipgate_api.SipgateAPI(username, password, api)

	def get_balance(self):
		return self.sms.get_balance()

	def send_sms(self, phone, message):
		assert phone.startswith('+')
		# TODO: preprocess phone and message
		self.send_sms(phone[1:], message)
