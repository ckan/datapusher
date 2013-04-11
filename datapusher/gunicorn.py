import ckanserviceprovider.web as web
import jobs

# check whether jobs have been imported properly
assert(jobs.push_to_datastore)


web.configure()
app = web.app
