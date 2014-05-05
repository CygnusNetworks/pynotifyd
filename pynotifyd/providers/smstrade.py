#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gsmsapi.smstrade_api

from .. import errors
import base


class ProviderSmstrade(base.SMSProviderBase):
	"""Send a sms using http://www.smstrade.eu/

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
		api_key = config.get("key", None)
		route = config.get("route", "basic")
		sender = config.get("sender", None)
		if api_key is None:
			raise errors.PyNotifyDConfigurationError("No api key given")
		if route not in ("basic", "gold", "direct"):
			raise errors.PyNotifyDConfigurationError("invalid value %s for route" % route)
		if sender is None:
			raise errors.PyNotifyDConfigurationError("No sender given")

		self.sms = gsmsapi.smstrade_api.SMSTradeAPI(api_key, sender, route)

	def get_balance(self):
		return self.sms.get_balance()

	def send_sms(self, phone, message):
		assert phone.startswith('+')
		# TODO: preprocess phone and message
		self.send_sms(phone[1:], message)