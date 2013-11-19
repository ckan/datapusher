# Data Pusher

[![Build Status](https://travis-ci.org/okfn/datapusher.png)](https://travis-ci.org/okfn/datapusher)

A service that extracts data from files that contain tabular data (like CSV or Excel) and writes it to the CKAN DataStore. You only have to provide a URL to the resource, an API key and the URL to your CKAN instance. The Data Pusher will then asynchronously fetch the file, parse it, create a DataStore resource and put the data in the DataStore.  This service is intended to replace the DataStorer.

The Data Pusher is built on the [CKAN Service Provider](https://github.com/okfn/ckan-service-provider) and [Messytables](https://github.com/okfn/messytables).

## Deployment

The Data Pusher is a flask application so you can choose your preferred [way of deployment](http://flask.pocoo.org/docs/deploying/). 
The following instructions are nonetheless the way the ckan package will install it in future versions.  So this method is recommended (especially if on ubuntu or debian). Other distros should follow a very similar pattern.

This assumes you already have CKAN installed on this server in the same location as the docs mention or via a package install.  If this is correct you should be able to run the following as is.

### Download and Install
```bash
#go to the ckan source directory
cd /usr/lib/ckan/default/src

#clone the source
sudo git clone https://github.com/okfn/datapusher.git

#install the datapussher
cd datapusher
sudo /usr/lib/ckan/default/bin/python setup.py develop

#copy the standard apache config file
sudo cp deployment/datapusher /etc/apache2/sites-available/

#copy the standard datapusher wsgi file
sudo cp deployment/datapusher.wsgi /etc/ckan/

#copy the standard datapusher settings.
sudo cp deployment/datapusher_settings /etc/ckan/

#open up port 8800 on apache where the datapusher accepts connections.
sudo sh -c 'echo "NameVirtualHost *:8800" >> /etc/apache2/ports.conf'
sudo sh -c 'echo "Listen 8800" >> /etc/apache2/ports.conf'

#enable datapusher apache
sudo a2ensite datapusher
```

### Instructions for CKAN 2.1 users
Follow these instruction for CKAN 2.1 only
```bash
#go to the ckan source directory
cd /usr/lib/ckan/default/src
#clone the datapusher CKAN extension
sudo git clone https://github.com/okfn/ckanext-datapusherext.git
#install datapusherext
cd ckanext-datapusherext
sudo /usr/lib/ckan/default/bin/python setup.py develop
```

Add ``` datapusherext  ``` to the plugins line in /etc/ckan/default/production.ini
Restart apache.  ``` sudo service apache2 restart ```

### Instructions for CKAN 2.2 users

Add ``` datapusher ``` to the plugins line in /etc/ckan/default/production.ini
Restart apache.  ``` sudo service apache2 restart ```


### Test the configuration

To test if it is datapusher service is working or not run

```curl 0.0.0.0:8800```

The result should look something like
```
{
  "help": "\n        Get help at:\n        http://ckan-service-provider.readthedocs.org/."
}
```

### Error and logs.

If there are issues you should look in ``` /var/log/apache2/datapusher.error.log ```


