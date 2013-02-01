import os
import json
import uuid
import time

from nose.tools import assert_equal
import requests
from httpretty import HTTPretty
from httpretty import httprettified

import ckanserviceprovider.web as web
import importerservice.main as main
import importerservice.datastorer as ds

import settings_test as config

os.environ['JOB_CONFIG'] = os.path.join(os.path.dirname(__file__),
                                        'settings_test.py')

web.configure()
app = main.serve_test()


def join_static_path(filename):
    return os.path.join(os.path.dirname(__file__), 'static', filename)


def get_static_file(filename):
    return open(join_static_path(filename)).read()


class TestDatastorer():
    resource_ids = []

    @classmethod
    def setup_class(cls):
        cls.host = config.CKAN_HOST
        cls.api_key = config.USER_API_KEY

    def teardown(self):
        self.clean_up()

    def clean_up(self):
        ''' Go through all created resources and delete them
        '''
        while self.resource_ids:
            res_id = self.resource_ids.pop()
            request = {'resource_id': res_id}
            r = requests.post('http://%s/api/action/datastore_delete' % self.host,
                         data=json.dumps(request),
                         headers={'Content-Type': 'application/json',
                                  'Authorization': self.api_key},
                         )
            if r.status_code not in [200, 404]:
                raise Exception('Error deleting datastore for resource %s' % res_id)

    def make_resource_id(self):
        ''' Create a resource in ckan and get back the id
        '''
        r = requests.post(
            'http://%s/api/action/package_create' % self.host,
            data=json.dumps(
                {'name': str(uuid.uuid4()),
                 'resources': [{u'url': u'test'}]}
            ),
            headers={'Authorization': self.api_key, 'content-type': 'application/json'}
        )
        if r.status_code != 200:
                raise Exception('Error creating datastore for resource. Check the CKAN output.')

        res_id = json.loads(r.content)['result']['resources'][0]['id']
        self.resource_ids.append(res_id)
        return res_id

    @httprettified
    def test_simple_csv_directly(self):
        url = 'http://www.ckan.org/static/simple.csv'
        HTTPretty.register_uri(HTTPretty.GET, url,
                           body=get_static_file('simple.csv'),
                           content_type="application/csv")
        resource_id = self.make_resource_id()

        data = {
            'metadata': {'key': 'value'},
            'apikey': self.api_key,
            'job_type': 'import_into_datastore',
            'data': {
                'url': url,
                'format': 'csv',
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': resource_id
            }
        }

        ds.import_into_datastore(None, data)

        response = requests.get(
            'http://%s/api/action/datastore_search?resource_id=%s' % (self.host, resource_id),
             headers={"content-type": "application/json"})

        result = json.loads(response.content)

        assert not 'error' in result, result['error']

        value = result['result']['records'][0][u'temperature']
        assert_equal(int(value), 1)
        assert_equal(result['result']['total'], 6)
        assert_equal(result['result']['fields'], [{u'type': u'int4', u'id': u'_id'},
                                              {u'type': u'timestamp', u'id': u'date'},
                                              {u'type': u'numeric', u'id': u'temperature'},
                                              {u'type': u'text', u'id': u'place'}])

    @httprettified
    def test_simple_tsv_directly(self):
        url = 'http://www.ckan.org/static/simple.tsv'
        HTTPretty.register_uri(HTTPretty.GET, url,
                           body=get_static_file('simple.tsv'),
                           content_type="application/tsv")
        resource_id = self.make_resource_id()

        data = {
            'metadata': {'key': 'value'},
            'apikey': self.api_key,
            'job_type': 'import_into_datastore',
            'data': {
                'url': url,
                'format': 'tsv',
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': resource_id
            }
        }

        ds.import_into_datastore(None, data)

        response = requests.get(
            'http://%s/api/action/datastore_search?resource_id=%s' % (self.host, resource_id),
             headers={"content-type": "application/json"})

        result = json.loads(response.content)

        assert not 'error' in result, result['error']

        value = result['result']['records'][0][u'temperature']
        assert_equal(int(value), 1)
        assert_equal(result['result']['total'], 6)
        assert_equal(result['result']['fields'], [{u'type': u'int4', u'id': u'_id'},
                                              {u'type': u'timestamp', u'id': u'date'},
                                              {u'type': u'numeric', u'id': u'temperature'},
                                              {u'type': u'text', u'id': u'place'}])

    @httprettified
    def test_october_2011_directly(self):
        url = 'http://www.ckan.org/static/october_2011.csv'
        HTTPretty.register_uri(HTTPretty.GET, url,
                           body=get_static_file('october_2011.csv'),
                           content_type="application/csv")
        resource_id = self.make_resource_id()

        data = {
            'metadata': {'key': 'value'},
            'apikey': self.api_key,
            'job_type': 'import_into_datastore',
            'data': {
                'url': url,
                'format': 'csv',
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': resource_id
            }
        }

        ds.import_into_datastore(None, data)

        response = requests.get(
            'http://%s/api/action/datastore_search?resource_id=%s' % (self.host, resource_id),
             headers={"content-type": "application/json"})

        result = json.loads(response.content)

        assert not 'error' in result, result['error']

        value = result['result']['records'][0][u'Supplier Name']
        assert_equal(value, 'ALBANY OFFICE FURNITURE SOLUTIONS')
        assert_equal(result['result']['total'], 230)
        assert_equal(len(result['result']['records']), 100)

        assert_equal(result['result']['fields'], [{u'type': u'int4', u'id': u'_id'},
                                              {u'type': u'text', u'id': u'Directorate'},
                                              {u'type': u'text', u'id': u'Service Area'},
                                              {u'type': u'text', u'id': u'Expenditure Category'},
                                              {u'type': u'timestamp', u'id': u'Payment Date'},
                                              {u'type': u'text', u'id': u'Supplier Name'},
                                              {u'type': u'numeric', u'id': u'Internal Ref'},
                                              {u'type': u'text', u'id': u'Capital/ Revenue'},
                                              {u'type': u'text', u'id': u'Cost Centre'},
                                              {u'type': u'text', u'id': u'Cost Centre Description'},
                                              {u'type': u'float8', u'id': u'Grand Total'}])

    @httprettified
    def test_csv_file(self):
        url = 'http://www.ckan.org/static/simple.csv'
        HTTPretty.register_uri(HTTPretty.GET, url,
                           body=get_static_file('simple.csv'),
                           content_type="application/csv")
        resource_id = self.make_resource_id()

        data = {
            'metadata': {'key': 'value'},
            'apikey': self.api_key,
            'job_type': 'import_into_datastore',
            'data': {
                'url': url,
                'format': 'csv',
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': resource_id
            }
        }

        # good job
        rv = app.post('/job',
                      data=json.dumps(data),
                      content_type='application/json')

        job_status_data = json.loads(rv.data)
        assert 'job_id' in job_status_data, rv.data
        assert not 'error' in job_status_data, rv.data

        time.sleep(1.0)

        response = requests.get(
            'http://%s/api/action/datastore_search?resource_id=%s' % (self.host, resource_id),
             headers={"content-type": "application/json"})

        result = json.loads(response.content)

        assert not 'error' in result, result['error']

        value = result['result']['records'][0][u'temperature']
        assert_equal(int(value), 1)
        assert_equal(result['result']['total'], 6)
        assert_equal(result['result']['fields'], [{u'type': u'int4', u'id': u'_id'},
                                              {u'type': u'timestamp', u'id': u'date'},
                                              {u'type': u'numeric', u'id': u'temperature'},
                                              {u'type': u'text', u'id': u'place'}])
