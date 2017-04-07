v0.1.0 TBA
==========
* pgloader now used to load data (30x faster)

v0.0.10 2017-02-24
==================
* #114 Locale fix
* messytables version pinned
* SSL_VERIFY

v0.0.9 2016-10-18
=================
* html5lib version pinned

v0.0.8 2016-03-17
=================
* Fix related to datapusher being called multiple times when adding or deleting a CSV
  https://github.com/ckan/ckan/issues/2856
* Fix crash when column headers were not strings

v0.0.7 2015-10-26
=================
* Added the ability to configure the maximum file size (previously fixed at 10MB)

v0.0.6 2015-03-04
=================

v0.0.5 2015-02-27
=================
* Added the ability to configure the guessing of types to be done by something other than messytables.

v0.0.4 2015-02-06
=================
* Column names now have leading & trailing whitespace stripped off

v0.0.3 2015-01-13
=================
* Log messages from DataStore are reported to the user better

v0.0.2 2014-12-15
=================
* HTTP errors better reported

v0.0.1 2014-11-20
=================
* First packaged release, called "datapusher", based on ckan-service-provider

Early years
===========

Before it was released on PyPI, it was available in source form during 2012 and 2013 as versions "1.0" and "0.1". As well as "datapusher", it has names including "datastorer" and "ckan importer".