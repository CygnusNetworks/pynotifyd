pynotifyd
=========

configuration
-------------

The configuration is interpolated twice. Once at load time and a second time at
runtime for each delivery. The load-time interpolation expands `$variables`.
Some variables like `$hostname` are globally predefined. Configuration keys can
be used as variables in the same section as well. Here is an example employing
two variables::

   [example]
   key1 = value1
   key2 = $hostname:$key1

Subsections of the ``providers`` section are interpolated a second time for
each delivery. This time the interpolation syntax is the pythonic `%(variable)`
The variable ``message`` contains the message to be delivered. Additionally all
keys from the destination contact are available as ``contact:keynane``. Here is
an example for delivering messages to unix users using the ``write`` command::

   [contacts]
   [[example]]
   unixuser = example
   [providers]
   [example]
   driver = shell
   message_on_stdin = yes
   command = write %(contact:unixuser)

plugins
-------

jabber
~~~~~~

When using the ``jabber`` driver for a provider you need to set up additional
configuration, to tell the driver how and where to connect to. The ``jid`` key
defines the server, account and resource to use. It must be formatted like
``account@server/resource``. The ``password`` key needs to contain the plain
text password for the account. The ``timeout`` variable specifies the maximum
time in seconds to wait for a user to be online after connecting. Each delivery
attempt will take at most this many seconds. If you are processing many
deliveries, you should lower this value or switch to the ``persistentjabber``
driver.

Each contact wishing to use this driver must defined the ``jabber`` key to be a
jabber account excluding resource. It must be formatted like ``account@server``.
In addition you need to ensure that the contacts are on the provider's roster.

persistentjabber
~~~~~~~~~~~~~~~~

The ``persistentjabber`` driver uses the very same configuration keys as the
``jabber`` driver with the exception of the ``timeout`` key. This applies to
both the ``driver`` section and the ``contact`` section. The timeout is not
used, because the state of contacts is continuously tracked.

When configuring an ejabberd server, you need to enable the mod_ping plugin.
