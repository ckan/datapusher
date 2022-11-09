[![Tests](https://github.com/ckan/datapusher/actions/workflows/test.yml/badge.svg)](https://github.com/ckan/datapusher/actions/workflows/test.yml)
[![Latest Version](https://img.shields.io/pypi/v/datapusher.svg)](https://pypi.python.org/pypi/datapusher/)
[![Downloads](https://img.shields.io/pypi/dm/datapusher.svg)](https://pypi.python.org/pypi/datapusher/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/datapusher.svg)](https://pypi.python.org/pypi/datapusher/)
[![License](https://img.shields.io/badge/license-GPL-blue.svg)](https://pypi.python.org/pypi/datapusher/)

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
`deployment/datapusher_local_settings.py` and modify the file to suit your needs. Also if running a production setup, make sure that the host and port matcht the `http` settings in the uWSGI configuration.

To run the tests:

    pytest

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

     # Create a user to run the web service (if necessary)
     sudo addgroup www-data
     sudo adduser -G www-data www-data

     # Install uWSGI
     sudo /usr/lib/ckan/datapusher/bin/pip install uwsgi

At this point you can run DataPusher with the following command:

    /usr/lib/ckan/datapusher/bin/uwsgi -i /usr/lib/ckan/datapusher/src/datapusher/deployment/datapusher-uwsgi.ini


*Note*: If you are installing the DataPusher on a different location than the default
one you need to adapt the relevant paths in the `datapusher-uwsgi.ini` to the ones you are using. Also you might need to change the `uid` and `guid` settings when using a different user.


### High Availability Setup

The default DataPusher configuration uses SQLite as the backend for the jobs database and a single uWSGI thread. To increase performance and concurrency you can configure DataPusher in the following way:

1. Use Postgres as database backend, which will allow concurrent writes (and provide a more reliable backend anyway). To use Postgres, create a user and a database and update the `SQLALCHEMY_DATABASE_URI` settting accordingly:

    ```
    # This assumes DataPusher is already installed
    sudo apt-get install postgresql libpq-dev
    sudo -u postgres createuser -S -D -R -P datapusher_jobs
    sudo -u postgres createdb -O datapusher_jobs datapusher_jobs -E utf-8

    # Run this in the virtualenv where DataPusher is installed
    pip install psycopg2

    # Edit SQLALCHEMY_DATABASE_URI in datapusher_settings.py accordingly
    # eg SQLALCHEMY_DATABASE_URI=postgresql://datapusher_jobs:YOURPASSWORD@localhost/datapusher_jobs
    ```

2. Start more uWSGI threads. On the `deployment/datapusher-uwsgi.ini` file, set `workers` and `threads` to a value that suits your needs, and add the `lazy-apps=true` setting to avoid concurrency issues with SQLAlchemy, eg:

    ```
    # ... rest of datapusher-uwsgi.ini
    workers         =  3
    threads         =  3
    lazy-apps       =  true
    ```

## Configuring


### CKAN Configuration

Add `datapusher` to the plugins in your CKAN configuration file
(generally located at `/etc/ckan/default/production.ini` or `/etc/ckan/default/ckan.ini`):

    ckan.plugins = <other plugins> datapusher

In order to tell CKAN where this webservice is located, the following must be
added to the `[app:main]` section of your CKAN configuration file :

    ckan.datapusher.url = http://127.0.0.1:8800/
   
Starting from CKAN 2.10, DataPusher requires a valid API token to operate (see [the documentation on API tokens](https://docs.ckan.org/en/latest/api/index.html#authentication-and-api-tokens)), and will fail to start if the following option is not set:

    ckan.datapusher.api_token = <api_token>

There are other CKAN configuration options that allow to customize the CKAN - DataPusher
integation. Please refer to the [DataPusher Settings](https://docs.ckan.org/en/latest/maintaining/configuration.html#datapusher-settings) section in the CKAN documentation for more details.


### DataPusher Configuration

The DataPusher instance is configured in the `deployment/datapusher_settings.py` file.
Here's a summary of the options available.

| Name | Default | Description |
| -- | -- | -- |
| HOST | '0.0.0.0' | Web server host |
| PORT | 8800 | Web server port |
| SQLALCHEMY_DATABASE_URI | 'sqlite:////tmp/job_store.db' | SQLAlchemy Database URL. See note about database backend below. |
| MAX_CONTENT_LENGTH | '1024000' | Max size of files to process in bytes |
| CHUNK_SIZE | '16384' | Chunk size when processing the data file |
| CHUNK_INSERT_ROWS | '250' | Number of records to send a request to datastore |
| DOWNLOAD_TIMEOUT | '30' | Download timeout for requesting the file |
| SSL_VERIFY | False | Do not validate SSL certificates when requesting the data file (*Warning*: Do not use this setting in production) |
| TYPES | [messytables.StringType, messytables.DecimalType, messytables.IntegerType, messytables.DateUtilType] | [Messytables][] types used internally, can be modified to customize the type guessing |
| TYPE_MAPPING | {'String': 'text', 'Integer': 'numeric', 'Decimal': 'numeric', 'DateUtil': 'timestamp'} | Internal Messytables type mapping |
| LOG_FILE | `/tmp/ckan_service.log` | Where to write the logs. Use an empty string to disable |
| STDERR | `True` | Log to stderr? |


Most of the configuration options above can be also provided as environment variables prepending the name with `DATAPUSHER_`, eg `DATAPUSHER_SQLALCHEMY_DATABASE_URI`, `DATAPUSHER_PORT`, etc. In the specific case of `DATAPUSHER_STDERR` the possible values are `1` and `0`.


By default, DataPusher uses SQLite as the database backend for jobs information. This is fine for local development and sites with low activity, but for sites that need more performance, Postgres should be used as the backend for the jobs database (eg `SQLALCHEMY_DATABASE_URI=postgresql://datapusher_jobs:YOURPASSWORD@localhost/datapusher_jobs`. See also [High Availability Setup](#high-availability-setup). If SQLite is used, its probably a good idea to store the database in a location other than `/tmp`. This will prevent the database being dropped, causing out of sync errors in the CKAN side. A good place to store it is the CKAN storage folder (if DataPusher is installed in the same server), generally in `/var/lib/ckan/`.


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
