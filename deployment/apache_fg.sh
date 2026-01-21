#!/bin/bash

# started from
# http://linoxide.com/linux-how-to/configure-apache-containers-docker-fedora-22/

#set variables
export APACHE_LOG_DIR="/var/log/httpd"
export APACHE_LOCK_DIR="/var/lock/httpd"
export APACHE_RUN_USER="www-data"
export APACHE_RUN_GROUP="www-data"
export APACHE_PID_FILE="/var/run/httpd/httpd.pid"
export APACHE_RUN_DIR="/var/run/httpd"

#create directories if necessary
if ! [ -d /var/run/httpd ]; then mkdir /var/run/httpd;fi
if ! [ -d /var/log/httpd ]; then mkdir /var/log/httpd;fi
if ! [ -d /var/lock/httpd ]; then mkdir /var/lock/httpd;fi

#run Apache
apache2 -X