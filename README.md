# Data Pusher

[![Build Status](https://travis-ci.org/okfn/datapusher.png)](https://travis-ci.org/okfn/datapusher)

__WORK IN PROGRESS__ - Expect release in mid 2013.

A service that extracts data from files that contain tabular data (like CSV or Excel) and writes it to the CKAN DataStore. You only have to provide a URL to the resource, an API key and the URL to your CKAN instance. The Data Pusher will then asynchronously fetch the file, parse it, create a DataStore resource and put the data from the DataStore.

The Data Pusher is built on the [CKAN Service Provider](https://github.com/okfn/ckan-service-provider) and [Data Converters](https://github.com/okfn/dataconverters).

## API

Post the following data to `/job`

```json
{
    "api_key": "my-secret-key",
    "job_type": "push_to_datastore",
    "result_url": "https://www.ckan.org/datapusher/callback",
    "metadata": {
        "ckan_url": "http://www.ckan.org/",
        "resource_id": "3b2987d2-e0e8-413c-92f0-7f9bfe148adc"
    }
}
```

Note that the result_url is optional but it's the best way to get notifies when the (asynchronous) job has finished.

Read more about the API at http://ckan-service-provider.readthedocs.org/en/latest/

## Deployment

The Data Pusher is a flask application so you can choose your preferred [way of deployment](http://flask.pocoo.org/docs/deploying/). The following is just an example and not the only possible way to deploy the Data Pusher.

This is work in progress!

### Install dependencies

`sudo apt-get install python-dev postgresql libpq-dev python-pip python-virtualenv git-core uwsgi nginx`

### Create a virtual environment and install the Data Pusher

```
virtualenv venv
source venv/bin/activate
git clone git://github.com/okfn/datapusher.git
cd datapusher
python setup.py develop
```

### Edit the web server configuration and restart the server

...

### Install postgres and create a database

Install `psycopg2` because it is not a default package
`pip install psycopg2`

### Edit the Data Pusher configuration

`cp settings_local.py.tmpl settings_local.py`
`vim settings_local.py`

### Start the Data Pusher service

...


## Developers

You will need a running CKAN instance with a working DataStore to use the importer service. Make sure that you add the API key to the `tests/settings_test.py`. Use `nosetests` to run the tests.

The Data Pusher is built on the CKAN Service which makes functions available as jobs. The only job that the Data Pusher has, is `push_to_datastore`.
