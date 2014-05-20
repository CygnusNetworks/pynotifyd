#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement
import logging
import os
import random
import select
import socket
import threading
import time

import pyxmpp.exceptions
import pyxmpp.iq
import pyxmpp.jabber.client
import pyxmpp.jid
import pyxmpp.message
import pyxmpp.presence

from .. import errors
import base
import base_jabber

logger = logging.getLogger("pynotifyd.providers.persistentjabber")


def astr(obj):
	"""Convert the given object to unicode and then to ascii replacing
	non-printable characters."""
	return unicode(obj).encode("ascii", "replace")


class XMPPC2SPing(pyxmpp.iq.Iq, object):  # pylint:disable=R0904
	"""Creates ping message from the passed jid to its server."""
	def __init__(self, myjid):
		"""
		@type myjid: pyxmpp.jid.JID
		"""
		pyxmpp.iq.Iq.__init__(self, from_jid=myjid, to_jid=pyxmpp.jid.JID(myjid.domain), stanza_type="get")
		self.new_query("urn:xmpp:ping", "ping")


class FutureTimedOut(Exception):
	"""Raised when you wait for a future for a limited amount of time and no
	result is available after that timeout. """


class Future(object):
	"""A value which is not yet available."""
	def __init__(self):
		self.value = None
		self.event = threading.Event()

	def set(self, value):
		"""Set the value of the future. This may only be done once.
		@type value: object
		"""
		# The assertion is not thread-safe, but merely a sanity check.
		assert not self.event.is_set()
		self.value = value
		self.event.set()

	def get(self, timeout=None):
		"""Look up the value of the future. If the value is not yet set, this
		call blocks. It returns the value passed to set.
		@type timeout: float or None
		@param timeout: maximum number of seconds to wait (None means infinite)
		@raises FutureTimedOut:
		"""
		if timeout is None:
			self.event.wait()
		else:
			if timeout > 0:
				self.event.wait(timeout)
			if not self.event.is_set():
				raise FutureTimedOut()
		return self.value


class SendPing(object):
	"""Construct and send a XMPPC2SPing and set up response handlers."""
	def __init__(self, client, timeout=60):
		"""
		@type timeout: float
		@param timeout: maximum number of seconds to wait for an answer
		"""
		self.ping = XMPPC2SPing(client.jid)
		self.pingresult = Future()
		client.stream.set_response_handlers(self.ping, self.success_handler, self.failure_handler, self.timeout_handler, timeout)
		client.stream.send(self.ping)
		self.sent = time.time()

	def success_handler(self, *_):
		self.pingresult.set(True)

	def failure_handler(self, *_):
		self.pingresult.set(False)

	def timeout_handler(self, *_):
		self.pingresult.set(False)

	def answered(self, maxwait=0):
		"""Has this ping been answered?
		@type maxwait: float
		@param maxwait: wait at most this many number of seconds before
				deciding that there was no answer yet
		@rtype: bool
		"""
		try:
			return self.pingresult.get(maxwait)
		except FutureTimedOut:
			return False

	def age(self):
		"""How much time passed since the we sent this ping?
		@rtype: float
		@returns: seconds
		"""
		return time.time() - self.sent


