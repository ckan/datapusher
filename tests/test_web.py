import os
import json
import time

import requests

import ckanserviceprototype.web as web

import datastorerservice.datastorer as ds
os.environ['JOB_CONFIG'] = os.path.join(os.path.dirname(__file__),
                                        'test.ini')

try:
    os.remove('/tmp/job_store.db')
except OSError:
    pass
web.configure()
app = web.app.test_client()


class TestWeb():
    def test_status(self):
        rv = app.get('/status')
        assert json.loads(rv.data) == dict(version=0.1,
                                           job_types=['echo'],
                                           name='datastorer'), rv.data
