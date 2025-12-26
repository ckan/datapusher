import os
import ckanserviceprovider.web as web

config_filepath = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'datapusher_settings.py')

if 'JOB_CONFIG' not in os.environ:
    os.environ['JOB_CONFIG'] = config_filepath

web.init()

import datapusher.jobs as jobs

application = web.app
