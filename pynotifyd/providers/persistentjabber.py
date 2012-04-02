#!/usr/bin/env python

from __future__ import with_statement
import os
import select
import threading
import time

import pyxmpp.exceptions
import pyxmpp.jabber.client
import pyxmpp.jid
import pyxmpp.message
import pyxmpp.presence
import pyxmpp.iq

import pynotifyd
import pynotifyd.providers

__all__ = []

class XMPPC2SPing(pyxmpp.iq.Iq):
	"""Creates ping message from the passed jid to its server."""
	def __init__(self, myjid):
		"""
		@type myjid: pyxmpp.jid.JID
		"""
		pyxmpp.iq.Iq.__init__(self, from_jid=myjid,
				to_jid=pyxmpp.jid.JID(myjid.domain), stanza_type="get")
		self.new_query("urn:xmpp:ping", "ping")

class FutureTimedOut(Exception):
	"""Raised when you wait for a future for a limited amount of time and no
	result is available after that timeout. """

class Future:
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

class SendPing:
	"""Construct and send a XMPPC2SPing and set up response handlers."""
	def __init__(self, client, timeout=60):
		"""
		@type client: JabberClient
		@type timeout: float
		@param timeout: maximum number of seconds to wait for an answer
		"""
		self.ping = XMPPC2SPing(client.jid)
		self.pingresult = Future()
		client.stream.set_response_handlers(self.ping, self.success_handler,
				self.failure_handler, self.timeout_handler, timeout)
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

