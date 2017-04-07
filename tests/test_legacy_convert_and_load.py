# -*- coding: utf-8 -*-
"""Test DEPRECATED "convert_and_load" of tabular data files
(i.e. not using pgloader)

This just tests the push_to_datastore job's fetching and parsing of the files,
it does not actually test pushing the data into the datastore.

FIXME: These tests use push_to_datastore's dry_run=True argument to have it
just return the parsed data file headers and rows rather than pushing them to
the datastore. Why not just mock the datastore's URL with httpretty, and test
that the right values were pushed?

"""
import os
import json
import unittest
import datetime
from nose.tools import assert_equal, raises

import httpretty

import datapusher.main as main
import datapusher.jobs as jobs
import ckanserviceprovider.util as util
from ckanserviceprovider import web


web.app.config['USE_PGLOADER'] = False

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
        cls.api_key = 'my-fake-key'
        cls.resource_id = 'foo-bar-42'

    def register_urls(self, filename='simple.csv', format='CSV',
                      content_type='application/csv'):
        """Mock some test URLs with httpretty.

        Mocks some URLs related to a data file and a CKAN resource that
        contains the data file, including the URL of the data file itself and
        the resource_show, resource_update and datastore_delete URLs.

        :returns: a 2-tuple containing the URL of the data file itself and the
            resource_show URL for the resource that contains the data file

        """
        # A URL that just returns a static file (simple.csv by default).
        source_url = 'http://www.source.org/static/file'
        httpretty.register_uri(httpretty.GET, source_url,
                               body=get_static_file(filename),
                               content_type=content_type)

        # A URL that mocks CKAN's resource_show API.
        res_url = 'http://www.ckan.org/api/3/action/resource_show'
        httpretty.register_uri(httpretty.POST, res_url,
                               body=json.dumps({
                                   'success': True,
                                   'result': {
                                       'id': '32h4345k34h5l345',
                                       'name': 'short name',
                                       'url': source_url,
                                       'format': format
                                   }
                               }),
                               content_type='application/json')

        # A URL that mocks the response that CKAN's resource_update API would
        # give after successfully upddating a resource.
        resource_update_url = (
            'http://www.ckan.org/api/3/action/resource_update')
        httpretty.register_uri(httpretty.POST, resource_update_url,
                               body=json.dumps({'success': True}),
                               content_type='application/json')

        # A URL that mock's the response that CKAN's datastore plugin's
        # datastore_delete API would give after successfully deleting a
        # resource from the datastore.
        datastore_del_url = 'http://www.ckan.org/api/3/action/datastore_delete'
        httpretty.register_uri(httpretty.POST, datastore_del_url,
                               body=json.dumps({'success': True}),
                               content_type='application/json')


        # A URL that mocks checking if a datastore table exists
        datastore_check_url = 'http://www.ckan.org/api/3/action/datastore_search'
        httpretty.register_uri(httpretty.POST, datastore_check_url,
                               body=json.dumps({'success': True}),
                               content_type='application/json')


        return source_url, res_url

    # FIXME: Docstring
    @httpretty.activate
    def test_delete_404(self):
        self.register_urls()

        # Override the mocked datastore_delete URL with another mock response
        # that returns a 404.
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

        headers, results = jobs.push_to_datastore('fake_id', data, True)

        # FIXME: Shouldn't we be testing something here??

    @httpretty.activate
    def test_simple_csv(self):
        """Test successfully fetching and parsing a simple CSV file.

        When given dry_run=True and a resource with a simple CSV file the
        push_to_datastore job should fetch and parse the file and return the
        right headers and data rows from the file.

        """
        self.register_urls()
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore('fake_id', data, True)
        results = list(results)
        assert_equal(headers, [{'type': 'timestamp', 'id': u'date'},
                               {'type': 'numeric', 'id': u'temperature'},
                               {'type': 'text', 'id': u'place'}])
        assert_equal(len(results), 6)
        assert_equal(
            results[0],
            {u'date': datetime.datetime(2011, 1, 1, 0, 0), u'place': u'Galway',
             u'temperature': 1})

    @httpretty.activate
    def test_simple_tsv(self):
        """Test successfully fetching and parsing a simple TSV file.

        When given dry_run=True and a resource with a simple TSV
        (tab-separated values) file the push_to_datastore job should fetch and
        parse the file and return the right headers and data rows from the
        file.

        """
        self.register_urls('simple.tsv', 'tsv', 'application/csv')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore('fake_id', data, True)
        results = list(results)
        assert_equal(headers, [{'type': 'timestamp', 'id': u'date'},
                               {'type': 'numeric', 'id': u'temperature'},
                               {'type': 'text', 'id': u'place'}])
        assert_equal(len(results), 6)
        assert_equal(results[0],
                     {u'date': datetime.datetime(2011, 1, 1, 0, 0),
                      u'place': u'Galway', u'temperature': 1})

    @httpretty.activate
    def test_simple_ssv(self):
        """Test successfully fetching and parsing a simple SSV file.

        When given dry_run=True and a resource with a simple SSV
        (semicolon-separated values) file the push_to_datastore job should
        fetch and parse the file and return the right headers and data rows
        from the file.

        """
        self.register_urls('simple.ssv', 'csv', 'application/csv')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore('fake_id', data, True)
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
        """Test successfully fetching and parsing a simple XLS file.

        When given dry_run=True and a resource with a simple XLS (Excel) file
        the push_to_datastore job should fetch and parse the file and return
        the right headers and data rows from the file.

        """
        self.register_urls('simple.xls', 'xls', 'application/vnd.ms-excel')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore('fake_id', data, True)
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
        """Test fetching and parsing a more realistic CSV file.

        When given dry_run=True and a resource with a CSV file, the
        push_to_datastore job should return the right headers and rows from the
        CSV file.

        """
        self.register_urls('october_2011.csv', 'csv')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore('fake_id', data, True)
        results = list(results)
        assert_equal(headers, [{'type': 'text', 'id': u'Directorate'},
                               {'type': 'text', 'id': u'Service Area'},
                               {'type': 'text', 'id': u'Expenditure Category'},
                               {'type': 'timestamp', 'id': u'Payment Date'},
                               {'type': 'text', 'id': u'Supplier Name'},
                               {'type': 'numeric', 'id': u'Internal Ref'},
                               {'type': 'text', 'id': u'Capital/ Revenue'},
                               {'type': 'text', 'id': u'Cost Centre'},
                               {'type': 'text',
                                'id': u'Cost Centre Description'},
                               {'type': 'numeric', 'id': u'Grand Total'}])
        assert_equal(len(results), 230)
        assert_equal(results[0],
                     {u'Directorate': u'Adult and Culture',
                      u'Service Area': u'Ad Serv-Welfare Rights-    ',
                      u'Expenditure Category': u'Supplies & Services',
                      u'Cost Centre Description':
                      u'WELFARE RIGHTS WORKERS       M',
                      u'Capital/ Revenue': u'Revenue',
                      u'Grand Total': 828.0,
                      u'Payment Date': datetime.datetime(2011, 10, 24, 0, 0),
                      u'Internal Ref': 5277184,
                      u'Cost Centre': u'1MR48',
                      u'Supplier Name': u'ALBANY OFFICE FURNITURE SOLUTIONS'})

    @httpretty.activate
    def test_weird_header(self):
        """Test fetching and parsing a CSV file with "weird" header padding.

        When given dry_run=True and a resource with a CSV file with weird
        header padding the push_to_datastore job should return the right
        headers and rows from the CSV file.

        """
        self.register_urls('weird_head_padding.csv', 'csv')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore('fake_id', data, True)
        results = list(results)
        assert_equal(len(headers), 9)
        assert_equal(len(results), 82)
        assert_equal(headers[0]['id'].strip(), u'1985')
        assert_equal(results[1]['1993'].strip(), u'379')

    @httpretty.activate
    def test_mostly_numbers(self):
        """Test fetching and parsing a CSV file that contains mostly numbers.

        When given dry_run=True and a resource with a CSV file that contains
        mostly numbers the push_to_datastore job should return the right
        headers and rows from the CSV file.

        """
        self.register_urls('mixedGLB.csv')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore('fake_id', data, True)
        results = list(results)
        assert_equal(len(headers), 19)
        assert_equal(len(results), 133)

    @httpretty.activate
    def test_long_file(self):
        """Test fetching and parsing a long CSV file.

        When given dry_run=True and a resource with a long CSV file the
        push_to_datastore job should return the right number of headers and
        rows from the CSV file.

        """
        self.register_urls('long.csv', 'csv')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        headers, results = jobs.push_to_datastore('fake_id', data, True)
        results = list(results)
        assert_equal(len(headers), 1)
        assert_equal(len(results), 4000)

