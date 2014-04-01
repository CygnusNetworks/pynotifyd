#!/usr/bin/env python
# -*- coding: utf-8 -*-

import smtplib
import email.mime.text
import pynotifyd
import pynotifyd.providers


class ProviderMail(pynotifyd.providers.ProviderBase):
	"""Send message via email.

	Required configuration options:
		- from: The sender email address.

	Optional configuration options:
		- subject: The subject of the message. Default: "PyNotifyD Message".
		- body: A template to use for the message body. The string "MESSAGE"
			gets replace with the actual message.
		- forceto: Instead of using the email option from the contact use
			value as recipient for all messages.

	Required contact configuration options:
		- email: recipient email address. (Optional if forceto is given.)
	"""
	def __init__(self, config):
		self.subject = config.get("subject", "PyNotifyD Message")
		self.body = config.get("body", "MESSAGE")
		try:
			self.from_ = config["from"]
		except KeyError:
			raise pynotifyd.PyNotifyDConfigurationError("from address required")
		self.forceto = config.get("forceto")

	def sendmessage(self, recipient, message):
		if self.forceto is None:
			try:
				mailto = recipient["email"]
			except KeyError:
				raise pynotifyd.PyNotifyDConfigurationError(
						"email address required")
		else:
			mailto = self.forceto
		mail = email.mime.text.MIMEText(self.body.replace("MESSAGE", message))
		mail["From"] = self.from_
		mail["Subject"] = self.subject
		mail["To"] = mailto
		try:
			server = smtplib.SMTP()
			server.connect()
			server.sendmail(self.from_, [mailto], mail.as_string())
			server.quit()
		except smtplib.SMTPException, exc:
			raise pynotifyd.PyNotifyDTemporaryError(
					"SMTPException received: %s" % str(exc))
