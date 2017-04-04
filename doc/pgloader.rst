==================================
pgloader install and configuration
==================================

Datapusher uses 'pgloader' (by default) and it requires a few steps to install.

Versions
--------

Ideally you use version 3.3.0219f55 or later, because that is when the 'drop indexes' fix was added.

If you sacrifice the 'drop indexes' performance than you can use version 3.0.0 or later.

* Ubuntu 16.04 Xenial comes with pgloader 3.2.2, which can be used, but see: :ref:`label-name`
* Ubuntu 14.04 Trusty comes with pgloader 2.3.3, which is too old. Install from source instead.

Install pgloader from source
----------------------------

pgloader has no Backport PPA. There are .deb packages that are not currently up to date. However compiling it from source isn't too much trouble and provides maximum flexibility.

sbcl
~~~~

First you need 'sbcl' (Lisp compiler) version 1.2.4 or later.

Ubuntu 16.04 Xenial comes with sbcl 1.3.1, so you can do::

    sudo apt-get install sbcl

Ubuntu 14.04 Trusty comes with sbcl 1.1.14-2 which is too old, but there is a `backport PPA <https://launchpad.net/~jonathonf/+archive/ubuntu/backports/+index?batch=75&direction=backwards&start=75>`_::

    sudo add-apt-repository -y ppa:jonathonf/backports
    sudo apt-get update
    sudo apt-get install -y sbcl

Otherwise, compile sbcl from source::

    wget http://downloads.sourceforge.net/project/sbcl/sbcl/1.3.6/sbcl-1.3.6-source.tar.bz2
    tar xfj sbcl-1.3.6-source.tar.bz2
    cd sbcl-1.3.6
    ./make.sh --with-sb-thread --with-sb-core-compression --prefix=/usr
    # If it fails with "Killed" then increase memory. 1GB is not enough. 4GB works.
    sudo sh install.sh
    cd

other dependencies
~~~~~~~~~~~~~~~~~~

::

    sudo apt-get install -y unzip libsqlite3-dev make curl gawk freetds-dev libzip-dev

build
~~~~~

Download, build and install pgloader::

    cd ~
    git clone https://github.com/dimitri/pgloader.git  # e2bc7e4
    cd pgloader
    make
    sudo cp build/bin/pgloader /usr/bin/

Now check it runs::

    pgloader --version
    # e.g. pgloader version "3.3.0219f55"


Configuration
-------------

The datapusher_settings need adjusting if you with to use an older version of pgloader or not at all.

To change the settings, you should make a copy ``deployment/datapusher_settings.py``, edit the copy and then specify the copy when you start datapusher.

.. _drop-indexes:

Dropping indexes
~~~~~~~~~~~~~~~~

If you have installed pgloader version 3.0 to 3.3.e2bc7e4 (i.e. not as new as 3.3.0219f55), and are happy to sacrifice the speed (10x), then you can turn off 'drop indexes' by changing this option::

    DROP_INDEXES = False

Avoiding pgloader
~~~~~~~~~~~~~~~~~

If you wish to avoid using pgloader and revert to the legacy 'convert and load in chunks' code, sacrificing the pgloader speed improvements (3x or 30x if you drop indexes), then you can still do that by changing this option::

    USE_PGLOADER = False
