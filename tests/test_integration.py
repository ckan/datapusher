'''
Test the whole process. This requires a running CKAN instance
with the datastore activated.
'''

import os
import json
import uuid

from nose import SkipTest
from nose.tools import assert_equal
import requests

import httpretty

import ckanserviceprovider.web as web
import datapusher.main as main
import datapusher.jobs as jobs

import settings_test as config

os.environ['JOB_CONFIG'] = os.path.join(os.path.dirname(__file__),
                                        'settings_test.py')

web.configure()
app = main.serve_test()


def join_static_path(filename):
    return os.path.join(os.path.dirname(__file__), 'static', filename)


def get_static_file(filename):
    return open(join_static_path(filename)).read()


class TestImport():
    resource_ids = []

    @classmethod
    def setup_class(cls):
        try:
            r = requests.get('http://{0}/api/3/action/datastore_search?resource_id=_table_metadata'.format(config.CKAN_HOST))
            if r.status_code not in [200, 201]:
                raise SkipTest("Need a CKAN with the datastore enabled")
        except requests.ConnectionError:
            raise SkipTest("No CKAN running")
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
            r = requests.post('http://%s/api/3/action/datastore_delete' % self.host,
                              data=json.dumps(request),
                              headers={'Content-Type': 'application/json',
                                       'Authorization': self.api_key}
                              )
            if r.status_code not in [200, 404]:
                raise Exception('Error deleting datastore for resource %s' % res_id)

    def make_resource_id(self, url):
        ''' Create a resource in ckan and get back the id
        '''
        r = requests.post(
            'http://%s/api/3/action/package_create' % self.host,
            data=json.dumps(
                {'name': str(uuid.uuid4()),
                 'resources': [{'url': url, 'format': 'csv'}]}
            ),
            headers={'Authorization': self.api_key, 'content-type': 'application/json'}
        )
        if r.status_code != 200:
                raise Exception('Error creating datastore for resource. Check the CKAN output.')

        res_id = json.loads(r.content)['result']['resources'][0]['id']
        self.resource_ids.append(res_id)
        return res_id

    @httpretty.activate
    def test_simple_csv_directly(self):
        url = 'http://www.ckan.org/static/simple.csv'
        httpretty.register_uri(httpretty.GET, url,
                               body=get_static_file('simple.csv'),
                               content_type="application/csv")
        resource_id = self.make_resource_id(url)

        data = {
            'apikey': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': resource_id
            }
        }

        jobs.push_to_datastore(None, data)

        response = requests.get(
            'http://%s/api/action/datastore_search?resource_id=%s' % (self.host, resource_id),
            headers={"content-type": "application/json"})

        result = json.loads(response.content)

        assert not 'error' in result, result['error']

        value = result['result']['records'][0][u'temperature']
        assert_equal(int(value), 1)
        assert_equal(result['result']['total'], 6)
        assert_equal(result['result']['fields'],
                     [{u'type': u'int4', u'id': u'_id'},
                      {u'type': u'timestamp', u'id': u'date'},
                      {u'type': u'numeric', u'id': u'temperature'},
                      {u'type': u'text', u'id': u'place'}])
