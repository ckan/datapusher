# Use this file for development, on a production setup (eg a CKAN production
# install) use deployment/datapusher.wsgi

import ckanserviceprovider.web as web

web.init()

import datapusher.jobs as jobs
# check whether jobs have been imported properly
assert(jobs.push_to_datastore)

web.app.run(web.app.config.get('HOST'), web.app.config.get('PORT'))
