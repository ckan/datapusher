# Data Pusher

[![Build Status](https://travis-ci.org/okfn/datapusher.png)](https://travis-ci.org/okfn/datapusher)

A service that extracts data from files that contain tabular data (like CSV or Excel) and writes it to the CKAN DataStore. You only have to provide a URL to the resource, an API key and the URL to your CKAN instance. The Data Pusher will then asynchronously fetch the file, parse it, create a DataStore resource and put the data in the DataStore.  This service is intended to replace the DataStorer.

For installation guide please goto [datapusher docs](http://datapusher.readthedocs.org).

The Data Pusher is built on the [CKAN Service Provider](https://github.com/okfn/ckan-service-provider) and [Messytables](https://github.com/okfn/messytables).


