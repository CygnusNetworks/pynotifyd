#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = []
provider_drivers = {}
provider_errors = {}

try:
	from pynotifyd.providers.developergarden import ProviderDevelopergarden
	__all__.append("ProviderDevelopergarden")
	provider_drivers["developergarden"] = ProviderDevelopergarden
except Exception, msg:
	provider_errors["developergarden"] = msg

try:
	from pynotifyd.providers.sipgate import ProviderSipgate
	__all__.append("ProviderSipgate")
	provider_drivers["sipgate"] = ProviderSipgate
except Exception, msg:
	provider_errors["sipgate"] = msg

try:
	from pynotifyd.providers.shell import ProviderShell
	__all__.append("ProviderShell")
	provider_drivers["shell"] = ProviderShell
except Exception, msg:
	provider_errors["shell"] = msg

try:
	from pynotifyd.providers.mock import ProviderMock
	__all__.append("ProviderMock")
	provider_drivers["mock"] = ProviderMock
except:
	pass

try:
	from pynotifyd.providers.jabber import ProviderJabber
	__all__.append("ProviderJabber")
	provider_drivers["jabber"] = ProviderJabber
except Exception, msg:
	provider_errors["jabber"] = msg

try:
	from pynotifyd.providers.mail import ProviderMail
	__all__.append("ProviderMail")
	provider_drivers["mail"] = ProviderMail
except Exception, msg:
	provider_errors["mail"] = msg

try:
	from pynotifyd.providers.persistentjabber import ProviderPersistentJabber
	__all__.append("ProviderPersistentJabber")
	provider_drivers["persistentjabber"] = ProviderPersistentJabber
except Exception, msg:
	provider_errors["persistentjabber"] = msg

__all__.append("provider_drivers")