class PersistentJabberClient(base_jabber.BaseJabberClient, threading.Thread):  # pylint:disable=R0902,R0904
	"""Maintains a persistent jabber connection, presence states of contacts
	and user defined per-resource settings.

	Users may change their settings by sending messages:
	- "ignore": Further messages are pretended to be delivered without
	   being delivered.
	- "disable": This resource will not receive further messages. Other ways
	   of contacting the user are tried.
	- "normal": Reset configuration to normal delivery.
	- "help": Print help text.

	Once a user goes offline or pynotifyd is restarted these settings are reset
	back to "normal".

	Users of ejabberd need to enable mod_ping.

	@type contacts: {JID: {JID: (unicode, unicode)}}
	@ivar contacts: Maps bare JIDs to resourceful JIDs to presence settings
		and states. Possible settings are (u"normal", u"ignore", u"disable").
		Accessed by multiple threads.
	@type connection_is_usable: bool
	@ivar connection_is_usable: False when the connection is known to be dead.
		Accessed by multiple threads, but only locked by writers, because it
		reading is racy in any case.
	@type last_ping: None or SendPing
	@ivar last_ping: A SendPing instance for measuring the availability of the
		connection. Accessed by multiple threads.
	@type last_reconnect: float
	@ivar last_reconnect: unix timestamp when the last reconnect was attempted
		This varible is only accessed by the main thread and never by the
		jabber client thread.
	@type terminating: bool
	@ivar terminating: whether the client is about to shut down
	"""
	MAX_RECONNECT_WAITTIME = 120
	def __init__(self, jid, password, tls_require=True, tls_verify_peer=False, cacert_file=None, ping_max_age=0, ping_timeout=10, reconnect_timeout=600):  # pylint:disable=R0913
		"""
		@type jid: pyxmpp.jid.JID
		@type password: str
		"""
		base_jabber.BaseJabberClient.__init__(self, jid, password, tls_require=True, tls_verify_peer=False, cacert_file=None)
		threading.Thread.__init__(self)
		self.ping_max_age = ping_max_age
		self.ping_timeout = ping_timeout
		self.reconnect_timeout = reconnect_timeout
		self.reconnect_trigger_read, self.reconnect_trigger_write = os.pipe()
		self.reconnect_attempt = 0
		self.last_reconnect = 0
		self.client_lock = threading.Lock()
		self.connection_usable = threading.Condition(self.client_lock)
		self.connection_is_usable = False
		self.contacts = dict()
		self.last_ping = None
		self.terminating = False

	### Section: handler methods passed to pyxmpp
	def handle_message_normal(self, stanza):
		"""Messsage handler function for pyxmpp."""
		jid = stanza.get_from()
		try:
			self.contacts[jid.bare()][jid]  # raises KeyError
		except KeyError:
			return  # only accept messages from known clients
		body = stanza.get_body()
		if body == u"help":
			helpmessage = u"""Valid commands:
- "ignore": Further messages are pretended to be delivered without being delivered.
- "disable": This resource will not receive further messages. Other ways of contacting the user are tried.
- "normal": Reset configuration to normal delivery.
- "help": Print this help text.
"""
			self.stream.send(pyxmpp.message.Message(to_jid=jid, body=helpmessage))
			return
		if body not in (u"normal", u"ignore", u"disable"):
			return
		try:
			inner = self.contacts[jid.bare()]  # raises KeyError
			if inner[jid][0] == body:  # raises KeyError
				raise KeyError("no change needed")
			inner[jid] = (body, inner[jid][1])
		except KeyError:
			pass
		else:
			statusmap = {u"normal": None, u"ignore": u"away", u"disable": u"dnd"}
			self.stream.send(pyxmpp.presence.Presence(to_jid=jid, show=statusmap[body]))

	### Section: BaseJabberClient API methods
	def handle_session_started(self):
		self.stream.set_message_handler("normal", self.handle_message_normal)

	def handle_contact_available(self, jid, state):
		logger.debug("contact %s went online with state %r", astr(jid), state)
		inner = self.contacts.setdefault(jid.bare(), dict())
		inner[jid] = (u"normal", state)

	def handle_contact_unavailable(self, jid):
		logger.debug("contact %s went offline", astr(jid))
		try:
			inner = self.contacts[jid.bare()]  # raises KeyError
			del inner[jid]  # raises KeyError
			if not inner:
				del self.contacts[jid.bare()]
		except KeyError:
			logger.info("could not find jid %s in my online list", astr(jid))

	### Section: pyxmpp JabberClient API methods
	def roster_updated(self, item=None):
		"""pyxmpp API method"""
		if item is not None:
			return
		self.connection_is_usable = True
		self.connection_usable.notify_all()

	def disconnected(self):
		logger.info("Jabber connection terminated.")
		self.initiate_reconnect()

	### Section: our own methods for controlling the JabberClient
	def __del__(self):
		os.close(self.reconnect_trigger_write)
		os.close(self.reconnect_trigger_read)

	def check_availability(self):
		"""Determine availability of the server.
		@rtype: bool
		"""
		if not self.connection_is_usable:
			return False
		with self.client_lock:
			if self.stream is None:
				return False
			if self.last_ping is None or self.last_ping.age() >= self.ping_max_age:
				self.last_ping = SendPing(self, self.ping_timeout)
			last_ping = self.last_ping
		return last_ping.answered(self.ping_timeout)

	def initiate_reconnect(self):
		"""Tell the run method to reconnect immediately."""
		# The connection is broken. Don't wait for a lock to signal that it
		# is broken.
		now = time.time()
		if self.connection_is_usable:
			logger.debug("Initiating jabber reconnect on usable connection.")
		elif self.last_reconnect + self.reconnect_timeout < now:
			logger.debug("Initiating reconnect because previous reconnect timed out.")
		else:
			logger.debug("Not initiating jabber reconnect after recent reconnect.")
			return

		self.connection_is_usable = False
		os.write(self.reconnect_trigger_write, "\0")
		self.last_reconnect = now

	def do_reconnect(self):
		"""must not be called outside of run"""
		logger.debug("Starting reconnect loop.")
		assert not self.connection_is_usable
		while True:
			logger.debug("Clearing data structures before reconnect.")
			self.contacts.clear()
			self.last_ping = None
			# disconnect would be clean, but could take forever.
			if self.stream is not None:
				logger.debug("A stream exists. Close.")
				try:
					self.stream.close()
				except pyxmpp.exceptions.FatalStreamError as exc:
					logger.debug("Failed to close stream with %s. Proceed anyway.", exc)
			self.reconnect_attempt += 1
			wait_time = 10 * self.reconnect_attempt + random.randint(1,10)
			if wait_time > self.MAX_RECONNECT_WAITTIME:
				wait_time = self.MAX_RECONNECT_WAITTIME
			logger.debug("Waiting before trying next reconnect for %s seconds" % wait_time)
			for i in range(0, wait_time+1):
				time.sleep(1)
				if self.terminating:
					logger.debug("Received terminating event during reconnect. Stopping reconnect")
					return
			logger.debug("Attempting to connect to jabber server in try %s" % self.reconnect_attempt)
			try:
				self.connect()
			except pyxmpp.exceptions.FatalStreamError as exc:
				logger.info("Connect failed with %s", exc)
				continue  # try again
			except socket.error as exc:
				logger.info("Connect failed with socket error %s", exc)
				continue  # try again
			else:
				logger.debug("created jabber connection to jabber server - continuing with processing events")
				return

	def run(self):
		"""Process the jabber connection until someone .disconnect()s us.

		Ideally this would be a call to .loop(). Unfortunately there is no way
		to tell .loop() that the jabber connection has gone dead. This is
		rooted in the underlying stream.loop_iter() implementation. Simply
		closing the socket from another thread results in loop_iter() simply
		not noticing that its world suddenly changed. A select on a socket
		being closed simply blocks. So this way of doing things ultimately
		cannot be used. Instead we add a pipe for signalling dead connections
		between the threads and select both now, thus reimplementing the whole
		thing."""
		self.client_lock.acquire()
		try:
			self.connect()
			while True:
				stream = self.get_stream()
				if stream is not None:
					self.client_lock.release()
					logger.debug("jabber thread waiting for input")
					try:
						ifds, _, efds = select.select([stream.socket, self.reconnect_trigger_read], [], [stream.socket], 60)
					finally:
						self.client_lock.acquire()
					if self.terminating:
						logger.debug("detected termination after select")
						break
					elif self.reconnect_trigger_read in ifds:
						logger.debug("jabber thread received reconnect trigger")
						os.read(self.reconnect_trigger_read, 1)  # consume trigger
						self.do_reconnect()
					elif stream.socket in ifds or stream.socket in efds:
						logger.debug("jabber thread processing connection event")
						try:
							stream.process()
							self.reconnect_attempt = 0
						except pyxmpp.exceptions.StreamAuthenticationError:
							logger.error("failed to authenticate to jabber server. terminating", exc_info=True)
							self.terminating = True
							break
						except pyxmpp.exceptions.FatalStreamError as err:
							logger.warning("processing of xmpp stream failed with %r", err, exc_info=True)
							self.connection_is_usable = False
							self.do_reconnect()
							if self.terminating:
								break
					else:
						logger.debug("jabber thread doing xmpp housekeeping")
						stream.idle()
				elif self.terminating:
					logger.debug("detected termination on dead stream")
					break
				else:
					logger.info("no client stream found. reconnecting")
					self.connection_is_usable = False
					self.do_reconnect()
					if self.terminating:
						break
		except Exception as exc:
			logger.warning("jabber thread terminated with exception %r", exc, exc_info=True)
			raise
		else:
			logger.info("jabber thread terminated due to user request")
			assert self.terminating
		finally:
			self.client_lock.release()

	def send_message(self, target, message, exclude_resources, include_states):
		"""
		@type target: pyxmpp.jid.JID
		@type message: str
		@type exclude_resources: str -> bool
		@type include_states: str -> bool
		@raises PyNotifyDPermanentError:
		@raises PyNotifyDTemporaryError:
		"""
		deliver = None
		if not self.connection_is_usable:  # unlocked access, this is racy in any case
			self.initiate_reconnect()
			raise errors.PyNotifyDTemporaryError("jabber client connection is not ready")
		try:
			self.roster.get_item_by_jid(target)
		except KeyError:
			raise errors.PyNotifyDPermanentError("contact is not on my roster")
		if not self.check_availability():
			self.initiate_reconnect()
			raise errors.PyNotifyDTemporaryError("jabber server does not respond to ping, reconnecting")
		with self.client_lock:
			try:
				inner = self.contacts[target.bare()]
			except KeyError:
				raise errors.PyNotifyDTemporaryError("target contact is offline")
			deliver = []
			for jid, (settings, state) in inner.items():
				if settings == u"disable":
					logger.debug("Not sending message to %r. Disabled by user request.", jid)
					continue
				if exclude_resources(jid.resource):
					logger.debug("Not sending message to %r. Resource is excluded.", jid)
					continue
				if not include_states(state):
					logger.debug("Not sending to %r. State %r is not considered available.", jid, state)
					continue
				if settings == u"ignore":
					# Do not trigger temporary errors.
					deliver.append(None)
				else:
					deliver.append(pyxmpp.message.Message(to_jid=jid, body=message))
		for message in deliver:
			if message is not None:
				logger.debug("Sending xmpp message to %s.", astr(message.get_to()))
				self.stream.send(message)
		if not deliver:
			raise errors.PyNotifyDTemporaryError("no usable resources/states found for contact")


