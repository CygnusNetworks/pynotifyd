import pyxmpp.jabber.client
import pyxmpp.message
import pyxmpp.jid
import pyxmpp.presence
import time
import pynotifyd
import pynotifyd.providers

__all__ = []

class SendJabberClient(pyxmpp.jabber.client.JabberClient):
	def __init__(self, jid, password, target, message, exclude_resources,
			include_states):
		"""
		@type jid: pyxmpp.jid.JID
		@type password: str
		@type target: str
		@type message: str
		@type exclude_resources: str -> bool
		@type include_states: str -> bool
		"""
		pyxmpp.jabber.client.JabberClient.__init__(self, jid, password)
		self.target = pyxmpp.jid.JID(target)
		self.message = pyxmpp.message.Message(to_jid=self.target, body=message)
		self.exclude_resources = exclude_resources
		self.include_states = include_states
		self.failure = pynotifyd.PyNotifyDTemporaryError(
				"contact not available")
		self.isdisconnected = False

	def disconnect_once(self):
		"""Invoke disconnect on the first call of this method."""
		if not self.isdisconnected:
			self.disconnect()
			self.isdisconnected = True

	def presence_available(self, presence):
		"""Presence handler function for pyxmpp."""
		jid = presence.get_from_jid()
		if jid.bare() != self.target.bare():
			return
		if self.exclude_resources(jid.resource):
			return
		show = presence.get_show()
		if show is None:
			show = "online"
		if not self.include_states(show):
			return
		self.stream.send(self.message)
		self.failure = None
		self.disconnect_once()

	def session_started(self):
		"""pyxmpp API method"""
		self.stream.set_presence_handler("available", self.presence_available)
		self.request_roster()
		self.stream.send(pyxmpp.presence.Presence())

	def roster_updated(self, item=None):
		"""pyxmpp API method"""
		if item is not None:
			return
		try:
			self.roster.get_item_by_jid(self.target)
		except KeyError:
			self.failure = pynotifyd.PyNotifyDPermanentError(
					"contact is not my roster")
			# not on roster
			self.disconnect_once()

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

def make_set(value):
	if isinstance(value, list):
		pass # ok
	elif isinstance(value, str):
		value = map(str.strip, value.split(","))
	else:
		raise ValueError("invalid value type")
	return set(value)

__all__.append("ProviderJabber")
class ProviderJabber(pynotifyd.providers.ProviderBase):
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
		client = SendJabberClient(self.jid, self.password, jid, message,
				exclude_resources.__contains__, include_states.__contains__)
		client.connect()
		client.loop_timeout(self.timeout)
		client.disconnect_once()
		if client.failure:
			raise client.failure

