#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement
import logging
import random
import time
import os
import sys
import traceback

import errors
import processlock

logger = logging.getLogger("pynotifyd.queue")


QUEUE_PREFIX = "pynotifyd-"

def generate_unique_id():
	"""Generate a unique identifier.
	@rtype: str
	"""
	# These ids do not collide if a pid rollover takes at least one second.
	tokens = dict(P=os.getpid(), T=time.time(), C=generate_unique_id.counter, R=random.randrange(1 << 32))
	logger.debug("tokens are %s", tokens)
	generate_unique_id.counter += 1
	return "".join(["%s%x" % (key, value) for key, value in tokens.iteritems()])
generate_unique_id.counter = 0


class QueueEntry(object):
	def __init__(self, filename_or_parts):
		"""
		@type filename_or_parts: str or list
		"""
		if isinstance(filename_or_parts, list):
			self.filename = QUEUE_PREFIX + ".".join(filename_or_parts)
			self.parts = filename_or_parts
		else:
			if filename_or_parts.startswith(QUEUE_PREFIX):
				self.filename = filename_or_parts
				self.parts = filename_or_parts[len(QUEUE_PREFIX):].split(".")
			else:
				self.filename = QUEUE_PREFIX + filename_or_parts
				self.parts = filename_or_parts.split(".")
		assert len(self.parts) >= 3

	@classmethod
	def new(cls):
		return cls(["%x" % time.time(), "0", generate_unique_id()])

	def modify(self, wait=0, state=None):
		"""Create a modified QueueEntry instance.

		@type wait: int or float
		@param wait: add this number of seconds to the previous deadline
		@type state: int or None
		@param state: copy state if None, otherwise set state
		@rtype: QueueEntry
		"""
		assert isinstance(wait, int)
		assert state is None or isinstance(state, int)
		parts = ["%x" % (max(time.time(), self.deadline) + wait), self.parts[1] if state is None else "%x" % state] + self.parts[2:]
		return self.__class__(parts)

	@property
	def deadline(self):
		return int(self.parts[0], 16)

	@property
	def state(self):
		return int(self.parts[1], 16)

	@property
	def entryid(self):
		return self.parts[2]

	@property
	def istemporary(self):
		return len(self.parts) != 3

	@property
	def tmpfilename(self):
		return "%s.tmp" % self.filename

	def sleep_duration(self):
		return max(0, self.deadline - time.time())

	def __str__(self):
		return self.filename

	def __repr__(self):
		return "%s(%r)" % (self.__class__.__name__, self.filename)


