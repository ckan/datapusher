import os
import json
from nose.tools import assert_equal

import datapusher.main as main

os.environ['JOB_CONFIG'] = os.path.join(os.path.dirname(__file__),
                                        'settings_test.py')

app = main.serve_test()


class TestWeb():

    def test_status(self):
        rv = app.get('/status')
        assert_equal(json.loads(rv.data), dict(version=0.1,
                     job_types=['push_to_datastore'],
                     name='datapusher'))
