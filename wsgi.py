import ckanserviceprovider.web as web
import datapusher.jobs as jobs

# check whether jobs have been imported properly
assert(jobs.push_to_datastore)
web.configure()
app = web.app
