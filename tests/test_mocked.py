import os
import json
import unittest

from httpretty import HTTPretty
from httpretty import httprettified

import ckanserviceprovider.web as web
import systematicsquirrel.main as main
import systematicsquirrel.jobs as jobs
import ckanserviceprovider.util as util

os.environ['JOB_CONFIG'] = os.path.join(os.path.dirname(__file__),
                                        'settings_test.py')

web.configure()
app = main.serve_test()


def join_static_path(filename):
    return os.path.join(os.path.dirname(__file__), 'static', filename)


def get_static_file(filename):
    return open(join_static_path(filename)).read()


class TestImport(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        cls.host = 'www.ckan.org'
        cls.api_key = 'my-key'
        cls.resource_id = 'foo-bar-42'

    @httprettified
    def test_simple_csv_basic(self):
        source_url = 'http://www.source.org/static/simple.csv'
        HTTPretty.register_uri(HTTPretty.GET, source_url,
                               body=get_static_file('simple.csv'),
                               content_type="application/csv",
                               status=200)

        res_url = 'http://www.ckan.org/api/action/resource_show'
        HTTPretty.register_uri(HTTPretty.POST, res_url,
                               body=json.dumps({
                                'url': source_url,
                                'format': 'csv'
                                }),
                               content_type="application/csv",
                               status=200)

        def create_handler(method, uri, headers):
            return json.dumps({'success': True})

        datastore_url = 'http://www.ckan.org/api/action/datastore_create'
        HTTPretty.register_uri(HTTPretty.POST, datastore_url,
                               body=create_handler,
                               content_type="application/json",
                               status=200)

        data = {
            'apikey': self.api_key,
            'job_type': 'import_into_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        jobs.import_into_datastore(None, data)

        datastore_url = 'http://www.ckan.org/api/action/datastore_create'
        HTTPretty.register_uri(HTTPretty.POST, datastore_url,
                               body=json.dumps({'success': False, 'error': {'message': 'Zugriff verweigert', '__type': 'Authorization Error'}}),
                               content_type="application/json",
                               status=403)

        data = {
            'apikey': self.api_key,
            'job_type': 'import_into_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        self.assertRaises(util.JobError, jobs.import_into_datastore, None, data)
