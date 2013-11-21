======================
Installation and Setup
======================

Download and Install (All Version)
----------------------------------

This assumes you already have CKAN installed on this server in the same location as the docs mention or via a package install.  If this is correct you should be able to run the following as is::

    #go to the ckan source directory
    cd /usr/lib/ckan/default/src

    #clone the source
    sudo git clone https://github.com/okfn/datapusher.git

    #install the datapussher
    cd datapusher
    sudo /usr/lib/ckan/default/bin/python setup.py develop

    #copy the standard apache config file
    sudo cp deployment/datapusher /etc/apache2/sites-available/

    #copy the standard datapusher wsgi file
    sudo cp deployment/datapusher.wsgi /etc/ckan/

    #copy the standard datapusher settings.
    sudo cp deployment/datapusher_settings /etc/ckan/

    #open up port 8800 on apache where the datapusher accepts connections.
    sudo sh -c 'echo "NameVirtualHost *:8800" >> /etc/apache2/ports.conf'
    sudo sh -c 'echo "Listen 8800" >> /etc/apache2/ports.conf'

    #enable datapusher apache
    sudo a2ensite datapusher

Instructions for CKAN 2.1 users
-------------------------------

These commands should also be run if using CKAN 2.1::

    #go to the ckan source directory
    cd /usr/lib/ckan/default/src
    #clone the datapusher CKAN extension
    sudo git clone https://github.com/okfn/ckanext-datapusherext.git
    #install datapusherext
    cd ckanext-datapusherext
    sudo /usr/lib/ckan/default/bin/python setup.py develop


Add ``datapusherext`` to the plugins line in ``/etc/ckan/default/production.ini``

Restart apache::  

   sudo service apache2 restart

Instructions for CKAN 2.2 users
-------------------------------

Add ``datapusher`` to the plugins line in ``/etc/ckan/default/production.ini``

Restart apache::  

   sudo service apache2 restart


Test the configuration
----------------------

To test if it is datapusher service is working or not run::

    curl 0.0.0.0:8800

The result should look something like::

   {
   "help": "\n        Get help at:\n        http://ckan-service-provider.readthedocs.org/."
   }

Error and logs
--------------

If there are issues you should look in ``/var/log/apache2/datapusher.error.log``.  All log output will be put in there.



