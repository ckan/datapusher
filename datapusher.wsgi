import os
import ckanserviceprovider.web as web
import datapusher.jobs as jobs

# this assumes that the virtual environment in called venv and directly one step up this directory
activate_this = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../venv/bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

# check whether jobs have been imported properly
assert(jobs.push_to_datastore)

web.configure()
application = web.app
