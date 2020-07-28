Production installation and Setup
=================================

Download and Install (All CKAN Versions)
----------------------------------------

.. note:: Starting from CKAN 2.2, if you installed CKAN via a
    `package install`_, the DataPusher has already been installed and deployed
    for you. You can skip directly to :doc:`ckan-config`.


This assumes you already have CKAN installed on this server in the default
location described in the CKAN install documentation
(``/usr/lib/ckan/default``).  If this is correct you should be able to run the
following commands directly, if not you will need to adapt the previous path to
your needs.

These instructions set up the |datapusher| webservice on uWSGI running on port
8800, but can easily be adapted to other WSGI servers like Gunicorn. You'll
probably need to set up Nginx as a reverse proxy in front of it and something like
Supervisor to keep the process up.

   .. parsed-literal::

	 # Install requirements for the DataPusher
	 sudo apt install python3-venv python3-dev build-essential
	 sudo apt-get install python-dev python-virtualenv build-essential libxslt1-dev libxml2-dev git libffi-dev

	 # Create a virtualenv for datapusher
     sudo python3 -m venv /usr/lib/ckan/datapusher

	 # Create a source directory and switch to it
	 sudo mkdir /usr/lib/ckan/datapusher/src
	 cd /usr/lib/ckan/datapusher/src

	 # Clone the source (this should target the latest tagged version)
	 sudo git clone -b |version| https://github.com/ckan/datapusher.git

	 # Install the DataPusher and its requirements
	 cd datapusher
	 sudo /usr/lib/ckan/datapusher/bin/pip install -r requirements.txt
	 sudo /usr/lib/ckan/datapusher/bin/python setup.py develop

     # Install uWSGI
     sudo /usr/lib/ckan/datapusher/bin/pip install uwsgi

At this point you can run DataPusher with the following command::

    /usr/lib/ckan/datapusher/bin/uwsgi -i /usr/lib/ckan/datapusher/src/datapusher/deployment/datapusher-uswgi.ini


.. note:: If you are installing the |datapusher| on a different location than
    the default one you need to adapt the relevant paths in the
    ``datapusher-uwsgi.ini`` to the ones you are using.

.. _package install: http://docs.ckan.org/en/latest/install-from-package.html
