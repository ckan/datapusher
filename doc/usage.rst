====================
Using the Datapusher
====================

The datapusher will work without any more configuration as long as the
datapusher (or datapusherext for version 2.1) plugin is installed and added
to the ckan config file.

Any file that has a format of csv or xls will be attempted to be loaded
into to datastore.

Extra usage information for CKAN 2.2 users
------------------------------------------
When editing a resource is CKAN a new tab will appear named ``Resource Data``.
This will contain a log of the last attempted upload and an opportunity
to retry to upload.

Extra usage information for CKAN 2.1 users
------------------------------------------
If you want to retry an upload go into the resource edit form in CKAN and
just click the update button to resubmit the resource metadata.
This will retrigger an upload.
