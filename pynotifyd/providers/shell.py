#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import subprocess
import pynotifyd
import pynotifyd.providers


class ProviderShell(pynotifyd.providers.ProviderBase):
	"""Send a message using a shell command.

	Required configuration options:
		- command: The command used to send the message. Python string
			interpolation (%(foo)s) is used to insert the necessary
			values. The keys from the contact section are to be prefixed
			with "contact:". The message is provided via the message
			key. Example: echo %(contact:phone)s %(message)s

	Optional configuration options:
		- message_on_stdin: A boolean indicating whether the message
			is to be passed to the command via stdin.
	"""
	def __init__(self, config):
		try:
			command = config["command"]
		except KeyError:
			raise pynotifyd.PyNotifyDConfigurationError("shell driver requires a command")
		if not isinstance(command, str):
			raise pynotifyd.PyNotifyDConfigurationError("command option is not a string")
		self.command = command.split()
		message_on_stdin = config.get("message_on_stdin", "no").strip().lower()
		self.message_on_stdin = message_on_stdin not in ('no', 'false', '0')

	def sendmessage(self, contact, message):
		"""
		@type contact: dict
		@type message: str
		@raises PyNotifyDError:
		"""
		interpolate = dict(("contact:%s" % key, value) for key, value in contact.items())
		interpolate["message"] = message
		command = [part % interpolate for part in self.command]
		try:
			if self.message_on_stdin:
				proc = subprocess.Popen(command, stdin=subprocess.PIPE)
				proc.communicate(message)
			else:
				proc = subprocess.Popen(command)
			retcode = proc.wait()
			if retcode != 0:
				raise pynotifyd.PyNotifyDTemporaryError("received nonzero exit code from shell: %d" % retcode)
		except OSError, exc:
			raise pynotifyd.PyNotifyDPermanentError("received OSError while calling shell: %s" % str(exc))
