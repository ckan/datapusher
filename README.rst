=========================================================
DataPusher - Automatically add Data to the CKAN DataStore
=========================================================

.. image:: https://secure.travis-ci.org/ckan/datapusher.png?branch=master
    :target: http://travis-ci.org/ckan/datapusher
    :alt: Build Status

A service that extracts data from files that contain tabular data (like CSV or
Excel) and writes it to the CKAN DataStore. You only have to provide a URL to
the resource, an API key and the URL to your CKAN instance. The DataPusher
will then asynchronously fetch the file, parse it, create a DataStore resource
and put the data in the DataStore.

This service is intended to replace the DataStorer_.

For an installation guide please go to the `DataPusher documentation`_.

The Data Pusher is built on the `CKAN Service Provider`_
and Messytables_.
    
.. _Datastorer: https://github.com/ckan/ckanext-datastorer
.. _DataPusher documentation: http://docs.ckan.org/projects/datapusher
.. _CKAN Service Provider: https://github.com/ckan/ckan-service-provider
.. _Messytables: https://github.com/okfn/messytables

