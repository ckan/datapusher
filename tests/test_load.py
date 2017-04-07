# -*- coding: utf-8 -*-
"""Test load of tabular data files using pgloader

This just tests the push_to_datastore job's fetching, detection of headers and
actually pushing the data into the datastore.
"""
import os
import json
import unittest
import datetime
from decimal import Decimal

from nose.tools import assert_equal, raises, assert_not_in
import httpretty
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import select

import datapusher.main as main
import datapusher.jobs as jobs
import ckanserviceprovider.util as util
from ckanserviceprovider import web
from ckanserviceprovider import db as ckan_service_provider_db
from ckanext.datastore import db
try:
    from collections import OrderedDict  # from python 2.7
except ImportError:
    from sqlalchemy.util import OrderedDict

web.app.config['USE_PGLOADER'] = True

os.environ['JOB_CONFIG'] = os.path.join(os.path.dirname(__file__),
                                        'settings_test.py')

app = main.serve_test()


def join_static_path(filename):
    return os.path.join(os.path.dirname(__file__), 'static', filename)


def get_static_file(filename):
    return open(join_static_path(filename)).read()

def assert_equal_list(a, b):
    if a != b:
        min_length = min(len(a), len(b))
        max_length = max(len(a), len(b))
        for i in range(max_length):
            if i <= min_length:
                print '=' if a[i] == b[i] else '!', a[i], '\t\t', b[i]
            elif len(a) > len(b):
                print '!', a[i]
            else:
                print '!', '\t\t', a[i]

class Logs(list):
    def get_errors(self):
        return [message for level, message in self
                if level == 'ERROR']

    def grep(self, text):
        return [message for level, message in self
                if text in message]

    def assert_no_errors(self):
        errors = self.get_errors()
        assert not errors, errors


