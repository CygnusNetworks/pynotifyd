#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import random

from .. import errors
import base


class ProviderMock(base.ProviderBase):
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
			raise errors.PyNotifyDConfigurationError("failtype must be one out of: permanent, temporary, random or success")

	def send_message(self, recipient, message):
		if self.failtype == "permanent":
			raise errors.PyNotifyDPermanentError("mocking permanent error")
		time.sleep(self.duration)
		if self.failtype == "temporary":
			raise errors.PyNotifyDTemporaryError("mocking temporary error")
		elif self.failtype == "random":
			if random.randrange(2) == 0:
				raise errors.PyNotifyDTemporaryError("mocking random error")
