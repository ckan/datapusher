# -*- coding: utf-8 -*-
"""Test fetching and parsing various tabular data files.

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
import requests

import datapusher.main as main
import datapusher.jobs as jobs
import ckanserviceprovider.util as util

os.environ['JOB_CONFIG'] = os.path.join(os.path.dirname(__file__),
                                        'settings_test.py')

app = main.serve_test()


def join_static_path(filename):
    return os.path.join(os.path.dirname(__file__), 'static', filename)


def get_static_file(filename):
    return open(join_static_path(filename), 'rb').read()


class TestImport(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        cls.host = 'www.ckan.org'
        cls.api_key = 'my-fake-key'
        cls.resource_id = 'foo-bar-42'

    def register_urls(self, filename='simple.csv', format='CSV',
                      content_type='application/csv',
                      source_url='http://www.source.org/static/file'):
        """Mock some test URLs with httpretty.

        Mocks some URLs related to a data file and a CKAN resource that
        contains the data file, including the URL of the data file itself and
        the resource_show, resource_update and datastore_delete URLs.

        :returns: a 2-tuple containing the URL of the data file itself and the
            resource_show URL for the resource that contains the data file

        """
        # A URL that just returns a static file (simple.csv by default).
        if source_url:
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

    @httpretty.activate
    @raises(util.JobError)
    def test_too_large_content_length(self):
        """It should raise JobError if the returned Content-Length header
        is too large.

        If the returned header is larger than MAX_CONTENT_LENGTH then the async
        background job push_to_datastore should raise JobError
        (ckanserviceprovider will catch this exception and return an error to
        the client).

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

        # Override the source_url (already mocked by self.register_urls()
        # above) with another mock response, this one mocks a response body
        # that's bigger than MAX_CONTENT_LENGTH.
        source_url = 'http://www.source.org/static/file'
        size = jobs.MAX_CONTENT_LENGTH + 1
        httpretty.register_uri(
            httpretty.GET, source_url,
            body='a' * size,
            content_length=size,
            content_type='application/json')

        jobs.push_to_datastore('fake_id', data, True)

    @httpretty.activate
    @raises(util.JobError)
    def test_too_large_file(self):
        """It should raise JobError if the data file is too large.

        If the data file is larger than MAX_CONTENT_LENGTH then the async
        background job push_to_datastore should raise JobError
        (ckanserviceprovider will catch this exception and return an error to
        the client).

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

        # Override the source_url (already mocked by self.register_urls()
        # above) with another mock response, this one mocks a response body
        # that's bigger than MAX_CONTENT_LENGTH.
        source_url = 'http://www.source.org/static/file'
        size = jobs.MAX_CONTENT_LENGTH + 1
        httpretty.register_uri(
            httpretty.GET, source_url,
            body='a' * size,
            content_type='application/json',
            forcing_headers={
                'content-length': None
            })

        jobs.push_to_datastore('fake_id', data, True)

    @httpretty.activate
    def test_content_length_string(self):
        """If the Content-Length header value is a string, just ignore it.
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

        source_url = 'http://www.source.org/static/file'
        httpretty.register_uri(
            httpretty.GET, source_url,
            body='aaaaa',
            content_type='application/json',
            forcing_headers={
                'Content-Length': 'some string'
            })

        jobs.push_to_datastore('fake_id', data, True)

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
        assert_equal(headers, [{'type': 'timestamp', 'id': 'date'},
                               {'type': 'numeric', 'id': 'temperature'},
                               {'type': 'text', 'id': 'place'}])
        assert_equal(len(results), 6)
        assert_equal(
            results[0],
            {'date': datetime.datetime(2011, 1, 1, 0, 0), 'place': 'Galway',
             'temperature': 1})

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
        assert_equal(headers, [{'type': 'timestamp', 'id': 'date'},
                               {'type': 'numeric', 'id': 'temperature'},
                               {'type': 'text', 'id': 'place'}])
        assert_equal(len(results), 6)
        assert_equal(results[0],
                     {'date': datetime.datetime(2011, 1, 1, 0, 0),
                      'place': 'Galway', 'temperature': 1})

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
        assert_equal(headers, [{'type': 'timestamp', 'id': 'date'},
                               {'type': 'numeric', 'id': 'temperature'},
                               {'type': 'text', 'id': 'place'}])
        assert_equal(len(results), 6)
        assert_equal(results[0],
                     {'date': datetime.datetime(2011, 1, 1, 0, 0),
                      'place': 'Galway', 'temperature': 1})

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
        assert_equal(headers, [{'type': 'timestamp', 'id': 'date'},
                               {'type': 'numeric', 'id': 'temperature'},
                               {'type': 'text', 'id': 'place'}])
        assert_equal(len(results), 6)
        assert_equal(results[0],
                     {'date': datetime.datetime(2011, 1, 1, 0, 0),
                      'place': 'Galway', 'temperature': 1})

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
        assert_equal(headers, [{'type': 'text', 'id': 'Directorate'},
                               {'type': 'text', 'id': 'Service Area'},
                               {'type': 'text', 'id': 'Expenditure Category'},
                               {'type': 'timestamp', 'id': 'Payment Date'},
                               {'type': 'text', 'id': 'Supplier Name'},
                               {'type': 'numeric', 'id': 'Internal Ref'},
                               {'type': 'text', 'id': 'Capital/ Revenue'},
                               {'type': 'text', 'id': 'Cost Centre'},
                               {'type': 'text',
                                'id': 'Cost Centre Description'},
                               {'type': 'numeric', 'id': 'Grand Total'}])
        assert_equal(len(results), 230)
        assert_equal(results[0],
                     {'Directorate': 'Adult and Culture',
                      'Service Area': 'Ad Serv-Welfare Rights-    ',
                      'Expenditure Category': 'Supplies & Services',
                      'Cost Centre Description':
                      'WELFARE RIGHTS WORKERS       M',
                      'Capital/ Revenue': 'Revenue',
                      'Grand Total': 828.0,
                      'Payment Date': datetime.datetime(2011, 10, 24, 0, 0),
                      'Internal Ref': 5277184,
                      'Cost Centre': '1MR48',
                      'Supplier Name': 'ALBANY OFFICE FURNITURE SOLUTIONS'})

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
        assert_equal(headers[0]['id'].strip(), '1985')
        assert_equal(results[1]['1993'].strip(), '379')

    @raises(util.JobError)
    @httpretty.activate
    def test_bad_url(self):
        """It should raise HTTPError(JobError) if the resource.url is badly
        formed.

        (ckanserviceprovider will catch this exception and return an error to
        the client).

        """
        self.register_urls(source_url='http://url-badly-formed')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        jobs.push_to_datastore('fake_id', data, True)

    @raises(util.JobError)
    @httpretty.activate
    def test_bad_scheme(self):
        """It should raise HTTPError(JobError) if the resource.url is an
        invalid scheme.

        (ckanserviceprovider will catch this exception and return an error to
        the client).

        """
        self.register_urls(source_url='invalid://example.com')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        jobs.push_to_datastore('fake_id', data, True)

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

    @httpretty.activate
    def test_do_not_push_when_same_hash(self):
        """A file should not be pushed if it hasn't changed.

        If a resource's file has already been added to the datastore and then
        the datapusher's push_to_datastore job fetchess and parses it again
        and the file has not changed, then push_to_datastore should return
        None rather than parsing the file and returning headers and rows.

        FIXME:
        This relies on a return statement early in the push_to_datastore
        function, this doesn't seem like a great way to test that the file
        was not pushed.

        """
        source_url, res_url = self.register_urls()
        httpretty.register_uri(
            httpretty.POST, res_url,
            body=json.dumps({
                'success': True,
                'result': {
                    'id': '32h4345k34h5l345',
                    'name': 'short name',
                    'url': source_url,
                    'format': 'csv',
                    'hash': '0ccb75d277ec2da41faae58642e3fb11'
                }
            }),
            content_type='application/json')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        res = jobs.push_to_datastore('fake_id', data, True)
        # res should be None because we didn't get to the part that
        # returns something
        assert not res, res
