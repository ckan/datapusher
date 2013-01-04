# ckan-importer-service

__WORK IN PROGRESS__ - Expect release in early 2013.

A service that migrates data to the CKAN datastore. 

There will be two endpoints. An asynchronous one that imports data into the datastore and a synchronous one that parses files and returns JSON (this will eventually replace dataproxy).

## Developer

You will need a running CKAN instance with a working datastore to use the importer service. Make sure that you add the API key to the `test.ini`. Use `nosetests` to run the tests. 