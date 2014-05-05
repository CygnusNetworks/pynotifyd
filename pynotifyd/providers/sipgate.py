#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gsmsapi

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
		if api not in ("basic", "plus", "team"):
			raise errors.PyNotifyDConfigurationError("invalid value %s for api" % api)
		self.sms = gsmsapi.sipgate_api.SipgateAPI(config.get("username"), config.get("password"), api)

	def get_balance(self):
		return self.sms.get_balance()

	def send_sms(self, phone, message):
		assert phone.startswith('+')
		# TODO: preprocess phone and message
		self.send_sms(phone[1:], message)
