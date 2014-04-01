#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This module provides a class ProcessLock that can create reliable
and fault tolerant lock files.
"""

import os
import errno
import time


class ProcessLock(object):
	"""This is a locking mechanism for processes. It uses the fact that
	creation of symbolic links is atomic. To acquire a lock the current
	process id is symlinked to a fixed filename. This is probably a
	dead link. Using the pid from the link stale locks (where
	corresponding process died) can be automatically cleaned. By
	default this class will also clean up the lock automatically on
	destruction (__del__).
	"""
	def __init__(self, filename, autorelease=True):
		"""
		@type filename: str
		@type autorelease: bool
		@param autorelease: the __del__ method will automatically
				release the lock if this is True.
		"""
		self.filename = filename
		self.mypid = os.getpid()
		self.autorelease = autorelease

	def getowner(self):
		"""Return the pid of the process owning the lock.
		@rtype: int or None
		"""
		try:
			otherpid = os.readlink(self.filename)
		except OSError:  # EINVAL, ENOENT, ...
			return None
		# self.filename is a symbolic link pointing to otherpid
		try:
			return int(otherpid)
		except ValueError:
			return None

	def tryacquire(self, handlestale=True):
		"""
		@type handlestale: bool
		@param handlestale: Whether to clean locks that correspond to
				non-existant pids.
		@rtype: bool
		"""
		try:
			os.symlink("%d" % self.mypid, self.filename)
			return True
		except OSError, err:  # ENOENT, EEXIST, ...
			if err.errno != errno.EEXIST or not handlestale:
				return False
		# self.filename exists
		otherpid = self.getowner()
		if otherpid is None:
			return False
		# otherpid is a number
		try:
			os.kill(otherpid, 0)
			return False
		except OSError, err:  # ESRCH, EPERM, ...
			if err.errno != errno.ESRCH:
				return False
		# otherpid is a non-existant pid => stale lock
		try:
			os.unlink(self.filename)
		except OSError:
			return False
		return self.tryacquire()

	def acquire(self, maxwait=None, interval=5, handlestale=True):
		"""
		@type maxwait: int or None
		@param maxwait: maximum number of seconds to wait for the lock
				and None means infinity
		@type interval: int
		@param interval: try locking every interval seconds
		@type handlestale: bool
		@param handlestale: Whether to clean locks that correspond to
				non-existant pids.
		@rtype: bool
		"""
		if maxwait is not None:
			maxwait += time.time()
		while maxwait is None or time.time() < maxwait:
			result = self.tryacquire(handlestale)
			if result:
				return True
			time.sleep(interval)
		return False

	def release(self, force=False):
		"""
		@type force: bool
		@param force: whether to force cleaning the lock even if it got
				tampered with (pid changed, etc.)
		@rtype: bool
		"""
		if (not force) and self.mypid != self.getowner():
			return False
		try:
			os.unlink(self.filename)
		except OSError:
			return False
		return True

	def __del__(self):
		if self.autorelease:
			self.release()
