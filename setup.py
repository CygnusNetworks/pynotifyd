#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

from pynotifyd import __version__

setup(name='pynotifyd',
	version=__version__,
	description="Python Notification Daemon",
	long_description="The daemon allows you to send a message to a contact via jabber, email or sms whatever fits best. It is intended for use with Nagios.",
	author='Helmut Grohne, Torge Szczepanek',
	author_email='debian@cygnusnetworks.de',
	maintainer='Torge Szczepanek',
	maintainer_email='debian@cygnusnetworks.de',
	license='GNU GPLv3',
	packages=['pynotifyd', "pynotifyd.providers"],
	scripts=['pynotifyd_client', 'pynotifydaemon', 'developergarden_ctl'],
	classifiers=[
		"Development Status :: 4 - Beta",
		"Intended Audience :: System Administrators",
		"Programming Language :: Python",
		"License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
		],  # see: https://pypi.python.org/pypi?%3Aaction=list_classifiers
	platforms='any',
	install_requires=["configobj", "pyinotify", "setproctitle", "pyxmpp", "gsmsapi", "phonenumbers"],
	)
