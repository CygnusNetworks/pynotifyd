from __future__ import with_statement
import contextlib
import httplib
import urllib
import pynotifyd
import pynotifyd.providers

# Welcome to the json hell in Python. We have to support no less than three
# different json libraries!
#  * cjson.
#    + Works.
#    + Throws one exception for everything.
#    + Fast.
#    - C-Extension.
#  * json from Python2.6
#    + Standard library.
#    - Also throws RuntimeError
#  * json from http://sf.net/projects/json-py
#    + Plain Python module for 2.5.
#    - Uses same name as 2.6 module.
#    - Uses different names than 2.6 module. Yeah!
#    - Not only throws RuntimeError but also StopIteration.
#
# Module     | parse  | Exception
# -----------+--------+----------
# cjson      | decode | DecodeError
# json (2.6) | loads  | ValueError
# json (2.5) | read   | ReadException

try:
	import cjson
	json_exception = cjson.DecodeError
	decode_json = cjson.decode
except ImportError:
	import json
	try: # Python2.6 standard library
		json.loads # pylint: disable=W0104
		json_exception = ValueError
		def decode_json(string):
			try:
				return json.loads(string)
			except RuntimeError: # try json.loads(500*"[")
				raise json_exception("recursion depth exceeded")

	except AttributeError: # py2.5 json-py
		json_exception = json.ReadException
		def decode_json(string):
			try:
				return json.read(string)
			except StopIteration: # Why the fuck is this thrown???
				raise json_exception("StopIteration")
			except RuntimeError: # try json.loads(500*"[")
				raise json_exception("recursion depth exceeded")

__all__ = []

