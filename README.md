[![Build Status](https://travis-ci.org/ckan/datapusher.png?branch=master)](https://travis-ci.org/ckan/datapusher)
[![Coverage Status](https://coveralls.io/repos/ckan/datapusher/badge.png?branch=master)](https://coveralls.io/r/ckan/datapusher?branch=master)
[![Latest Version](https://img.shields.io/pypi/v/datapusher.svg)](https://pypi.python.org/pypi/datapusher/)
[![Downloads](https://img.shields.io/pypi/dm/datapusher.svg)](https://pypi.python.org/pypi/datapusher/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/datapusher.svg)](https://pypi.python.org/pypi/datapusher/)
[![License](https://img.shields.io/badge/license-GPL-blue.svg)](https://pypi.python.org/pypi/datapusher/)

[PyPI]: https://pypi.python.org/pypi/datapusher
[DataStorer]: https://github.com/ckan/ckanext-datastorer
[DataPusher documentation]: https://docs.ckan.org/projects/datapusher/en/latest/
[CKAN Service Provider]: https://github.com/ckan/ckan-service-provider
[Messytables]: https://github.com/okfn/messytables


# DataPusher

DataPusher is a standalone web service that automatically downloads any tabular
data files like CSV or Excel from a CKAN site's resources when they are added to the
CKAN site, parses them to pull out the actual data, then uses the DataStore API
to push the data into the CKAN site's DataStore.

This makes the data from the resource files available via CKAN's DataStore API.
In particular, many of CKAN's data preview and visualization plugins will only
work (or will work much better) with files whose contents are in the DataStore.

To get it working you have to:

1. Deploy a DataPusher instance to a server (or use an existing DataPusher
   instance)
2. Enable and configure the `datastore` plugin on your CKAN site.
3. Enable and configure the `datapusher` plugin on your CKAN site.

Note that if you installed CKAN using the _package install_ option then a
DataPusher instance should be automatically installed and configured to work
with your CKAN site.

DataPusher is built using [CKAN Service Provider][] and [Messytables][].

The original author of DataPusher was
Dominik Moritz <dominik.moritz@okfn.org>. For the current list of contributors
see [github.com/ckan/datapusher/contributors](https://github.com/ckan/datapusher/contributors)

## Development installation

Install the required packages::

    sudo apt-get install python-dev python-virtualenv build-essential libxslt1-dev libxml2-dev zlib1g-dev git libffi-dev

Get the code::

    git clone https://github.com/ckan/datapusher
    cd datapusher

Install the dependencies::

    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    pip install -e .

Run the DataPusher::

    python datapusher/main.py deployment/datapusher_settings.py

By default DataPusher should be running at the following port:

    http://localhost:8800/

If you need to change the host or port, copy `deployment/datapusher_settings.py` to
`deployment/datapusher_local_settings.py` and modify the file to suit your needs.

To run the tests:

    nosetests

## Production deployment

*Note*: If you installed CKAN via a [package install](http://docs.ckan.org/en/latest/install-from-package.html), the DataPusher has already been installed and deployed for you. You can skip directly to the [Configuring](#configuring) section.


Thes instructions assume you already have CKAN installed on this server in the default
location described in the CKAN install documentation
(`/usr/lib/ckan/default`).  If this is correct you should be able to run the
following commands directly, if not you will need to adapt the previous path to
your needs.

These instructions set up the DataPusher web service on [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) running on port 8800, but can be easily adapted to other WSGI servers like Gunicorn. You'll
probably need to set up Nginx as a reverse proxy in front of it and something like
Supervisor to keep the process up.


	 # Install requirements for the DataPusher
	 sudo apt install python3-venv python3-dev build-essential
	 sudo apt-get install python-dev python-virtualenv build-essential libxslt1-dev libxml2-dev git libffi-dev

	 # Create a virtualenv for datapusher
     sudo python3 -m venv /usr/lib/ckan/datapusher

	 # Create a source directory and switch to it
	 sudo mkdir /usr/lib/ckan/datapusher/src
	 cd /usr/lib/ckan/datapusher/src

	 # Clone the source (you should target the latest tagged version)
	 sudo git clone -b 0.0.17 https://github.com/ckan/datapusher.git

	 # Install the DataPusher and its requirements
	 cd datapusher
	 sudo /usr/lib/ckan/datapusher/bin/pip install -r requirements.txt
	 sudo /usr/lib/ckan/datapusher/bin/python setup.py develop

     # Install uWSGI
     sudo /usr/lib/ckan/datapusher/bin/pip install uwsgi

At this point you can run DataPusher with the following command:

    /usr/lib/ckan/datapusher/bin/uwsgi -i /usr/lib/ckan/datapusher/src/datapusher/deployment/datapusher-uswgi.ini


*Note*: If you are installing the DataPusher on a different location than the defaul
one you need to adapt the relevant paths in the `datapusher-uwsgi.ini` to the ones you are using.


## Configuring


### CKAN Configuration

Add `datapusher` to the plugins in your CKAN configuration file
(generally located at `/etc/ckan/default/production.ini` or `/etc/ckan/default/ckan.ini`):

    ckan.plugins = <other plugins> datapusher

In order to tell CKAN where this webservice is located, the following must be
added to the `[app:main]` section of your CKAN configuration file :

    ckan.datapusher.url = http://0.0.0.0:8800/

There are other CKAN configuration options that allow to customize the CKAN - DataPusher
integation. Please refer to the [DataPusher Settings](https://docs.ckan.org/en/latest/maintaining/configuration.html#datapusher-settings) section in the CKAN documentation for more details.


### DataPusher Configuration

The DataPusher instance is configured in the `deployment/datapusher_settings.py` file.
Here's a summary of the options available.

| Name | Default | Description |
| -- | -- | -- |
| HOST | '0.0.0.0' | Web server host |
| PORT | 8800 | Web server port |
| SQLALCHEMY_DATABASE_URI | 'sqlite:////tmp/job_store.db' | SQLAlchemy Database URL |
| MAX_CONTENT_LENGTH | '1024000' | Max size of files to process in bytes |
| CHUNK_SIZE | '16384' | Chunk size when processing the data file |
| CHUNK_INSERT_ROWS | '250' | Number of records to send a request to datastore |
| DOWNLOAD_TIMEOUT | '30' | Download timeout for requesting the file |
| SSL_VERIFY | False | Do not validate SSL certificates when requesting the data file (*Warning*: Do not use this setting in production) |
| TYPES | [messytables.StringType, messytables.DecimalType, messytables.IntegerType, messytables.DateUtilType] | [Messytables][] types used internally, can be modified to customize the type guessing |
| TYPE_MAPPING | {'String': 'text', 'Integer': 'numeric', 'Decimal': 'numeric', 'DateUtil': 'timestamp' | Internal Messytables type mapping |
}

Most of the configuration options above can be also provided as environment variables prepending the name with `DATAPUSHER_`, eg `DATAPUSHER_SQLALCHEMY_DATABASE_URI`, `DATAPUSHER_PORT`, etc.


## Usage

Any file that has one of the supported formats (defined in [`ckan.datapusher.formats`](https://docs.ckan.org/en/latest/maintaining/configuration.html#ckan-datapusher-formats)) will be attempted to be loaded
into the DataStore.

You can also manually trigger resources to be resubmitted. When editing a resource in CKAN (clicking the "Manage" button on a resource page), a new tab named "DataStore" will appear. This will contain a log of the last attempted upload and a button to retry the upload.

![DataPusher UI](images/ui.png)

### Command line

Run the following command to submit all resources to datapusher, although it will skip files whose hash of the data file has not changed:

    ckan -c /etc/ckan/default/ckan.ini datapusher resubmit

On CKAN<=2.8:

    paster --plugin=ckan datapusher resubmit -c /etc/ckan/default/ckan.ini

To Resubmit a specific resource, whether or not the hash of the data file has changed::

    ckan -c /etc/ckan/default/ckan.ini datapusher submit {dataset_id}

On CKAN<=2.8:

    paster --plugin=ckan datapusher submit <pkgname> -c /etc/ckan/default/ckan.ini


## License

This material is copyright (c) 2020 Open Knowledge Foundation and other contributors

It is open and licensed under the GNU Affero General Public License (AGPL) v3.0
whose full text may be found at:

[http://www.fsf.org/licensing/licenses/agpl-3.0.html]()

