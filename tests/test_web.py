import os
import json
import uuid
import time
import ConfigParser

import requests
from httpretty import HTTPretty
from httpretty import httprettified

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


def join_static_path(filename):
    return os.path.join(os.path.dirname(__file__), 'static', filename)


def get_static_file(filename):
    return open(join_static_path(filename)).read()


class TestWeb():
    serving = False
    resource_ids = []

    @classmethod
    def setup_class(cls):
        config = ConfigParser.ConfigParser()
        config_file = os.environ.get('JOB_CONFIG')
        config.read(config_file)

        cls.host = config.get('app:ckan', 'ckan_host')
        cls.api_key = config.get('app:ckan', 'user_api_key')

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
            if r.status_code != 200 and r.status_code != 404:
                raise Exception('Error deleting datastore for resource %s') % res_id

    def make_resource_id(self):
        ''' Create a resource in ckan and get back the id
        '''
        response = requests.post(
            'http://%s/api/action/package_create' % self.host,
            data=json.dumps(
                {'name': str(uuid.uuid4()),
                 'resources': [{u'url': u'test'}]}
            ),
            headers={'Authorization': self.api_key, 'content-type': 'application/json'}
        )
        res_id = json.loads(response.content)['result']['resources'][0]['id']

        self.resource_ids.append(res_id)

        return res_id

    def test_status(self):
        rv = app.get('/status')
        assert json.loads(rv.data) == dict(version=0.1,
                                           job_types=['upload'],
                                           name='datastorer'), rv.data

    @httprettified
    def test_csv_directly(self):
        url = 'http://www.ckan.org/static/simple.csv'
        HTTPretty.register_uri(HTTPretty.GET, url,
                           body=get_static_file('simple.csv'),
                           content_type="application/csv")
        resource_id = self.make_resource_id()

        data = {
            'metadata': {'key': 'value'},
            'apikey': self.api_key,
            'job_type': 'upload',
            'data': {
                'url': url,
                'format': 'csv',
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': resource_id
            }
        }

        ds.upload(None, data)

        response = requests.get(
            'http://%s/api/action/datastore_search?resource_id=%s' % (self.host, resource_id),
             headers={"content-type": "application/json"})

        result = json.loads(response.content)

        assert not 'error' in result, result['error']

        value = result['result']['records'][0][u'temperature']
        assert int(value) == 1, value
        assert result['result']['total'] == 6, (result['result']['total'], resource_id)
        assert result['result']['fields'] == [{u'type': u'int4', u'id': u'_id'},
                                              {u'type': u'timestamp', u'id': u'date'},
                                              {u'type': u'numeric', u'id': u'temperature'},
                                              {u'type': u'text', u'id': u'place'}], result['result']['fields']

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
            'job_type': 'upload',
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

        time.sleep(0.2)

        response = requests.get(
            'http://%s/api/action/datastore_search?resource_id=%s' % (self.host, resource_id),
             headers={"content-type": "application/json"})

        result = json.loads(response.content)

        assert not 'error' in result, result['error']

        value = result['result']['records'][0][u'temperature']
        assert int(value) == 1, value
        assert result['result']['total'] == 6, (result['result']['total'], resource_id)
        assert result['result']['fields'] == [{u'type': u'int4', u'id': u'_id'},
                                              {u'type': u'timestamp', u'id': u'date'},
                                              {u'type': u'numeric', u'id': u'temperature'},
                                              {u'type': u'text', u'id': u'place'}], result['result']['fields']
