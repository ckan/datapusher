'''
Test the whole datapusher but mock the datastore. The difference to the import tests
is that these tests can run on travis without a running CKAN and datastore.
'''

import os
import json
import unittest
import datetime
from nose.tools import assert_equal

from httpretty import HTTPretty
from httpretty import httprettified

import ckanserviceprovider.web as web
import datapusher.main as main
import datapusher.jobs as jobs
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

    def register_urls(self, filename='simple.csv', format='CSV', content_type='application/csv'):
        source_url = 'http://www.source.org/static/file'
        HTTPretty.register_uri(HTTPretty.GET, source_url,
                               body=get_static_file(filename),
                               content_type=content_type)

        res_url = 'http://www.ckan.org/api/3/action/resource_show'
        HTTPretty.register_uri(HTTPretty.POST, res_url,
                               body=json.dumps({
                                   'success': True,
                                   'result': {
                                       'url': source_url,
                                       'format': format
                                   }
                               }),
                               content_type="application/json")

        resource_update_url = 'http://www.ckan.org/api/3/action/resource_update'
        HTTPretty.register_uri(HTTPretty.POST, resource_update_url,
                               body=json.dumps({'success': True}),
                               content_type="application/json")

        datastore_del_url = 'http://www.ckan.org/api/3/action/datastore_delete'
        HTTPretty.register_uri(HTTPretty.POST, datastore_del_url,
                               body=json.dumps({'success': True}),
                               content_type="application/json")

    @httprettified
    def test_simple_csv(self):
        self.register_urls()
        data = {
            'apikey': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore(None, data, True)
        results = list(results)
        assert_equal(headers, [{'type': 'timestamp', 'id': u'date'},
                               {'type': 'numeric', 'id': u'temperature'},
                               {'type': 'text', 'id': u'place'}])
        assert_equal(len(results), 6)
        assert_equal(results[0],
                     {u'date': datetime.datetime(2011, 1, 1, 0, 0), u'place': u'Galway', u'temperature': 1})

    @httprettified
    def test_simple_tsv(self):
        self.register_urls('simple.tsv', 'tsv', 'application/csv')
        data = {
            'apikey': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore(None, data, True)
        results = list(results)
        assert_equal(headers, [{'type': 'timestamp', 'id': u'date'},
                               {'type': 'numeric', 'id': u'temperature'},
                               {'type': 'text', 'id': u'place'}])
        assert_equal(len(results), 6)
        assert_equal(results[0],
                     {u'date': datetime.datetime(2011, 1, 1, 0, 0),
                      u'place': u'Galway', u'temperature': 1})

    @httprettified
    def test_simple_xls(self):
        self.register_urls('simple.xls', 'xls', '')
        data = {
            'apikey': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore(None, data, True)
        results = list(results)
        assert_equal(headers, [{'type': 'timestamp', 'id': u'date'},
                               {'type': 'numeric', 'id': u'temperature'},
                               {'type': 'text', 'id': u'place'}])
        assert_equal(len(results), 6)
        assert_equal(results[0],
                     {u'date': datetime.datetime(2011, 1, 1, 0, 0),
                      u'place': u'Galway', u'temperature': 1})
