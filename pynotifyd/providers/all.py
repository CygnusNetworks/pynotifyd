#!/usr/bin/env python
# -*- coding: utf-8 -*-

provider_drivers = {}
provider_errors = {}

try:
	import developergarden
	provider_drivers["developergarden"] = developergarden.ProviderDevelopergarden
except Exception, msg:
	provider_errors["developergarden"] = msg

try:
	import sipgate
	provider_drivers["sipgate"] = sipgate.ProviderSipgate
except Exception, msg:
	provider_errors["sipgate"] = msg

try:
	import smstrade
	provider_drivers["smstrade"] = smstrade.ProviderSmstrade
except Exception, msg:
	provider_errors["smstrade"] = msg

try:
	import shell
	provider_drivers["shell"] = shell.ProviderShell
except Exception, msg:
	provider_errors["shell"] = msg

try:
	import mock
	provider_drivers["mock"] = mock.ProviderMock
except Exception, msg:
	provider_errors["mock"] = msg

try:
	import jabber
	provider_drivers["jabber"] = jabber.ProviderJabber
except Exception, msg:
	provider_errors["jabber"] = msg

try:
	import mail
	provider_drivers["mail"] = mail.ProviderMail
except Exception, msg:
	provider_errors["mail"] = msg

try:
	import persistentjabber
	provider_drivers["persistentjabber"] = persistentjabber.ProviderPersistentJabber
except Exception, msg:
	provider_errors["persistentjabber"] = msg