__all__.append("ProviderDevelopergarden")
class ProviderDevelopergarden(pynotifyd.providers.SMSProviderBase):
	"""Send sms via http://www.developergarden.com using the rest
	interface.

	Required configuration options:
		- username
		- password

	Optional configuration options:
		- suite: one out of production, mock or sandbox.
		- sender: a phone number used for sending. It must be validated
			by the Developergarden service.

	See also L{SMSProviderBase}.
	"""
	# The following values are taken from 
	# http://www.developergarden.com/openapi/dokumentation/
	# http://www.developergarden.com/c/document_library/get_file?uuid=e089d8b5-7baf-4d34-81f3-40625b6f2553&groupId=18925
	tokenserver = "sts.idm.telekom.com" # page 146
	tokenpath = "/rest-v1/tokens/odg" # page 147
	smsserver = "gateway.developer.telekom.com" # page 82
	smspathtemplate = "/p3gw-mod-odg-sms/rest/%s/sms" # page 82
	validationsmspathtemplate = \
			"/p3gw-mod-odg-sms-validation/rest/%s/send" # page 89
	validatepathmplate = \
			"/p3gw-mod-odg-sms-validation/rest/%s/validatednumbers/%s" # page 91
	getbalancetemplate = \
			"/p3gw-mod-odg-admin/rest/%s/account/balance" # page 109
	maxsmslength = 765 # page 81
	maxreplysize = 65536

	def __init__(self, config):
		"""
		@type config: dict-like
		@param config: required keys are username and password.
		@raises PyNotifyDConfigurationError:
		"""
		pynotifyd.providers.SMSProviderBase.__init__(self, config)
		try:
			self.username = config["username"]
			self.password = config["password"]
		except KeyError:
			raise pynotifyd.PyNotifyDConfigurationError(
					"username and password required")
		suite = config.get("suite", "production")
		if suite not in ("production", "mock", "sandbox"):
			raise pynotifyd.PyNotifyDConfigurationError("invalid suite")
		self.suite = suite
		self.sender = config.get("sender")

	def make_rest_request(self, server, method, path, headers, body):
		"""
		@type server: str
		@type method: str
		@type path: str
		@type headers: {str: str}
		@type body: None or str
		@rtype: (int, {str: str})
		@returns: (http_status, rest)
		@raises PyNotifyDTemporaryError:
		"""
		realheaders = {"Accept": "text/plain", "Accept-Charset": "UTF-8"}
		realheaders.update(headers)
		try:
			with contextlib.closing(httplib.HTTPSConnection(server)) \
					as connection:
				connection.request(method, path, body, realheaders)
				response = connection.getresponse()
				data = response.read(self.maxreplysize+1)
			if len(data) > self.maxreplysize:
				raise pynotifyd.PyNotifyDTemporaryError(
						"Response from Developergarden server %s is too long" %
						server)
			ctype = response.msg.getheader("Content-Type")
			if ctype is None:
				raise pynotifyd.PyNotifyDTemporaryError(
						("Response from Developergarden server %s does not " +
							"contain a Content-Type") % server)

			ctype = ctype.split(";", 1)[0] # remove subtypes

			if ctype == "text/plain":
				answer = {}
				for line in data.splitlines():
					if '=' not in line:
						raise pynotifyd.PyNotifyDTemporaryError(
								"Invalid response from Developergarden: " +
								"non-assignment line")
					key, value = line.split('=', 1)
					answer[key] = value
			elif ctype == "application/json":
				try:
					answer = decode_json(data)
				except json_exception, err:
					raise pynotifyd.PyNotifyDTemporaryError(
							"received invalid json from Developergarden " +
							"server %s: %s" % (server, str(err)))
				if not isinstance(answer, dict):
					raise pynotifyd.PyNotifyDTemporaryError(
							"received non-dict json response from " +
							"Developergarden server %s" % server)
			else:
				raise pynotifyd.PyNotifyDTemporaryError(
						("Received unknown Content-Type %r from " +
							"Developergarden server %s") % (ctype, server))

			return (response.status, answer)
		except httplib.HTTPException, exc:
			raise pynotifyd.PyNotifyDTemporaryError("Received HTTPException " +
					"during request to Developergarden server %s: %s" %
					(server, str(exc)))

	def get_token(self):
		"""
		@rtype: str
		@raises PyNotifyDTemporaryError:
		"""
		creds = "%s:%s" % (self.username, self.password)
		creds = creds.encode("base64")
		headers = dict(Authorization="Basic %s" % creds)
		status, answer = self.make_rest_request(self.tokenserver, "GET",
				self.tokenpath, headers, None)
		if status != 200:
			raise pynotifyd.PyNotifyDTemporaryError(
					"HTTP status from Developergarden token server is %d" %
					status)
		if answer.get("tokenFormat") != "CompactToken":
			raise pynotifyd.PyNotifyDTemporaryError(
					"Received unknown token format from Developergarden")
		if answer.get("tokenEncoding") != "text/base64":
			raise pynotifyd.PyNotifyDTemporaryError(
					"Received unknown token encoding from Developergarden")
		if "token" not in answer:
			raise pynotifyd.PyNotifyDTemporaryError(
					"Received no token from Developergarden")
		return answer["token"]

	def make_authorized_rest_request(self, path, token, params):
		"""
		@type path: str
		@type token: str
		@type params: {str: str}
		@rtype: (int, {str: str})
		@returns: (http_status, rest)
		@raises PyNotifyDTemporaryError:
		"""
		headers = {
				"Authorization": 'TAuth realm="https://odg.t-online.de",' +
					'tauth_token="%s"' % token,
				"Content-Type": "application/x-www-form-urlencoded"}
		status, answer = self.make_rest_request(self.smsserver, "POST", path,
				headers, urllib.urlencode(params))
		if "status.statusMessage" not in answer or \
				not answer.get("status.statusCode", "nondigit").isdigit():
			if status != 200:
				raise pynotifyd.PyNotifyDTemporaryError(
						"HTTP status from Developergarden sms server is %d" %
						status)
			raise pynotifyd.PyNotifyDTemporaryError("Invalid response from " +
					"Developergarden: mandatory fields missing")
		answerstatus = int(answer["status.statusCode"])
		if status != 200 or answerstatus != 0:
			raise pynotifyd.PyNotifyDTemporaryError(
					"Error %d from Developergarden: %s" %
					(answerstatus, repr(answer["status.statusMessage"])))
		return (status, answer)

	def initiate_send(self, token, phone, message):
		"""
		@type token: str
		@type phone: str
		@type message: str
		@raises PyNotifyDTemporaryError:
		"""
		params = dict(number=phone, message=message)
		if self.sender is not None:
			params["originator"] = self.sender
		self.make_authorized_rest_request(self.smspathtemplate % self.suite,
				token, params)

	def request_validation_sms(self, token, phone):
		"""
		@type token: str
		@type phone: str
		@raises PyNotifyDTemporaryError:
		"""
		self.make_authorized_rest_request(
				self.validationsmspathtemplate % self.suite, token,
				dict(number=phone))

	def enter_validation_code(self, token, phone, code):
		"""
		@type token: str
		@type phone: str
		@type code: str
		@raises PyNotifyDTemporaryError:
		"""
		if not phone.startswith("+49"):
			raise pynotifyd.PyNotifyDPermanentError(
					"cannot handle numbers outside Germany")
		phone = "0" + phone[3:]
		self.make_authorized_rest_request(
				self.validatepathmplate % (self.suite, phone), token,
				dict(key=code))

	def get_balance(self, token):
		"""
		@type token: str
		@rtype: [{"account": int, "credits": int}]
		@raises PyNotifyDTemporaryError:
		"""
		status, answer = self.make_authorized_rest_request(
				self.getbalancetemplate % self.suite, token, {})
		results = {}
		for key, value in answer.items():
			parts = key.split('.')
			if parts.pop(0) != "accounts":
				continue
			if len(parts) < 2:
				continue
			field = parts.pop()
			if field not in ("account", "credits"):
				continue
			result = results.setdefault(".".join(parts), {})
			if not value.isdigit():
				raise pynotifyd.PyNotifyDTemporaryError(
						"received non-number for credits or account id")
			result[field] = int(value)
		return [result for result in results.values()
				if len(result.keys()) == 2]

	def sendsms(self, phone, message):
		token = self.get_token()
		self.initiate_send(token, phone, message)
