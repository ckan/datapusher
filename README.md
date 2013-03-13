# Systematic Squirrel

[![Build Status](https://travis-ci.org/okfn/systematic-squirrel.png)](https://travis-ci.org/okfn/systematic-squirrel)

__WORK IN PROGRESS__ - Expect release in mid 2013.

A service that migrates data to the CKAN datastore. Built on the [CKAN Service Provider](https://github.com/okfn/ckan-service-provider) and [Data Converters](https://github.com/okfn/dataconverters).

## API

```
{
    'apikey': 'my-secret-key',
    'job_type': 'import_into_datastore',
    'metadata': {
        'ckan_url': 'http://www.ckan.org/',
        'resource_id': '3b2987d2-e0e8-413c-92f0-7f9bfe148adc'
    }
}
```

## Developers

You will need a running CKAN instance with a working datastore to use the importer service. Make sure that you add the API key to the `tests/settings_test.py`. Use `nosetests` to run the tests.
