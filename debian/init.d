#!/bin/sh
### BEGIN INIT INFO
# Provides:          pynotifyd
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Python Notification Daemon
# Description:       The daemon allows you to send a message to a contact via
#                    jabber, email or sms whatever fits best. It is intended for
#                    use with Nagios.
#
### END INIT INFO

# Author: Helmut Grohne <h.grohne@cygnusnetworks.de>
#
# Do NOT "set -e"

# PATH should only include /usr/* if it runs after the mountnfs.sh script
# added /usr/local since the daemon is likely to invoke user defined commands
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/usr/sbin:/bin:/usr/bin
DESC="Python Notification Daemon"
NAME=pynotifyd
PACKAGE=python-$NAME
DAEMON=/usr/bin/pynotifydaemon
DAEMON_ARGS=
PIDFILE=/var/run/$NAME.pid
SCRIPTNAME=/etc/init.d/$PACKAGE
PYNOTIFYD_CONFIG=/etc/pynotifyd.conf

# Exit if the package is not installed
[ -x "$DAEMON" ] || exit 0

# Read configuration variable file if it is present
[ -r /etc/default/$PACKAGE ] && . /etc/default/$PACKAGE

test -f "$PYNOTIFYD_CONFIG" || exit 0

# Load the VERBOSE setting and other rcS variables
. /lib/init/vars.sh

# Define LSB log_* functions.
# Depend on lsb-base (>= 3.0-6) to ensure that this file is present.
. /lib/lsb/init-functions


get_queuedir()
{
	$DAEMON --queuedir-print
}

do_status()
{
	local queuedir pid
	queuedir=`get_queuedir`
	# test -d "" fails, so failure in get_queuedir is covered as well
	test -d "$queuedir" || return 4 # cannot determine status
	pid=`readlink "$queuedir/.lock"`
	test -z "$pid" && return 3 # lockfile absent -> program not running
	ps "$pid" >/dev/null 2>&1 || return 2 # dead, but lockfile exists
	return 0
}

#
# Function that starts the daemon/service
#
do_start()
{
	# Return
	#   0 if daemon has been started
	#   1 if daemon was already running
	#   2 if daemon could not be started
	do_status && return 1

	$DAEMON -c "$PYNOTIFYD_CONFIG" $DAEMON_ARGS
	test "$?" = 0 && return 0
	return 2
}

#
# Function that stops the daemon/service
#
do_stop()
{
	# Return
	#   0 if daemon has been stopped
	#   1 if daemon was already stopped
	#   2 if daemon could not be stopped
	#   other if a failure occurred
	local queuedir pid
	queuedir=`get_queuedir`
	test -z "$queuedir" && return 3
	pid=`readlink "$queuedir/.lock"`
	test -z "$pid" && return 1
	ps "$pid" >/dev/null 2>&1 || return 1
	kill -TERM "$pid" || return 2
	for w in 0.5 0.5 1 1 1 1 1 1 1 1 1; do
		sleep $w
		ps "$pid" >/dev/null 2>&1 || return 0
	done
	kill -KILL "$pid"
	for w in 0.5 0.5 1 1; do
		sleep $w
		ps "$pid" >/dev/null 2>&1 || return 0
	done
	return 2
}

case "$1" in
  status)
	do_status
	RETCODE=$?
	case $RETCODE in
		0) echo " alive" ;;
		1) echo " dead" ;;
	esac
	exit $RETCODE
	;;
  start)
	log_daemon_msg "Starting $DESC" "$NAME"
	do_start
	case "$?" in
		0|1) log_end_msg 0 ;;
		2) log_end_msg 1 ;;
	esac
	;;
  stop)
	log_daemon_msg "Stopping $DESC" "$NAME"
	do_stop
	case "$?" in
		0|1) log_end_msg 0 ;;
		2) log_end_msg 1 ;;
	esac
	;;
  restart|force-reload)
	log_daemon_msg "Restarting $DESC" "$NAME"
	do_stop
	case "$?" in
	  0|1)
		do_start
		case "$?" in
			0) log_end_msg 0 ;;
			1) log_end_msg 1 ;; # Old process is still running
			*) log_end_msg 1 ;; # Failed to start
		esac
		;;
	  *)
	  	# Failed to stop
		log_end_msg 1
		;;
	esac
	;;
  *)
	echo "Usage: $SCRIPTNAME {status|start|stop|restart|force-reload}" >&2
	exit 3
	;;
esac

:
