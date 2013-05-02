# -*- coding: utf-8 -*-
'''
Test the whole datapusher but do not push to the datastore.
The difference to the integration tests is that these tests can
run on travis without a running CKAN and datastore. These testsdo not
mock the datastore but instead set the dry-run variable.
'''

import os
import json
import unittest
import datetime
from nose.tools import assert_equal, raises

import httpretty

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
        cls.api_key = 'my-fake-key'
        cls.resource_id = 'foo-bar-42'

    def register_urls(self, filename='simple.csv', format='CSV', content_type='application/csv'):
        source_url = 'http://www.source.org/static/file'
        httpretty.register_uri(httpretty.GET, source_url,
                               body=get_static_file(filename),
                               content_type=content_type)

        res_url = 'http://www.ckan.org/api/3/action/resource_show'
        httpretty.register_uri(httpretty.POST, res_url,
                               body=json.dumps({
                                   'success': True,
                                   'result': {
                                       'url': source_url,
                                       'format': format
                                   }
                               }),
                               content_type='application/json')

        resource_update_url = 'http://www.ckan.org/api/3/action/resource_update'
        httpretty.register_uri(httpretty.POST, resource_update_url,
                               body=json.dumps({'success': True}),
                               content_type='application/json')

        datastore_del_url = 'http://www.ckan.org/api/3/action/datastore_delete'
        httpretty.register_uri(httpretty.POST, datastore_del_url,
                               body=json.dumps({'success': True}),
                               content_type='application/json')

    @httpretty.activate
    @raises(util.JobError)
    def test_too_large_file(self):
        self.register_urls()
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }
        source_url = 'http://www.source.org/static/file'
        size = jobs.MAX_CONTENT_LENGTH + 1
        httpretty.register_uri(
            httpretty.GET, source_url,
            body='a' * size,
            content_length=size,
            content_type='application/json')

        jobs.push_to_datastore(None, data, web.queue, True)

    @httpretty.activate
    def test_delete_404(self):
        self.register_urls()
        datastore_del_url = 'http://www.ckan.org/api/3/action/datastore_delete'
        httpretty.register_uri(httpretty.POST, datastore_del_url,
                               status=404,
                               body=json.dumps({'success': False}),
                               content_type='application/json')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore(None, data, web.queue, True)

    @httpretty.activate
    def test_simple_csv(self):
        self.register_urls()
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore(None, data, web.queue, True)
        results = list(results)
        assert_equal(headers, [{'type': 'timestamp', 'id': u'date'},
                               {'type': 'numeric', 'id': u'temperature'},
                               {'type': 'text', 'id': u'place'}])
        assert_equal(len(results), 6)
        assert_equal(results[0],
                     {u'date': datetime.datetime(2011, 1, 1, 0, 0), u'place': u'Galway', u'temperature': 1})

    @httpretty.activate
    def test_simple_tsv(self):
        self.register_urls('simple.tsv', 'tsv', 'application/csv')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore(None, data, web.queue, True)
        results = list(results)
        assert_equal(headers, [{'type': 'timestamp', 'id': u'date'},
                               {'type': 'numeric', 'id': u'temperature'},
                               {'type': 'text', 'id': u'place'}])
        assert_equal(len(results), 6)
        assert_equal(results[0],
                     {u'date': datetime.datetime(2011, 1, 1, 0, 0),
                      u'place': u'Galway', u'temperature': 1})

    @httpretty.activate
    def test_simple_xls(self):
        self.register_urls('simple.xls', 'xls', 'application/vnd.ms-excel')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore(None, data, web.queue, True)
        results = list(results)
        assert_equal(headers, [{'type': 'timestamp', 'id': u'date'},
                               {'type': 'numeric', 'id': u'temperature'},
                               {'type': 'text', 'id': u'place'}])
        assert_equal(len(results), 6)
        assert_equal(results[0],
                     {u'date': datetime.datetime(2011, 1, 1, 0, 0),
                      u'place': u'Galway', u'temperature': 1})

    @httpretty.activate
    def test_real_csv(self):
        self.register_urls('october_2011.csv', 'csv')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore(None, data, web.queue, True)
        results = list(results)
        assert_equal(headers, [{'type': 'text', 'id': u'Directorate'},
                               {'type': 'text', 'id': u'Service Area'},
                               {'type': 'text', 'id': u'Expenditure Category'},
                               {'type': 'timestamp', 'id': u'Payment Date'},
                               {'type': 'text', 'id': u'Supplier Name'},
                               {'type': 'numeric', 'id': u'Internal Ref'},
                               {'type': 'text', 'id': u'Capital/ Revenue'},
                               {'type': 'text', 'id': u'Cost Centre'},
                               {'type': 'text', 'id': u'Cost Centre Description'},
                               {'type': 'float', 'id': u'Grand Total'}])
        assert_equal(len(results), 230)
        assert_equal(results[0],
                     {u'Directorate': u'Adult and Culture',
                      u'Service Area': u'Ad Serv-Welfare Rights-    ',
                      u'Expenditure Category': u'Supplies & Services',
                      u'Cost Centre Description': u'WELFARE RIGHTS WORKERS       M',
                      u'Capital/ Revenue': u'Revenue',
                      u'Grand Total': 828.0,
                      u'Payment Date': datetime.datetime(2011, 10, 24, 0, 0),
                      u'Internal Ref': 5277184,
                      u'Cost Centre': u'1MR48',
                      u'Supplier Name': u'ALBANY OFFICE FURNITURE SOLUTIONS'})

    @httpretty.activate
    def test_weird_header(self):
        self.register_urls('weird_head_padding.csv', 'csv')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore(None, data, web.queue, True)
        results = list(results)
        assert_equal(len(headers), 11)
        assert_equal(len(results), 82)
        assert_equal(headers[1]['id'].strip(), u'1985')
        assert_equal(results[1]['column_1'].strip(), u'Gefäßchirurgie')
