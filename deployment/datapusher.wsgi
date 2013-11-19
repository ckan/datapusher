import os
import sys
import hashlib

activate_this = os.path.join('/usr/lib/ckan/default/bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

import ckanserviceprovider.web as web
import datapusher.jobs as jobs
os.environ['JOB_CONFIG'] = '/etc/ckan/datapusher_settings.py'

web.configure()
application = web.app


