#!/usr/bin/env python
# -*- coding: utf-8 -*-

provider_drivers = {}
provider_errors = {}

try:
	import pynotifyd.providers.developergarden
	provider_drivers["developergarden"] = pynotifyd.providers.developergarden.ProviderDevelopergarden
except Exception, msg:
	provider_errors["developergarden"] = msg

try:
	import pynotifyd.providers.sipgate
	provider_drivers["sipgate"] = pynotifyd.providers.sipgate.ProviderSipgate
except Exception, msg:
	provider_errors["sipgate"] = msg

try:
	import pynotifyd.providers.shell
	provider_drivers["shell"] = pynotifyd.providers.shell.ProviderShell
except Exception, msg:
	provider_errors["shell"] = msg

try:
	import pynotifyd.providers.mock
	provider_drivers["mock"] = pynotifyd.providers.mock.ProviderMock
except Exception, msg:
	provider_errors["mock"] = msg

try:
	import pynotifyd.providers.jabber
	provider_drivers["jabber"] = pynotifyd.providers.jabber.ProviderJabber
except Exception, msg:
	provider_errors["jabber"] = msg

try:
	import pynotifyd.providers.mail
	provider_drivers["mail"] = pynotifyd.providers.mail.ProviderMail
except Exception, msg:
	provider_errors["mail"] = msg

try:
	import pynotifyd.providers.persistentjabber
	provider_drivers["persistentjabber"] = pynotifyd.providers.persistentjabber.ProviderPersistentJabber
except Exception, msg:
	provider_errors["persistentjabber"] = msg
