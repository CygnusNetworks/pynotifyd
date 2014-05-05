#!/usr/bin/env python
# -*- coding: utf-8 -*-

import errno
import signal
import select
import time


class SignalDirectoryWatcher(object):
	def __init__(self, _, maxwaittime=3600, signum=signal.SIGUSR1):
		"""
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
		pass  # handling signal to interrupt the sleep

	def __call__(self, maxwait=None):
		if maxwait is None:
			maxwait = self.maxwaittime
		else:
			maxwait = min(maxwait, self.maxwaittime)
		time.sleep(maxwait)  # interrupted by signal

try:
	import pyinotify
except ImportError:
	class InotifyDirectoryWatcher(object):  # pylint: disable=R0903
		def __init__(self, _):
			raise ImportError("failed to import pyinotify")
else:
	class InotifyDirectoryWatcher(object):
		class IgnoreEvent(pyinotify.ProcessEvent):  # pylint:disable=R0903
			def __init__(self):
				pyinotify.ProcessEvent.__init__(self)
			def process_default(self, event):
				pass

		def __init__(self, directory):
			self.watchmanager = pyinotify.WatchManager()
			try:
				self.watchmanager.add_watch(directory, pyinotify.EventsCodes.IN_MOVED_TO)
			except AttributeError:
				self.watchmanager.add_watch(directory, pyinotify.IN_MOVED_TO)

			self.notifier = pyinotify.Notifier(self.watchmanager, InotifyDirectoryWatcher.IgnoreEvent())

		def notifier_check_events_hack(self, maxwait=None):
			"""Hack around limitations of Notifier.check_events.

			I'd like check_events to terminate when a signal is
			received. This is not possible with the current interface,
			so this method monkey patches Notifier."""
			fd = self.notifier._fd  # pylint:disable=W0212
			if maxwait is not None:
				maxwait /= 1000.  # convert milliseconds back to seconds
			try:
				rlist, _, _ = select.select([fd], [], [], maxwait)
				return fd in rlist
			except select.error, err:
				if err[0] == errno.EINTR:
					return False
				raise

		def __call__(self, maxwait=None):
			if maxwait is not None:
				maxwait *= 1000  # milliseconds
			if self.notifier_check_events_hack(maxwait):  # select/poll
				self.notifier.read_events()  # nonblocking read
				self.notifier.process_events()  # clean queue