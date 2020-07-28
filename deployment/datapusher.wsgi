import os
import ckanserviceprovider.web as web

config_filepath = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'datapusher_settings.py')

os.environ['JOB_CONFIG'] = config_filepath

web.init()

import datapusher.jobs as jobs

application = web.app
