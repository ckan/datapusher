# Data Pusher

[![Build Status](https://travis-ci.org/okfn/datapusher.png)](https://travis-ci.org/okfn/datapusher)

__WORK IN PROGRESS__ - Expect release in mid 2013.

A service that migrates data to the CKAN datastore. Built on the [CKAN Service Provider](https://github.com/okfn/ckan-service-provider) and [Data Converters](https://github.com/okfn/dataconverters).

## API

Post the following data to `/job`

```json
{
    "apikey": "my-secret-key",
    "job_type": "push_to_datastore",
    "result_url": "https://www.ckan.org/datapusher/callback",
    "metadata': {
        "ckan_url": "http://www.ckan.org/",
        "resource_id": "3b2987d2-e0e8-413c-92f0-7f9bfe148adc"
    }
}
```

## Deployment

The datapusher is a standard flask app so you can choose your preferred [way of deployment](http://flask.pocoo.org/docs/deploying/). in the following we will explain a set up with postgres, nginx and gunicorn.

This is work in progress!

### Install dependencies

`sudo apt-get install python-dev postgresql libpq-dev python-pip python-virtualenv git-core uwsgi nginx`

### Create a virtual environment and install the datapusher

`virtualenv venv`
`source venv/bin/activate`
`git clone git://github.com/okfn/datapusher.git`
`cd datapusher`
`python setup.py develop`

### edit the nginx configuration and restart the server

...

### Install postgres and create a database

Install `psycopg2` because it is not a default package
`pip install psycopg2`

### Edit the datapusher configuration

`cp settings_local.py.tmpl settings_local.py`
`vim settings_local.py`

### Run uwsgi

create a config file for uwsgi
...

run uwsgi
`uwsgi --ini /usr/share/uwsgi/conf/default.ini --ini /etc/uwsgi/apps-enabled/pusher.ini --daemonize`

## Developers

You will need a running CKAN instance with a working datastore to use the importer service. Make sure that you add the API key to the `tests/settings_test.py`. Use `nosetests` to run the tests.