class TestImport(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        cls.host = 'www.ckan.org'
        cls.api_key = 'my-fake-key'
        cls.resource_id = 'foo-bar-42'
        # drop test table
        engine, conn = cls.get_datastore_engine_and_connection()
        conn.execute('DROP TABLE IF EXISTS "{}"'.format(cls.resource_id))

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
                                       'id': self.resource_id,
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

        # Create a table
        def mock_datastore_create(request, uri, headers):
            '''Creates test table in postgres (datastore)

            By mocking this we saving starting up ckan. Creating the table
            isn't the thing we're interested in testing here.'''
            context = {}
            data_dict = {
                'resource_id': request.parsed_body['resource_id'],
                'fields': request.parsed_body['fields'],
                'connection_url':
                    web.app.config.get('CKAN_DATASTORE_WRITE_URL'),
                    }
            try:
                result = db.create(context, data_dict)
            except db.InvalidDataError as err:
                raise p.toolkit.ValidationError(unicode(err))
            engine, conn = self.get_datastore_engine_and_connection()
            meta = MetaData(bind=engine, reflect=True)
            table = Table(self.resource_id, meta,
                          autoload=True, autoload_with=engine)
            return (200, headers, json.dumps({'success': True}))
        httpretty.register_uri(
            httpretty.POST,
            'http://www.ckan.org/api/3/action/datastore_create',
            body=mock_datastore_create)

        # A URL that mocks checking if a datastore table exists and return
        # no.
        datastore_check_url = \
            'http://www.ckan.org/api/3/action/datastore_search'
        httpretty.register_uri(httpretty.POST, datastore_check_url,
                               status=404)
                               # body=json.dumps({'success': True}),
                               # content_type='application/json')

        return source_url, res_url

    @classmethod
    def get_datastore_engine_and_connection(cls):
        if '_datastore' not in dir(cls):
            datastore_postgres_url = \
                web.app.config.get('CKAN_DATASTORE_WRITE_URL')
            engine = create_engine(datastore_postgres_url, echo=False)
            conn = engine.connect()
            cls._datastore = (engine, conn)
        return cls._datastore

    def get_datastore_table(self):
        engine, conn = self.get_datastore_engine_and_connection()
        meta = MetaData(bind=engine, reflect=True)
        table = Table(self.resource_id, meta,
                      autoload=True, autoload_with=engine)
        s = select([table])
        result = conn.execute(s)
        return dict(
            num_rows=result.rowcount,
            headers=result.keys(),
            header_dict=OrderedDict([(c.key, str(c.type))
                                    for c in table.columns]),
            rows=result.fetchall(),
            )

    def get_load_logs(self, task_id):
        conn = ckan_service_provider_db.ENGINE.connect()
        logs = ckan_service_provider_db.LOGS_TABLE
        result = conn.execute(select([logs.c.level, logs.c.message])
                              .where(logs.c.job_id == task_id))
        return Logs(result.fetchall())

    # KEEP - NOT RELATED TO PGLOADER
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
            content_length=size,
            content_type='application/json')

        jobs.push_to_datastore('fake_id', data, True)

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

        jobs.push_to_datastore('fake_id', data)
        data = self.get_datastore_table()
        assert_equal(data['headers'],
                     ['_id', '_full_text', 'date', 'temperature', 'place'])
        assert_equal(data['header_dict']['date'],
                     'TIMESTAMP WITHOUT TIME ZONE')
        assert_equal(data['header_dict']['temperature'], 'NUMERIC')
        assert_equal(data['header_dict']['place'], 'TEXT')
        assert_equal(data['num_rows'], 6)
        assert_equal(data['rows'][0][2:],
                     (datetime.datetime(2011, 1, 1), Decimal(1), 'Galway'))

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

        jobs.push_to_datastore('fake_id', data)
        data = self.get_datastore_table()
        assert_equal(data['headers'],
                     ['_id', '_full_text', 'date', 'temperature', 'place'])
        assert_equal(data['header_dict']['date'],
                     'TIMESTAMP WITHOUT TIME ZONE')
        assert_equal(data['header_dict']['temperature'], 'NUMERIC')
        assert_equal(data['header_dict']['place'], 'TEXT')
        assert_equal(data['num_rows'], 6)
        assert_equal(data['rows'][0][2:],
                     (datetime.datetime(2011, 1, 1), Decimal(1), 'Galway'))

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

        jobs.push_to_datastore('fake_id', data)
        data = self.get_datastore_table()
        assert_equal(data['headers'],
                     ['_id', '_full_text', 'date', 'temperature', 'place'])
        assert_equal(data['header_dict']['date'],
                     'TIMESTAMP WITHOUT TIME ZONE')
        assert_equal(data['header_dict']['temperature'], 'NUMERIC')
        assert_equal(data['header_dict']['place'], 'TEXT')
        assert_equal(data['num_rows'], 6)
        assert_equal(data['rows'][0][2:],
                     (datetime.datetime(2011, 1, 1), Decimal(1), 'Galway'))

    # DOESNT USE PGLOADER yet
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
        self.register_urls('spend_defra_jan_17.csv', 'csv')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        jobs.push_to_datastore('fake_id', data)

        logs = self.get_load_logs('fake_id')
        errors = logs.get_errors()
        assert_equal(errors[0], u'ERROR Database error 22008: date/time field value out of range: "19/01/2017"HINT: Perhaps you need a different "datestyle" setting.')
        # it will do allow 21 or 25 rejected rows before it gives up
        assert_equal(errors[-1][2:], u' rows were rejected: 2, 3, 4, 5, 6 etc. The errors related to these columns: Date')

        data = self.get_datastore_table()
        assert_equal_list(
            data['headers'],
            ['_id', '_full_text', 'Directorate', 'Service Area',
             'Expenditure Category', 'Payment Date', 'Supplier Name',
             'Internal Ref', 'Capital/ Revenue', 'Cost Centre',
             'Cost Centre Description', 'Grand Total'])
        assert_equal(data['header_dict']['Directorate'], 'TEXT')
        assert_equal(data['header_dict']['Payment Date'],
                     'TIMESTAMP WITHOUT TIME ZONE')
        assert_equal(data['header_dict']['Internal Ref'], 'NUMERIC')
        assert_equal(data['num_rows'], 230)
        assert_equal(data['rows'][0][2:],
                     (u'Adult and Culture',
                      u'Ad Serv-Welfare Rights-    ',
                      u'Supplies & Services',
                      u'WELFARE RIGHTS WORKERS       M',
                      u'Revenue',
                      Decimal(828.0),
                      datetime.datetime(2011, 10, 24, 0, 0),
                      Decimal(5277184),
                      u'1MR48',
                      u'ALBANY OFFICE FURNITURE SOLUTIONS'))

    @httpretty.activate
    def test_csv_encoding_issue(self):
        """Test fetching and parsing a more realistic CSV file.

        When given dry_run=True and a resource with a CSV file, the
        push_to_datastore job should return the right headers and rows from the
        CSV file.

        """
        self.register_urls('spend_co_feb_17.csv', 'csv')
        data = {
            'api_key': self.api_key,
            'job_type': 'push_to_datastore',
            'metadata': {
                'ckan_url': 'http://%s/' % self.host,
                'resource_id': self.resource_id
            }
        }

        jobs.push_to_datastore('fake_id', data)

        logs = self.get_load_logs('fake_id')
        errors = logs.get_errors()

        # TODO
        #assert_equal(errors[0], u'ERROR Database error 22008: date/time field value out of range: "19/01/2017"HINT: Perhaps you need a different "datestyle" setting.')
        #assert_equal(errors[-1][2:], u' rows were rejected: 2, 3, 4, 5, 6 etc. The errors related to these columns: Date')

    @httpretty.activate
    def test_csv_with_commas_in_decimal(self):
        """Test fetching and parsing a CSV file made difficult by numbers like
        "6,200" which postgres will reject.
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

        jobs.push_to_datastore('fake_id', data)

        logs = self.get_load_logs('fake_id')
        errors = logs.get_errors()
        assert_equal(errors[0], u'ERROR Database error 22P02: invalid input syntax for type numeric: "6,200.00"CONTEXT: COPY foo-bar-42, line 5, column Grand Total: "6,200.00"')
        # it will do allow 20 odd rejected rows before we kill it
        assert_equal(errors[-2][2:], u' rows were rejected: 8, 11, 12, 14, 15 etc. The errors related to these columns: Grand Total')
        assert_equal(errors[-1], u'pgloader summary not found - this happens after errors and it gets killed. Rather than leave only a small fraction of the data in DataStore, remove it all.')


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

    # KEEP - NOT RELATED TO PGLOADER
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
                    'id': self.resource,
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
