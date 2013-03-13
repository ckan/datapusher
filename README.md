# Systematic Squirrel

[![Build Status](https://travis-ci.org/okfn/systematic-squirrel.png)](https://travis-ci.org/okfn/systematic-squirrel)

__WORK IN PROGRESS__ - Expect release in mid 2013.

A service that migrates data to the CKAN datastore. Built on the [CKAN Service Provider](https://github.com/okfn/ckan-service-provider) and [Data Converters](https://github.com/okfn/dataconverters).

## Developer

You will need a running CKAN instance with a working datastore to use the importer service. Make sure that you add the API key to the `test.ini`. Use `nosetests` to run the tests.
