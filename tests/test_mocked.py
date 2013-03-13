import os
import json

from nose.tools import assert_equal
import requests
from httpretty import HTTPretty
from httpretty import httprettified

import ckanserviceprovider.web as web
import systematicsquirrel.main as main
import systematicsquirrel.jobs as jobs

os.environ['JOB_CONFIG'] = os.path.join(os.path.dirname(__file__),
                                        'settings_test.py')

web.configure()
app = main.serve_test()


def join_static_path(filename):
    return os.path.join(os.path.dirname(__file__), 'static', filename)


def get_static_file(filename):
    return open(join_static_path(filename)).read()


class TestImport():
    @classmethod
    def setup_class(cls):
        cls.host = 'www.ckan.org'
        cls.api_key = 'my-key'
        cls.resource_id = 'foo-bar-42'

    @httprettified
    def test_simple_csv_directly(self):
        source_url = 'http://www.source.org/static/simple.csv'
        HTTPretty.register_uri(HTTPretty.GET, source_url,
                               body=get_static_file('simple.csv'),
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
            'metadata': {'key': 'value'},
            'apikey': self.api_key,
            'job_type': 'import_into_datastore',
            'data': {
                'url': source_url,
                'format': 'csv',
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        jobs.import_into_datastore(None, data)
