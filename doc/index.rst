=============================================================
|datapusher| - Automatically add Data to the CKAN |datastore|
=============================================================

This application is a service that adds automatic CSV/Excel file loading to
CKAN_.

You should have a CKAN instance with the |datastore| installed before using
this.  Head to the `CKAN documentation`_ for information on how to `install
CKAN`_ and set up the `DataStore`_.

Development installation
========================

Install the required packages::

    sudo apt-get install python-dev python-virtualenv build-essential libxslt1-dev libxml2-dev git

Get the code::

    git clone https://github.com/ckan/datapusher
    cd datapusher

Install the dependencies::

    pip install -r requirements.txt
    pip install -e .

Run the DataPusher::

    JOB_CONFIG='/home/foo/datapusher/deployment/datapusher_settings.py' python wsgi.py

.. note:: `JOB_CONFIG` environment variable needs the full path to datapusher.

By default DataPusher should be running at the following port:

    http://localhost:8800/

You can change the ``HOST``, ``PORT`` and ``DEBUG`` environment variables to
suit your needs.


Production installation and Setup
=================================

Download and Install (All CKAN Versions)
----------------------------------------

.. note:: Starting from CKAN 2.2, if you installed CKAN via a `package install`_,
    the DataPusher has already been installed and deployed for you. You can skip
    directly to `Configuration`_.


This assumes you already have CKAN installed on this server in the default location described in the CKAN install documentation (``/usr/lib/ckan/default``).
If this is correct you should be able to run the following commands directly, if not you will need to adapt the previous path to your needs.

These instructions set up the |datapusher| webservice on Apache running on port 8800.

::

    #install requirements for the DataPusher
    sudo apt-get install python-dev python-virtualenv build-essential libxslt1-dev libxml2-dev git

    #create a virtualenv for datapusher
    sudo virtualenv /usr/lib/ckan/datapusher

    #create a source directory and switch to it
    sudo mkdir /usr/lib/ckan/datapusher/src
    cd /usr/lib/ckan/datapusher/src

    #clone the source (always target the stable branch)
    sudo git clone -b stable https://github.com/ckan/datapusher.git

    #install the DataPusher and its requirements
    cd datapusher
    sudo /usr/lib/ckan/datapusher/bin/pip install -r requirements.txt
    sudo /usr/lib/ckan/datapusher/bin/python setup.py develop

    #copy the standard Apache config file
    sudo cp deployment/datapusher /etc/apache2/sites-available/

    #copy the standard DataPusher wsgi file
    #(see note below if you are not using the default CKAN install location)
    sudo cp deployment/datapusher.wsgi /etc/ckan/

    #copy the standard DataPusher settings.
    sudo cp deployment/datapusher_settings.py /etc/ckan/

    #open up port 8800 on Apache where the DataPusher accepts connections.
    #make sure you only run these 2 functions once otherwise you will need
    #to manually edit /etc/apache2/ports.conf.
    sudo sh -c 'echo "NameVirtualHost *:8800" >> /etc/apache2/ports.conf'
    sudo sh -c 'echo "Listen 8800" >> /etc/apache2/ports.conf'

    #enable DataPusher Apache site
    sudo a2ensite datapusher

.. note:: If you are installing the |datapusher| on a different location than
    the default one you need to adapt the following line in the
    ``datapusher.wsgi`` file to point to the virtualenv you are using::

        activate_this = os.path.join('/usr/lib/ckan/datapusher/bin/activate_this.py')


Configuration
-------------

In order to tell CKAN where this webservice is located, the following must be
added to the ``[app:main]`` section of your CKAN configuration file (generally
located at ``/etc/ckan/default/production.ini``)::

    ckan.datapusher.url = http://0.0.0.0:8800/

The DataPusher also requires the ``ckan.site_url`` configuration option to be
set on your configuration file::


    ckan.site_url = http://your.ckan.instance.com

CKAN 2.2 and above
++++++++++++++++++

If you are using at least CKAN 2.2, you just need to add ``datapusher`` to the
plugins in your CKAN configuration file::

    ckan.plugins = <other plugins> datapusher

Restart apache::

    sudo service apache2 restart

CKAN 2.1
++++++++

If you are using CKAN 2.1, the logic for interacting with the |datapusher| is
located in a separate extension, ckanext-datapusherext_.

To install it, follow the following steps ::

    #go to the ckan source directory
    cd /usr/lib/ckan/default/src

    #clone the DataPusher CKAN extension
    sudo git clone https://github.com/ckan/ckanext-datapusherext.git

    #install datapusherext
    cd ckanext-datapusherext
    sudo /usr/lib/ckan/default/bin/python setup.py develop


Add ``datapusherext`` to the plugins line in
``/etc/ckan/default/production.ini``::

    ckan.plugins = <other plugins> datapusherext

Restart apache::

   sudo service apache2 restart


Test the configuration
----------------------

To test if it is |datapusher| service is working or not run::

    curl 0.0.0.0:8800

The result should look something like::

    {
    "help": "\n        Get help at:\n        http://ckan-service-provider.readthedocs.org/."
    }

Error and logs
--------------

If there are any issues you should look in ``/var/log/apache2/datapusher.error.log``.
All log output will be put in there.

Using the |datapusher|
======================

The |datapusher| will work without any more configuration as long as the
``datapusher`` (or ``datapusherext`` for version 2.1) plugin is installed and
added to the ckan config file.

Any file that has a format of csv or xls will be attempted to be loaded
into to datastore.

CKAN 2.2 and above
------------------

When editing a resource in CKAN (clicking the "Manage" button on a resource
page), a new tab will appear named "Resource Data".
This will contain a log of the last attempted upload and an opportunity
to retry to upload.

.. image:: images/ui.png


CKAN 2.1
--------

If you want to retry an upload go into the resource edit form in CKAN and
just click the "Update" button to resubmit the resource metadata.
This will retrigger an upload.


License
=======

This material is copyright (c) Open Knowledge Foundation.

It is open and licensed under the GNU Affero General Public License (AGPL) v3.0
whose full text may be found at:

http://www.fsf.org/licensing/licenses/agpl-3.0.html

.. _CKAN: http://ckan.org
.. _CKAN Documentation: http://docs.ckan.org
.. _install CKAN: http://docs.ckan.org/en/latest/installing.html
.. _package install: http://docs.ckan.org/en/latest/install-from-package.html
.. _DataStore: http://docs.ckan.org/en/latest/datastore.html
.. _ckanext-datapusherext: https://github.com/ckan/ckanext-datapusherext