class PersistentQueue(object):
	def __init__(self, queuedir, retrylogic):
		if not os.path.isdir(queuedir):
			raise errors.PyNotifyDError("queuedir %s does not exist or is not a directory" % queuedir)
		if not os.access(queuedir, os.R_OK | os.W_OK | os.X_OK):
			raise errors.PyNotifyDError("queuedir %s lacks required permission" % queuedir)
		self.queuedir = queuedir
		self.retrylogic = retrylogic
		self.processlock = None

	def get_path(self, filename):
		"""
		@type filename: str or QueueEntry
		@rtype: str
		"""
		if isinstance(filename, QueueEntry):
			filename = filename.filename
		return os.path.join(self.queuedir, filename)

	def advance_waits(self, entry, fast=False):
		"""Create a new entry with the sleep states advanced.
		The queue is not modified in any way.

		@type entry: QueueEntry
		@type fast: bool
		@param fast: if True the next pending wait states are skipped.
			This is useful if the previous failure is permanent and
			additional waiting does not improve the situation.
		@rtype: QueueEntry
		"""
		state = self.get_state(entry)
		while isinstance(state, int):
			entry = entry.modify(wait=0 if fast else state, state=entry.state + 1)
			state = self.get_state(entry)
		return entry

	def enqueue(self, recipient, message):
		"""
		@type recipient: str
		@type message: str
		@rtype: QueueEntry
		"""
		entry = self.advance_waits(QueueEntry.new())
		tmpname = self.get_path(entry.tmpfilename)
		try:
			with file(tmpname, "w") as tmpfile:
				tmpfile.write("%s\n%s" % (recipient, message))
			os.rename(tmpname, self.get_path(entry))
		except OSError, err:
			raise errors.PyNotifyDError("failed to create queue file: %s" % str(err))
		return entry

	def iter_entries(self):
		"""
		@rtype: gen([QueueEntry])
		"""
		for entry in os.listdir(self.queuedir):
			logger.debug("Found file named %s in queuedir %s", entry, self.queuedir)
			if entry.startswith(QUEUE_PREFIX):
				logger.debug("File %s is a pynotifyd queue entry", entry)
				entry = QueueEntry(entry)
				if not entry.istemporary:
					yield entry

	def find_next(self):
		"""
		@rtype: QueueEntry or None
		"""
		try:
			return min(self.iter_entries(), key=lambda entry: entry.deadline)
		except ValueError:  # empty sequence
			return None

	def get_state(self, entry):
		"""Converts an entry (which has a state) to a provider name or
		waiting time.

		@type entry: QueueEntry
		@rtype: int or str
		@returns: number of seconds to wait or the next provider
		"""
		state = entry.state
		if state >= len(self.retrylogic):
			return "GIVEUP"
		state = self.retrylogic[state]
		if state.isdigit():
			state = int(state)
		return state

	def get_contents(self, entry):
		"""
		@type entry: QueueEntry
		@rtype: (str, str)
		@returns: (recipient, message)
		"""
		with file(self.get_path(entry)) as queuefile:
			return queuefile.readline().strip(), queuefile.read()

	def entry_done(self, entry):
		"""
		@type entry: QueueEntry
		"""
		os.unlink(self.get_path(entry))

	def entry_next(self, entry, fast=False):
		"""
		@type entry: QueueEntry
		@type fast: bool
		@param fast: if True the next pending wait states are skipped.
			This is useful if the previous failure is permanent and
			additional waiting does not improve the situation.
		"""
		newentry = self.advance_waits(entry.modify(state=entry.state + 1), fast)
		os.rename(self.get_path(entry), self.get_path(newentry))

	def lock(self):
		"""Lock the queuedir.

		@raises PyNotifyDError:
		"""
		if self.processlock:
			raise errors.PyNotifyDError("already locked")
		self.processlock = processlock.ProcessLock(os.path.join(self.queuedir, ".lock"))
		if not self.processlock.tryacquire():
			self.processlock = None
			raise errors.PyNotifyDError("failed to lock queuedir")

	def getlockowner(self):
		"""Return the pid of the process owning the queue lock.
		@rtype: int or None
		"""
		if self.processlock:
			return self.processlock.getowner()
		return processlock.ProcessLock(os.path.join(self.queuedir, ".lock")).getowner()

	def unlock(self):
		"""Unlock the queuedir."""
		if self.processlock:
			self.processlock.release()
			self.processlock = None

	def clear(self):
		"""Removes all entries from the queue without processing them."""
		logger.debug("queue.clear called")
		for entry in self.iter_entries():
			logger.debug("queue.clear processing entry %s" % entry)
			self.entry_done(entry)


def process_queue_step(config, queue, providers):
	"""
	@type config: configobj.ConfigObj
	@type queue: PersistentQueue
	@type providers: {str: ProviderBase}
	@rtype: int or None
	@returns: None if the queue is empty, number of seconds to sleep
			before calling this function again otherwise
	"""
	entry = queue.find_next()
	if entry is None:
		return
	sleep_time = entry.sleep_duration()
	if sleep_time > 0:
		return sleep_time
	providername = queue.get_state(entry)

	if providername == "GIVEUP":
		logger.debug("giving up on entry %s", str(entry))
		queue.entry_done(entry)
		return 0

	contactname, message = queue.get_contents(entry)
	recipient = dict(name=contactname)
	recipient.update(config["contacts"][contactname])

	logger.debug("delivering entry %s to %s using %s", str(entry), contactname, providername)
	try:
		providers[providername].send_message(recipient, message)
	except errors.PyNotifyDPermanentError, err:
		logger.error("delivery of %s to %s using %s failed with permanent error: %s", str(entry), contactname, providername, str(err))
		queue.entry_next(entry, fast=True)
	except errors.PyNotifyDTemporaryError, err:
		logger.warn("delivery of %s to %s using %s failed with temporary error: %s", str(entry), contactname, providername, str(err))
		queue.entry_next(entry)
	except Exception, exc:
		for line in traceback.format_exc(sys.exc_info()[2]).splitlines():
			logger.warn(line)
		logger.error("delivery of %s to %s using %s failed with an unknown exception: %s  %s", str(entry), contactname, providername, exc.__class__.__name__, str(exc))
		queue.entry_next(entry)
	else:
		logger.debug("delivery of %s to %s using %s succeeded", str(entry), contactname, providername)
		queue.entry_done(entry)
	return 0
