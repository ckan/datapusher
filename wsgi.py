import ckanserviceprovider.web as web
import datapusher.jobs as jobs

# check whether jobs have been imported properly
assert(jobs.push_to_datastore)

web.init()
web.app.run(web.app.config.get('HOST'), web.app.config.get('PORT'))