class PersistentJabberClient(pyxmpp.jabber.client.JabberClient, threading.Thread):
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
	"""
	def __init__(self, jid, password, ping_max_age=0, ping_timeout=10):
		"""
		@type jid: pyxmpp.jid.JID
		@type password: str
		"""
		pyxmpp.jabber.client.JabberClient.__init__(self, jid, password)
		threading.Thread.__init__(self)
		self.ping_max_age = ping_max_age
		self.ping_timeout = ping_timeout
		self.reconnect_trigger_read, self.reconnect_trigger_write = os.pipe()
		self.client_lock = threading.Lock()
		self.connection_usable = threading.Condition(self.client_lock)
		self.connection_is_usable = False
		self.contacts = dict()
		self.last_ping = None

	### Section: handler methods passed to pyxmpp
	def handle_presence_available(self, presence):
		"""Presence handler function for pyxmpp."""
		status = presence.get_show() or u"online"
		jid = presence.get_from_jid()
		with self.client_lock:
			inner = self.contacts.setdefault(jid.bare(), dict())
			inner[jid] = (u"normal", status)

	def handle_presence_unavailable(self, presence):
		"""Presence handler function for pyxmpp."""
		jid = presence.get_from_jid()
		with self.client_lock:
			try:
				inner = self.contacts[jid.bare()] # raises KeyError
				del inner[jid] # raises KeyError
				if not inner:
					del self.contacts[jid.bare()]
			except KeyError:
				pass

	def handle_message_normal(self, stanza):
		"""Messsage handler function for pyxmpp."""
		jid = stanza.get_from()
		with self.client_lock:
			try:
				self.contacts[jid.bare()][jid] # raises KeyError
			except KeyError:
				return # only accept messages from known clients
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
		with self.client_lock:
			try:
				inner = self.contacts[jid.bare()] # raises KeyError
				inner[jid] = (body, inner[jid][1]) # raises KeyError
			except KeyError:
				pass

	### Section: pyxmpp JabberClient API methods
	def session_started(self):
		"""pyxmpp API method"""
		self.stream.set_presence_handler("available", self.handle_presence_available)
		self.stream.set_presence_handler("unavailable", self.handle_presence_unavailable)
		self.stream.set_message_handler("normal", self.handle_message_normal)
		self.request_roster()
		self.stream.send(pyxmpp.presence.Presence())

	def roster_updated(self, item=None):
		"""pyxmpp API method"""
		if item is not None:
			return
		with self.client_lock:
			self.connection_is_usable = True
			self.connection_usable.notify_all()

	### Section: our own methods for controlling the JabberClient
	def __del__(self):
		os.close(self.reconnect_trigger_write)
		os.close(self.reconnect_trigger_read)

	def check_availability(self):
		"""Determine availability of the server.
		@type maxage: float
		@param maxage: use previous result if its age is lower than maxage
				seconds
		@type maxwait: float
		@param maxwait: block up to this number of seconds to send a ping
		@rtype: bool
		"""
		if not self.connection_usable:
			return False
		with self.client_lock:
			if self.last_ping is None or \
					self.last_ping.age() >= self.ping_max_age:
				self.last_ping = SendPing(self, self.ping_timeout)
			last_ping = self.last_ping
		return last_ping.answered(self.ping_timeout)

	def initiate_reconnect(self):
		"""Tell the run method to reconnect immediately."""
		# The connection is broken. Don't wait for a lock to signal that it
		# is broken.
		with self.client_lock:
			if self.connection_is_usable:
				self.connection_is_usable = False
				os.write(self.reconnect_trigger_write, "\0")

	def do_reconnect(self):
		"""must not be called outside of run"""
		assert not self.connection_is_usable
		while True:
			self.contacts.clear()
			self.last_ping = None
			# disconnect would be clean, but could take forever.
			if self.stream is not None:
				try:
					self.stream.close()
				except pyxmpp.exceptions.FatalStreamError:
					pass
			try:
				self.connect()
			except pyxmpp.exceptions.FatalStreamError:
				continue # try again
			else:
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
		self.connect()
		stream = self.get_stream()
		while stream:
			ifds, _, efds = select.select([stream.socket,
				self.reconnect_trigger_read], [], [stream.socket], 60)
			if self.reconnect_trigger_read in ifds:
				os.read(self.reconnect_trigger_read, 1) # consume trigger
				self.do_reconnect()
			elif stream.socket in ifds or stream.socket in efds:
				try:
					stream.process()
				except pyxmpp.exceptions.FatalStreamError:
					self.connection_is_usable = False
					self.do_reconnect()
			else:
				stream.idle()
			stream = self.get_stream()

	def send_message(self, target, message, exclude_resources, include_states):
		"""
		@type target: str
		@type message: str
		@type exclude_resources: str -> bool
		@type include_states: str -> bool
		@raises PyNotifyDPermanentError:
		@raises PyNotifyDTemporaryError:
		"""
		target = pyxmpp.jid.JID(target)
		if not self.connection_is_usable: # unlocked access, this is racy in any case
			raise pynotifyd.PyNotifyDTemporaryError(
					"jabber client connection is not ready")
		try:
			self.roster.get_item_by_jid(target)
		except KeyError:
			raise pynotifyd.PyNotifyDPermanentError(
					"contact is not on my roster")
		if not self.check_availability():
			self.initiate_reconnect()
			raise pynotifyd.PyNotifyDTemporaryError(
					"jabber server does not respond to ping, reconnecting")
		with self.client_lock:
			try:
				inner = self.contacts[target.bare()]
			except KeyError:
				raise pynotifyd.PyNotifyDTemporaryError(
						"target contact is offline")
			deliver = []
			for jid, (settings, state) in inner.items():
				if settings == u"disable":
					continue
				if exclude_resources(jid.resource):
					continue
				if not include_states(state):
					continue
				if settings == u"ignore":
					# Do not trigger temporary errors.
					deliver.append(None)
				else:
					deliver.append(pyxmpp.message.Message(to_jid=jid,
						body=message))
		for message in deliver:
			if message is not None:
				self.stream.send(message)
		if not deliver:
			raise pynotifyd.PyNotifyDTemporaryError(
					"no usable resources/states found for contact")

def make_set(value):
	if isinstance(value, list):
		pass # ok
	elif isinstance(value, str):
		value = map(str.strip, value.split(","))
	else:
		raise ValueError("invalid value type")
	return set(value)

__all__.append("ProviderPersistentJabber")
class ProviderPersistentJabber(pynotifyd.providers.ProviderBase):
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
		self.client_thread = PersistentJabberClient(
				pyxmpp.jid.JID(config["jid"]), config["password"])
		self.client_thread.start()

	def sendmessage(self, recipient, message):
		try:
			jid = recipient["jabber"]
		except KeyError:
			raise pynotifyd.PyNotifyDConfigurationError(
					"missing jabber on contact")
		try:
			exclude_resources = make_set(recipient["jabber_exclude_resources"])
		except KeyError:
			exclude_resources = set()
		except ValueError, err:
			raise pynotifyd.PyNotifyDConfigurationError(
					"invalid value for jabber_exclude_resources: %s" % str(err))
		try:
			include_states = make_set(recipient["jabber_include_states"])
		except KeyError:
			include_states = set(["online"])
		except ValueError:
			raise pynotifyd.PyNotifyDConfigurationError(
					"invalid value for jabber_include_states: %s" % str(err))
		if not include_states:
			raise pynotifyd.PyNotifyDConfigurationError(
					"jabber_include_states is empty")
		# The following raises a number of pynotifyd exceptions.
		self.client_thread.send_message(jid, message,
				exclude_resources.__contains__, include_states.__contains__)

	def terminate(self):
		self.client_thread.disconnect()
		self.client_thread.join()
