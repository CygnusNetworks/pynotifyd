#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pyxmpp.exceptions
import pyxmpp.jabber.client
import pyxmpp.jid
import pyxmpp.presence
import pyxmpp.streamtls

from .. import errors


class BaseJabberClient(pyxmpp.jabber.client.JabberClient, pyxmpp.streamtls.StreamTLSMixIn, object):  # pylint:disable=R0904
	def __init__(self, jid, password, tls_require=True, tls_verify_peer=False, cacert_file=None):
		if tls_verify_peer is True:
			assert cacert_file is not None
		tls = pyxmpp.streamtls.TLSSettings(require=tls_require, verify_peer=tls_verify_peer, cacert_file=cacert_file)
		pyxmpp.jabber.client.JabberClient.__init__(self, jid, password, tls_settings=tls)

	### Section: own hooks
	def handle_session_started(self):
		pass

	def handle_contact_available(self, jid, state):
		"""
		@type jid: pyxmpp.jid.JID
		@type state: unicode
		"""
		pass

	def handle_contact_unavailable(self, jid):
		"""
		@type jid: pyxmpp.jid.JID
		"""
		pass

	### Section: handler functions passed to pyxmpp
	def handle_presence_available(self, presence):
		jid = presence.get_from_jid()
		show = presence.get_show() or u"online"
		self.handle_contact_available(jid, show)

	def handle_presence_unavailable(self, presence):
		jid = presence.get_from_jid()
		self.handle_contact_unavailable(jid)

	### Section: pyxmpp JabberClient API methods
	def session_started(self):
		self.stream.set_presence_handler("available", self.handle_presence_available)
		self.stream.set_presence_handler("unavailable", self.handle_presence_unavailable)
		self.handle_session_started()
		self.request_roster()
		self.stream.send(pyxmpp.presence.Presence())


def make_set(value):
	if isinstance(value, list):
		pass  # ok
	elif isinstance(value, str):
		value = [str.strip(x) for x in value.split(",")]
	else:
		raise ValueError("invalid value type")
	return set(value)


def validate_recipient(recipient):
	"""Extracts and parses the keys "jabber", "jabber_exclude_resources"
	and "jabber_include_states" from the given recipient configuration.

	@type recipient: dict
	@raises pynotifyd.PyNotifyDConfigurationError:
	@rtype: (pyxmpp.jid.JID, set([str]), set([str]))
	@returns: (jid, exclude_resources, include_states)
	"""
	try:
		jid = recipient["jabber"]
	except KeyError:
		raise errors.PyNotifyDConfigurationError("missing jabber on contact")
	try:
		jid = pyxmpp.jid.JID(jid)
	except pyxmpp.exceptions.JIDError, err:
		raise errors.PyNotifyDConfigurationError("failed to parse jabber id: %s" % str(err))
	try:
		exclude_resources = make_set(recipient["jabber_exclude_resources"])
	except KeyError:
		exclude_resources = set()
	except ValueError, err:
		raise errors.PyNotifyDConfigurationError("invalid value for jabber_exclude_resources: %s" % str(err))
	try:
		include_states = make_set(recipient["jabber_include_states"])
	except KeyError:
		include_states = {"online", "chat"}
	except ValueError, err:
		raise errors.PyNotifyDConfigurationError("invalid value for jabber_include_states: %s" % str(err))
	if not include_states:
		raise errors.PyNotifyDConfigurationError("jabber_include_states is empty")
	return jid, exclude_resources, include_states
