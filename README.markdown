[![Build Status](https://travis-ci.org/ckan/datapusher.png?branch=master)](https://travis-ci.org/ckan/datapusher)
[![Coverage Status](https://coveralls.io/repos/ckan/datapusher/badge.png?branch=master)](https://coveralls.io/r/ckan/datapusher?branch=master)
[![Latest Version](https://img.shields.io/pypi/v/datapusher.svg)](https://pypi.python.org/pypi/datapusher/)
[![Downloads](https://img.shields.io/pypi/dm/datapusher.svg)](https://pypi.python.org/pypi/datapusher/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/datapusher.svg)](https://pypi.python.org/pypi/datapusher/)
[![Development Status](https://img.shields.io/pypi/status/datapusher.svg)](https://pypi.python.org/pypi/datapusher/)
[![License](https://img.shields.io/badge/license-GPL-blue.svg)](https://pypi.python.org/pypi/datapusher/)

[PyPI]: https://pypi.python.org/pypi/datapusher
[DataStorer]: https://github.com/ckan/ckanext-datastorer
[DataPusher documentation]: https://docs.ckan.org/projects/datapusher/en/latest/
[CKAN Service Provider]: https://github.com/ckan/ckan-service-provider
[Messytables]: https://github.com/okfn/messytables


DataPusher
==========

DataPusher is a standalone web service that automatically downloads any CSV or
XLS (Excel) data files from a CKAN site's resources when they are added to the
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

For details see the [DataPusher documentation][].

Note that if you installed CKAN using the _package install_ option then a
DataPusher instance should be automatically installed and configured to work
with your CKAN site.

DataPusher is a replacement for [DataStorer][].
It's built using [CKAN Service Provider][] and [Messytables][].

The original author of DataPusher was
Dominik Moritz <dominik.moritz@okfn.org>. For the current list of contributors
see [github.com/ckan/datapusher/contributors](https://github.com/ckan/datapusher/contributors)


## Development

To install DataPusher for development:

```bash
git clone https://github.com/ckan/datapusher.git
cd datapusher
pip install -r requirements-dev.txt
```

To run the tests:

```bash
nosetests
```

To build the documentation:

```bash
pip install -r doc-requirements.txt
python setup.py build_sphinx
```

## Releasing a New Version

To release a new version of DataPusher:

1. Increment the version number in [datapusher/__init__.py](datapusher/__init__.py)

2. Build a source distribution of the new version and publish it to
   [PyPI][]:

   ```bash
   python setup.py sdist bdist_wheel
   pip install --upgrade twine
   twine upload dist/*
   ```

   You may want to test installing and running the new version from PyPI in a
   clean virtualenv before continuing to the next step.

3. Commit your setup.py changes to git, tag the release, and push the changes
   and the tag to GitHub:

   ```bash
   git commit setup.py -m "Bump version number"
   git tag 0.0.1
   git push
   git push origin 0.0.1
   ```

   (Replace both instances of 0.0.1 with the number of the version you're
   releasing.)
