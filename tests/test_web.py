import os
import json
import uuid
import ConfigParser

import requests

import ckanserviceprototype.web as web

import datastorerservice.datastorer as ds
os.environ['JOB_CONFIG'] = os.path.join(os.path.dirname(__file__),
                                        'test.ini')
import file_server as file_server

try:
    os.remove('/tmp/job_store.db')
except OSError:
    pass
web.configure()
app = web.app.test_client()


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

        if not cls.serving:
                file_server.serve()
                cls.serving = True
                # gets shutdown when nose finishes all tests,
                # so don't restart ever

    def teardown(self):
        self.clean_up()

    def clean_up(self):
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

    def test_csv_file(self):

        data = {'url': 'http://0.0.0.0:50001/static/simple.csv',
                'format': 'csv',
                'id': 'uuid1'}

        context = {'site_url': 'http://%s' % self.host,
                   'site_user_apikey': self.api_key,
                   'apikey': self.api_key}

        resource_id = self.make_resource_id()
        data['id'] = resource_id

        # good job
        rv = app.post('/job',
                      data=json.dumps({"job_type": "upload",
                                       "data": {
                                            'context': json.dumps(context),
                                            'data': json.dumps(data)}}),
                      content_type='application/json')

        assert 'job_id' in json.loads(rv.data)

        response = requests.get(
            'http://%s/api/action/datastore_search?resource_id=%s' % (self.host, resource_id),
             headers={"content-type": "application/json"})

        result = json.loads(response.content)

        value = result['result']['records'][0][u'temperature']
        assert int(value) == 1, value
        assert result['result']['total'] == 6, (result['result']['total'], resource_id)
        assert result['result']['fields'] == [{u'type': u'int4', u'id': u'_id'},
                                              {u'type': u'timestamp', u'id': u'date'},
                                              {u'type': u'numeric', u'id': u'temperature'},
                                              {u'type': u'text', u'id': u'place'}], result['result']['fields']
