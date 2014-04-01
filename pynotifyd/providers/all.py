#!/usr/bin/env python
# -*- coding: utf-8 -*-

provider_drivers = {}
provider_errors = {}

try:
	from pynotifyd.providers.developergarden import ProviderDevelopergarden
	provider_drivers["developergarden"] = ProviderDevelopergarden
except Exception, msg:
	provider_errors["developergarden"] = msg

try:
	from pynotifyd.providers.sipgate import ProviderSipgate
	provider_drivers["sipgate"] = ProviderSipgate
except Exception, msg:
	provider_errors["sipgate"] = msg

try:
	from pynotifyd.providers.shell import ProviderShell
	provider_drivers["shell"] = ProviderShell
except Exception, msg:
	provider_errors["shell"] = msg

try:
	from pynotifyd.providers.mock import ProviderMock
	provider_drivers["mock"] = ProviderMock
except Exception, msg:
	provider_errors["mock"] = msg

try:
	from pynotifyd.providers.jabber import ProviderJabber
	provider_drivers["jabber"] = ProviderJabber
except Exception, msg:
	provider_errors["jabber"] = msg

try:
	from pynotifyd.providers.mail import ProviderMail
	provider_drivers["mail"] = ProviderMail
except Exception, msg:
	provider_errors["mail"] = msg

try:
	from pynotifyd.providers.persistentjabber import ProviderPersistentJabber
	provider_drivers["persistentjabber"] = ProviderPersistentJabber
except Exception, msg:
	provider_errors["persistentjabber"] = msg



