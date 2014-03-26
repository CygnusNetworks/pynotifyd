#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configobj
import time
import validate
import signal
import socket
import select
import errno

__all__ = []

__all__.append("PyNotifyDError")
class PyNotifyDError(Exception):
	"""Base class for PyNotifyD Exceptions."""

__all__.append("PyNotifyDPermanentError")
class PyNotifyDPermanentError(PyNotifyDError):
	"""This exception indicates a problem that cannot be solved by
	simply trying again later."""

__all__.append("PyNotifyDConfigurationError")
class PyNotifyDConfigurationError(PyNotifyDPermanentError):
	"""This exception indicates a problem with the configuration file."""

__all__.append("PyNotifyDTemporaryError")
class PyNotifyDTemporaryError(PyNotifyDError):
	"""This exception indicates a temporary problem with the provider."""

__all__.append("SignalDirectoryWatcher")
class SignalDirectoryWatcher:
	def __init__(self, directory, maxwaittime=3600, signum=signal.SIGUSR1):
		"""
		@type directory: str
		@type maxwaittime: int
		@type signum: int or None
		@param signum: unless None a signal handler is installed for
			this signal. The handler does nothing, but the signal
			interrupts a sleep, so the __call__ method returns upon
			receiving said signal.
		"""
		self.maxwaittime = maxwaittime
		if signum is not None:
			signal.signal(signum, self.process_signal)

	def process_signal(self, signum, stackframe):
		pass # handling signal to interrupt the sleep

	def __call__(self, maxwait=None):
		if maxwait is None:
			maxwait = self.maxwaittime
		else:
			maxwait = min(maxwait, self.maxwaittime)
		time.sleep(maxwait) # interrupted by signal

__all__.append("InotifyDirectoryWatcher")
try:
	import pyinotify
except ImportError:
	class InotifyDirectoryWatcher:
		def __init__(self, directory):
			raise ImportError("failed to import pyinotify")
else:
	class InotifyDirectoryWatcher:
		class IgnoreEvent(pyinotify.ProcessEvent):
			def process_default(self, event):
				pass
		def __init__(self, directory):
			self.watchmanager = pyinotify.WatchManager()
			try:
				self.watchmanager.add_watch(directory,
						pyinotify.EventsCodes.IN_MOVED_TO)
			except AttributeError:
				self.watchmanager.add_watch(directory,
						pyinotify.IN_MOVED_TO)
				
			self.notifier = pyinotify.Notifier(self.watchmanager,
					InotifyDirectoryWatcher.IgnoreEvent())

		def notifier_check_events_hack(self, maxwait=None):
			"""Hack around limitations of Notifier.check_events.

			I'd like check_events to terminate when a signal is
			received. This is not possible with the current interface,
			so this method monkey patches Notifier."""
			fd = self.notifier._fd
			if maxwait is not None:
				maxwait /= 1000. # convert milliseconds back to seconds
			try:
				rlist, _, _ = select.select([fd], [], [], maxwait)
				return fd in rlist
			except select.error, err:
				if err[0] == errno.EINTR:
					return False
				raise

		def __call__(self, maxwait=None):
			if maxwait is not None:
				maxwait *= 1000 # milliseconds
			if self.notifier_check_events_hack(maxwait): # select/poll
				self.notifier.read_events() # nonblocking read
				self.notifier.process_events() # clean queue

config_spec = configobj.ConfigObj("""
[general]
queuedir = string(min=1)
retry = list(min=1)
notify = option("inotify", "signal")
[contacts]
[[__many__]]
[providers]
[[__many__]]
driver = string(min=1)
""".splitlines(), interpolation=False, list_values=False)

def get_the_item(obj, key):
	"""
	Yield obj[key] if it exists and nothing otherwise.
	"""
	try:
		yield obj[key]
	except KeyError:
		pass

def validate_contact(contact):
	"""
	@type contact: {str: str}
	@raises PyNotifyDConfigurationError:
	"""
	for number in get_the_item(contact, "number"):
		if not number.startswith("+"):
			raise PyNotifyDConfigurationError("phone number must start with " +
					"a plus sign")
		if not number[1:].isdigit():
			raise PyNotifyDConfigurationError("non-digits found in phone " +
					"number")

	for jabber in get_the_item(contact, "jabber"):
		if '@' not in jabber:
			raise PyNotifyDConfigurationError("a jabberid has to contain an " +
					"@ sign")

	for email in get_the_item(contact, "email"):
		if '@' not in email:
			raise PyNotifyDConfigurationError("an email address has to " +
					"contain an @ sign")

__all__.append("read_config")
def read_config(filename):
	"""
	@type filename: str
	@rtype: configobj.ConfigObj
	@raises PyNotifyDConfigurationError:
	"""
	spec = config_spec.copy()
	spec["hostname"] = "string(default=%r)" % socket.getfqdn()
	try:
		config = configobj.ConfigObj(filename, interpolation="template",
				configspec=spec, file_error=True)
	except OSError:
		raise PyNotifyDConfigurationError("Failed to read configuration file " +
				"named %r" % repr(filename))

	# general verification
	for section_list, key, error in configobj.flatten_errors(config,
			config.validate(validate.Validator())):
		raise PyNotifyDConfigurationError(("Failed to validate %s in section " +
				"%s.") % (key, ", ".join(section_list)))

	# check contacts
	for contactname, contact in config["contacts"].items():
		if not isinstance(contact, dict):
			raise PyNotifyDConfigurationError("non-section found in section " +
					"contacts")
		try:
			validate_contact(contact)
		except PyNotifyDConfigurationError, err:
			raise PyNotifyDConfigurationError("%s in contact %s" %
					(err.message, contactname))

	# check retry logic
	for provider in config["general"]["retry"]:
		if provider.isdigit() or provider == "GIVEUP":
			continue
		if provider in config["providers"]:
			continue
		raise PyNotifyDConfigurationError("provider %s not found" %
				provider)
	return config
