#pynotifyd

Python Notification Daemon for Nagios Notifications through Jabber/XMPP and SMS Providers

##Introduction
pynotifyd comes as a library, a daemon and a client. To be used it requires configobj, pyxmpp, pyinotify and some json implementation.

Both the client and the daemon share a configuration file. It contains a queue directory which must be writable to the client. The client enqueues a message by adding a file to the queue directory. The daemon notices the file (using inotify) and starts processing the message. It tries different providers and waits some time according to a retry logic defined in the configuration file.

Most of the code is to be found in the library part, so you can base different applications on this library or use just part of the functionality (such as talking to a specific sms provider). Specifically the configuration of providers is documented in the Python doc strings of the providers respectively. The repository also includes an example configuration file with comments.

##Setting up
First of all install the library and the utilities in a way "pynotifyd_client --help" doesn't get you an exception. The default configuration location is /etc/pynotifyd.conf, if you deviate from this you need to patch the source or pass -c on every invocation.

Then edit your configuration file. In the spirit of Nagios every contact needs to be defined in the configuration file. Additionally every provider (for example developergarden (sms), sipgate(sms), jabber or email) needs to be configured. As mentioned above you should consult the doc strings of the python modules.

Messages can be enqueued all the time, once the daemon starts up it will start delivering them. The interface of pynotifyd_client is designed in a way the cooperates with Nagios.
