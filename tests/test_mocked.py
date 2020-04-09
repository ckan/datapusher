# -*- coding: utf-8 -*-
'''
Test the whole datapusher but mock the CKAN datastore.
'''

import os
import json
import unittest

import httpretty

import datapusher.main as main
import datapusher.jobs as jobs
import ckanserviceprovider.util as util

os.environ['JOB_CONFIG'] = os.path.join(os.path.dirname(__file__),
                                        'settings_test.py')

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

    def register_urls(self):
        source_url = 'http://www.source.org/static/simple.csv'
        httpretty.register_uri(httpretty.GET, source_url,
                               body=get_static_file('simple.csv'),
                               content_type="application/csv")

        res_url = 'http://www.ckan.org/api/3/action/resource_show'
        httpretty.register_uri(httpretty.POST, res_url,
                               body=json.dumps({
                                   'success': True,
                                   'result': {
                                       'id': '32h4345k34h5l345',
                                       'name': 'short name',
                                       'url': source_url,
                                       'format': 'CSV'
                                   }
                               }),
                               content_type="application/json")

        resource_update_url = 'http://www.ckan.org/api/3/action/resource_update'
        httpretty.register_uri(httpretty.POST, resource_update_url,
                               body='{"success": true}',
                               content_type="application/json")

        datastore_del_url = 'http://www.ckan.org/api/3/action/datastore_delete'
        httpretty.register_uri(httpretty.POST, datastore_del_url,
                               body='{"success": true}',
                               content_type="application/json")

        datastore_url = 'http://www.ckan.org/api/3/action/datastore_create'
        httpretty.register_uri(httpretty.POST, datastore_url,
                               body='{"success": true}',
                               content_type="application/json")

        datastore_check_url = 'http://www.ckan.org/api/3/action/datastore_search'
        httpretty.register_uri(httpretty.POST, datastore_check_url,
                               body=json.dumps({'success': True}),
                               content_type='application/json')

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

        jobs.push_to_datastore('fake_id', data)

    @httpretty.activate
    def test_wrong_api_key(self):
        self.register_urls()

        datastore_url = 'http://www.ckan.org/api/3/action/datastore_create'
        httpretty.register_uri(httpretty.POST, datastore_url,
                               body=json.dumps({
                                   'success': False,
                                   'error': {
                                       'message': 'Zugriff verweigert',
                                       '__type': 'Authorization Error'}}),
                               content_type="application/json",
                               status=403)

        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        self.assertRaises(util.JobError, jobs.push_to_datastore, 'fake_id', data)
