import os
import json
import ConfigParser

import importerservice.main as main

os.environ['JOB_CONFIG'] = os.path.join(os.path.dirname(__file__),
                                        'test.ini')

app = main.serve_test()


class TestWeb():
    @classmethod
    def setup_class(cls):
        config = ConfigParser.ConfigParser()
        config_file = os.environ.get('JOB_CONFIG')
        config.read(config_file)

    def test_status(self):
        rv = app.get('/status')
        assert json.loads(rv.data) == dict(version=0.1,
                                           job_types=['import_into_datastore', 'convert_resource'],
                                           name='ckan_importer'), rv.data