class ProviderPersistentJabber(base.ProviderBase):
	"""Send a jabber message.

	Required configuration options:
		- jid: The jabber id used for sending the message.
		- password: Password corresponding to the jid.

	Required contact configuration options:
		- jabber: The jabber id to send the message to.

	Optional contact configuration options:
		- jabber_exclude_resources: A comma-separated list of resources
			that will not receive messages. Default: none.
		- jabber_include_states: A comma-separated list of states that
			receive messages. Available states are online, away, chat,
			dnd and xa. Default: online.
	"""
	def __init__(self, config):
		"""
		@type config: dict-like
		"""
		myjid = pyxmpp.jid.JID(config["jid"])
		if myjid.node is None or myjid.resource is None:  # pylint: disable=E1101
			raise errors.PyNotifyDConfigurationError("jid must be of the form node@domain/resource")

		self.client_thread = PersistentJabberClient(myjid, config["password"])
		self.client_thread.start()

	def send_message(self, recipient, message):
		jid, exclude_resources, include_states = base_jabber.validate_recipient(recipient)
		# The following raises a number of pynotifyd exceptions.
		self.client_thread.send_message(jid, message, exclude_resources.__contains__, include_states.__contains__)

	def terminate(self):
		self.client_thread.terminating = True
		self.client_thread.disconnect()
		self.client_thread.join()
