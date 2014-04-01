#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import random
import pynotifyd
import pynotifyd.providers


class ProviderMock(pynotifyd.providers.ProviderBase):
	"""Do nothing and fail configurably.

	Optional configuration options:
		- duration: Sleep this number of seconds when delivering a
			message. Default: 3
		- failtype: The value must be one out of permanent, temporary,
			random or success. If set to permanent delivery fails with a
			permanent error. If set to temporary delivery fails with a
			temporary error. If set to random it fails with probability
			1/2 with a temporary error. If set to success nothing
			happens.
	"""
	def __init__(self, config):
		self.duration = int(config.get("duration", 3))
		self.failtype = config.get("failtype")
		if self.failtype not in (None, "permanent", "temporary", "random", "success"):
			raise pynotifyd.PyNotifyDConfigurationError("failtype must be one out of: permanent, temporary, random or success")

	def sendmessage(self, recipient, message):
		if self.failtype == "permanent":
			raise pynotifyd.PyNotifyDPermanentError("mocking permanent error")
		time.sleep(self.duration)
		if self.failtype == "temporary":
			raise pynotifyd.PyNotifyDTemporaryError("mocking temporary error")
		elif self.failtype == "random":
			if random.randrange(2) == 0:
				raise pynotifyd.PyNotifyDTemporaryError("mocking random error")
