#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configobj
import email.utils
import socket
import validate

HAS_PHONENUMBERS=False
try:
	import phonenumbers
	HAS_PHONENUMBERS=True
except ImportError:
	pass

import errors

config_spec = configobj.ConfigObj("""
[general]
queuedir = string(min=1)
retry = list(min=1)

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
	# Basic constraint checking on phone number, if phonenumbers is not used
	for number in get_the_item(contact, "number"):
		if not HAS_PHONENUMBERS:
			if not number.startswith("+"):
				raise errors.PyNotifyDConfigurationError("phone number must start with a plus sign")
			if not number[1:].isdigit():
				raise errors.PyNotifyDConfigurationError("non-digits found in phone number")
		else:
			try:
				# TODO: add region support
				_ = phonenumbers.parse(number, None)
			except Exception, msg:
				raise errors.PyNotifyDConfigurationError("phonenumber cannot be parsed with exception %s" % msg)

	for jabber in get_the_item(contact, "jabber"):
		if '@' not in jabber:
			raise errors.PyNotifyDConfigurationError("a jabberid has to contain an @ sign")

	for addr in get_the_item(contact, "email"):
		if len(email.utils.parseaddr(addr)[1])==0:
			raise errors.PyNotifyDConfigurationError("email address %s is invalid in contact %s" % (addr, contact))


def read_config(filename):
	"""
	@type filename: str
	@rtype: configobj.ConfigObj
	@raises PyNotifyDConfigurationError:
	"""
	spec = config_spec.copy()
	spec["hostname"] = "string(default=%r)" % socket.getfqdn()
	try:
		config = configobj.ConfigObj(filename, interpolation="template", configspec=spec, file_error=True)
	except IOError, msg:
		raise errors.PyNotifyDConfigurationError("Failed to read configuration file named %r with IOError: %s" % (filename, msg))
	except OSError, msg:
		raise errors.PyNotifyDConfigurationError("Failed to read configuration file named %r with OSError: %s" % (filename, msg))

	# general verification
	for section_list, key, error in configobj.flatten_errors(config, config.validate(validate.Validator())):
		raise errors.PyNotifyDConfigurationError("Failed to validate %s in section %s with error %s" % (key, ", ".join(section_list), error))

	# check contacts
	for contactname, contact in config["contacts"].items():
		if not isinstance(contact, dict):
			raise errors.PyNotifyDConfigurationError("non-section found in section contacts")
		try:
			validate_contact(contact)
		except errors.PyNotifyDConfigurationError, err:
			raise errors.PyNotifyDConfigurationError("%s in contact %s" % (err.message, contactname))

	# check retry logic
	for provider in config["general"]["retry"]:
		if provider.isdigit() or provider == "GIVEUP":
			continue
		if provider in config["providers"]:
			continue
		raise errors.PyNotifyDConfigurationError("provider %s not found" % provider)
	return config
