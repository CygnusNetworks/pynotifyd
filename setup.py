#!/usr/bin/python

import distutils.core

distutils.core.setup(name='pynotifyd',
	version='0.8.10',
	description="Python Notification Daemon",
	long_description="The daemon allows you to send a message to a contact via jabber, email or sms whatever fits best. It is intended for use with Nagios.",
	author='Helmut Grohne',
	author_email='h.grohne@cygnusnetworks.de',
	maintainer='Torge Szczepanek',
	maintainer_email='debian@cygnusnetworks.de',
	license='GNU GPLv3', 
	packages=['pynotifyd', "pynotifyd.providers"],
	scripts=['pynotifyd_client', 'pynotifydaemon', 'developergarden_ctl'],
	classifiers=[
		"Development Status :: 4 - Beta",
		"Intended Audience :: System Administrators",
		"Programming Language :: Python",
		]
	)

