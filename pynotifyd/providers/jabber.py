#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

import pyxmpp.jabber.client
import pyxmpp.message
import pyxmpp.jid
import pyxmpp.presence

import base
import jabbercommon

from .. import errors


class SendJabberClient(jabbercommon.BaseJabberClient, object):  # pylint:disable=R0904
	def __init__(self, jid, password, target, message, exclude_resources, include_states):  # pylint:disable=R0913
		"""
		@type jid: pyxmpp.jid.JID
		@type password: str
		@type target: pyxmpp.jid.JID
		@type message: str
		@type exclude_resources: str -> bool
		@type include_states: str -> bool
		"""
		jabbercommon.BaseJabberClient.__init__(self, jid, password)
		self.target = target
		self.message = pyxmpp.message.Message(to_jid=self.target, body=message)
		self.exclude_resources = exclude_resources
		self.include_states = include_states
		self.failure = errors.PyNotifyDTemporaryError("contact not available")
		self.isdisconnected = False

	### Section: BaseJabberClient API methods
	def handle_contact_available(self, jid, state):
		if jid.bare() != self.target.bare():
			return
		if self.exclude_resources(jid.resource):
			return
		if not self.include_states(state):
			return
		self.stream.send(self.message)
		self.failure = None
		self.disconnect_once()

	### Section: pyxmpp JabberClient API methods
	def roster_updated(self, item=None):
		"""pyxmpp API method"""
		if item is not None:
			return
		try:
			self.roster.get_item_by_jid(self.target)
		except KeyError:
			self.failure = errors.PyNotifyDPermanentError("contact is not my roster")
			# not on roster
			self.disconnect_once()

	### Section: our own methods for controlling the JabberClient
	def disconnect_once(self):
		"""Invoke disconnect on the first call of this method."""
		if not self.isdisconnected:
			self.disconnect()
			self.isdisconnected = True

	def loop_timeout(self, timeout):
		"""
		@type timeout: int
		"""
		now = time.time()
		deadline = now + timeout
		stream = self.get_stream()
		while stream is not None and now < deadline:
			stream.loop_iter(deadline - now)
			stream = self.get_stream()
			now = time.time()


class ProviderJabber(base.ProviderBase, object):
	"""Send a jabber message.

	Required configuration options:
		- jid: The jabber id used for sending the message.
		- password: Password corresponding to the jid.
		- timeout: Number of seconds to wait for presence updates.

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
		self.jid = pyxmpp.jid.JID(config["jid"])
		self.password = config["password"]
		self.timeout = int(config["timeout"])

	def send_message(self, recipient, message):
		jid, exclude_resources, include_states = jabbercommon.validate_recipient(recipient)
		client = SendJabberClient(self.jid, self.password, jid, message, exclude_resources.__contains__, include_states.__contains__)
		client.connect()
		client.loop_timeout(self.timeout)
		client.disconnect_once()
		if client.failure:
			raise client.failure
