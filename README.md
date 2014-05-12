[![Build Status](https://travis-ci.org/CygnusNetworks/pynotifyd.svg?branch=master)](https://travis-ci.org/CygnusNetworks/pynotifyd)

#pynotifyd

Notification Daemon for Notifications through various plugins (common plugins are Jabber/XMPP instant messaging and Mobile Short Messages (SMS) providers using a Web API).

Pynotifyd is providing a solution for sending Notifications to users 

by Instant Messaging (Jabber/XMPP) and depending on their Online Status to mobile phone numbers by short message, if the user is offline or the Online status (for example away) is not matching a defined criteria. Plugins exist for Jabber/XMPP and some SMS providers (Sipgate, T-Mobile Developergarden). Other handlers can be easily added by implementing a plugin or calling a shell command.

##Introduction
pynotifyd comes as a library, a daemon and a client. It requires at least Python 2.6 and the following Python modules:

* configobj

For Jabber/XMPP you will need:

* pyxmpp
* libxml2

For SMS Support for Sipgate and SMSTrade you will need:

* gsmsapi - see https://github.com/CygnusNetworks/python-gsmsapi

For notifications of new queue files (inotify) you should consider installing pyinotify. Otherwise a signal handler is used.

Both the client and the daemon share a configuration file. It contains a queue directory which must be writable to the client and must not contain any other files. 
The client enqueues a message by adding a file to the queue directory. The daemon notices the file (using inotify) and starts processing the message. It tries different providers and waits some time according to a retry logic defined in the configuration file.

Most of the code is to be found in the library part, so you can base different applications on this library or use just part of the functionality (such as talking to a specific sms provider). Specifically the configuration of providers is documented in the Python doc strings of the providers respectively. The repository also includes an example configuration file with comments.

##Setting up
First of all install the library and the other python modules in a way "pynotifyd_client --help" doesn't get you an exception. The default configuration location is /etc/pynotifyd.conf, if you deviate from this you need to pass -c on every invocation.

Then edit your configuration file. In the spirit of Nagios every contact needs to be defined in the configuration file. Additionally every provider (for example developergarden (sms), sipgate(sms), jabber or email) needs to be configured. As mentioned above you should consult the doc strings of the python modules.

Messages can be enqueued all the time, once the daemon starts up it will start delivering them. The interface of pynotifyd_client is designed in a way it works well with Nagios, but could also be used for other purposes.

##Example configfile

See provided pynotifyd.conf for a example /etc/pynotifyd.conf.

##Example Nagios command Configuration
```
define command{
        command_name    notify-service-by-pynotify
        command_line    /usr/bin/pynotifyd_client $CONTACTPAGER$ "Service: $SERVICEDESC$ Host: $HOSTNAME$ Address: $HOSTADDRESS$ State: $SERVICESTATE$ Info: $SERVICEOUTPUT$ Date: $LONGDATETIME$"
        }

define command{
        command_name    notify-host-by-pynotify
        command_line    /usr/bin/pynotifyd_client $CONTACTPAGER$ "Host $HOSTALIAS$ is $HOSTSTATE$ Info: $HOSTOUTPUT$ Time: $LONGDATETIME$"
        }
```
##Example Nagios Contact Configuration
```
define contact{
        contact_name                    username-pager
        alias                           Full Username
        service_notification_period     24x7
        host_notification_period        24x7
        service_notification_options    w,c,r
        host_notification_options       d,r
        service_notification_commands   notify-service-by-pynotify
        host_notification_commands      notify-host-by-pynotify
        pager                           username  # this is the named defined in contacts section of pynotifyd.conf 
        }
```



