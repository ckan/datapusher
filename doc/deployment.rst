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

These instructions set up the |datapusher| webservice on Apache running on port
8800.

   .. parsed-literal::

	 #install requirements for the DataPusher
	 sudo apt-get install python-dev python-virtualenv build-essential libxslt1-dev libxml2-dev git libffi-dev

	 #create a virtualenv for datapusher
	 sudo virtualenv /usr/lib/ckan/datapusher

	 #create a source directory and switch to it
	 sudo mkdir /usr/lib/ckan/datapusher/src
	 cd /usr/lib/ckan/datapusher/src

	 #clone the source (this should target the latest tagged version)
	 sudo git clone -b |version| https://github.com/ckan/datapusher.git

	 #install the DataPusher and its requirements
	 cd datapusher
	 sudo /usr/lib/ckan/datapusher/bin/pip install -r requirements.txt
	 sudo /usr/lib/ckan/datapusher/bin/python setup.py develop

	 #copy the standard Apache config file
	 # (use deployment/datapusher.apache2-4.conf if you are running under Apache 2.4)
	 sudo cp deployment/datapusher.conf /etc/apache2/sites-available/datapusher.conf

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

Deployment with Gunicorn
------------------------

The `wsgi.py` file provided lets you run datapusher with gunicorn if required.
You will need to run gunicorn under supervisor and configure Nginx or Apache to
proxy requests to gunicorn.


   .. parsed-literal::

    #install requirements for the DataPusher
    sudo apt-get install python-dev python-virtualenv build-essential libxslt1-dev libxml2-dev git

    #create a virtualenv for datapusher
    sudo virtualenv /usr/lib/ckan/datapusher

    #create a source directory and switch to it
    sudo mkdir /usr/lib/ckan/datapusher/src
    cd /usr/lib/ckan/datapusher/src

    #clone the source (this should target the latest tagged version)
    sudo git clone -b |version| https://github.com/ckan/datapusher.git

    #install the DataPusher and its requirements
    cd datapusher
    sudo /usr/lib/ckan/datapusher/bin/pip install -r requirements.txt
    sudo /usr/lib/ckan/datapusher/bin/python setup.py develop

    #install gunicorn
    pip install gunicorn

    #run datapusher with gunicorn
    JOB_CONFIG='/usr/lib/ckan/datapusher/src/datapusher/deployment/datapusher_settings.py' gunicorn -b 127.0.0.1:8800 wsgi:app

.. _package install: http://docs.ckan.org/en/latest/install-from-package.html
