#!/usr/bin/env python
# -*- coding: utf-8 -*-


class PyNotifyDError(Exception):
	"""Base class for PyNotifyD Exceptions."""
	pass


class PyNotifyDPermanentError(PyNotifyDError):
	"""This exception indicates a problem that cannot be solved by
	simply trying again later."""
	pass


class PyNotifyDConfigurationError(PyNotifyDPermanentError):
	"""This exception indicates a problem with the configuration file."""
	pass


class PyNotifyDTemporaryError(PyNotifyDError):
	"""This exception indicates a temporary problem with the provider."""
	pass