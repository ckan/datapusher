Debugging
=========

Test the configuration
----------------------

To test if it is |datapusher| service is working or not run::

    curl 0.0.0.0:8800

The result should look something like::

    {
    "help": "\n        Get help at:\n        http://ckan-service-provider.readthedocs.org/."
    }

Error and logs
--------------

If there are any issues you should look in ``/var/log/apache2/datapusher.error.log``.
All log output will be put in there.

Debugging Gunicorn
------------------

Gunicorn doesn't print error logs to the console by default. Use the option
`--log-file=-` to print logs to the console for debugging.
