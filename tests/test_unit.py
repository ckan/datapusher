# -*- coding: utf-8 -*-
'''
Test individual functions
'''

import json
import unittest
import requests

from nose.tools import assert_equal, raises

import httpretty

import datapusher.jobs as jobs
import ckanserviceprovider.util as util


class TestChunky():
    def test_simple(self):
        chunks = jobs.chunky('abcdefg', 3)
        assert_equal(
            list(chunks),
            [
                (['a', 'b', 'c'], False),
                (['d', 'e', 'f'], False),
                (['g'], True)
             ])

    def test_length_is_the_exact_multiple(self):
        chunks = jobs.chunky('abcdef', 3)
        assert_equal(
            list(chunks),
            [
                (['a', 'b', 'c'], False),
                (['d', 'e', 'f'], True),
             ])

    def test_empty(self):
        chunks = jobs.chunky('', 3)
        assert_equal(
            list(chunks), [])


class TestGetUrl():
    def test_get_action_url(self):
        assert_equal(
            jobs.get_url('datastore_create', 'http://www.ckan.org'),
            'http://www.ckan.org/api/3/action/datastore_create')

    def test_get_action_url_with_stuff(self):
        assert_equal(
            jobs.get_url('datastore_create', 'http://www.ckan.org/'),
            'http://www.ckan.org/api/3/action/datastore_create')

    def test_get_action_url_with_https(self):
        assert_equal(
            jobs.get_url('datastore_create', 'https://www.ckan.org/'),
            'https://www.ckan.org/api/3/action/datastore_create')

    def test_get_action_url_missing_http(self):
        assert_equal(
            jobs.get_url('datastore_create', 'www.ckan.org/'),
            'http://www.ckan.org/api/3/action/datastore_create')


class TestValidation(unittest.TestCase):
    def test_validate_input(self):
        jobs.validate_input({
            'metadata': {
                'resource_id': 'h32jk4h34k5',
                'ckan_url': 'http://www.ckan.org'
            },
            'api_key': 'köi'
        })

    @raises(util.JobError)
    def test_validate_input_raises_if_metadata_missing(self):
        jobs.validate_input({
            'foo': {},
            'api_key': 'my-key'
        })

    @raises(util.JobError)
    def test_validate_input_raises_if_res_id_missing(self):
        jobs.validate_input({
            'metadata': {
                'ckan_url': 'http://www.ckan.org'
            },
            'api_key': 'my-key'
        })

    @raises(util.JobError)
    def test_validate_input_raises_if_ckan_url_missing(self):
        jobs.validate_input({
            'metadata': {
                'resource_id': 'h32jk4h34k5'
            },
            'api_key': 'my-key'
        })

    @raises(util.JobError)
    def test_validate_api_key(self):
        jobs.validate_input({
            'metadata': {
                'resource_id': 'h32jk4h34k5',
                'ckan_url': 'http://www.ckan.org'
            }
        })


class TestCkanActionCalls(unittest.TestCase):
    @httpretty.activate
    def test_get_resource(self):
        url = 'http://www.ckan.org/api/3/action/resource_show'
        httpretty.register_uri(httpretty.POST, url,
                               body=json.dumps({
                                   'success': True,
                                   'result': {
                                       'foo': 42
                                   }}),
                               content_type="application/json")
        resource = jobs.get_resource('an_id', 'http://www.ckan.org/', None)
        assert_equal(resource, {'foo': 42})
        assert json.loads(httpretty.last_request().body)['id'] == 'an_id'

    @httpretty.activate
    def test_delete_datastore(self):
        url = 'http://www.ckan.org/api/3/action/datastore_delete'
        httpretty.register_uri(httpretty.POST, url,
                               body='{"success": true}',
                               content_type="application/json")
        jobs.delete_datastore_resource('an_id', 'my_key', 'http://www.ckan.org/')
        assert json.loads(httpretty.last_request().body)['id'] == 'an_id'

    @httpretty.activate
    def test_resource_update(self):
        url = 'http://www.ckan.org/api/3/action/resource_update'
        httpretty.register_uri(httpretty.POST, url,
                               body='{"success": true}',
                               content_type="application/json")
        jobs.update_resource({'foo': 42}, 'my_key', 'http://www.ckan.org/')
        assert json.loads(httpretty.last_request().body)['url_type'] == 'datapusher'

    @httpretty.activate
    def test_datastore_resource_exists(self):
        ckan_url = 'http://www.ckan.org'
        url = '{0}/api/3/action/datastore_search'.format(ckan_url)
        httpretty.register_uri(httpretty.POST, url,
                               content_type="application/json",
                               responses=[
                                   httpretty.Response(body='{"success": true}', status=200),
                                   httpretty.Response(body='{"success": false}', status=404),
                               ])

        assert jobs.datastore_resource_exists('found', 'api-key', ckan_url)
        assert not jobs.datastore_resource_exists('not-found', 'api-key', ckan_url)

    @httpretty.activate
    def test_send_resource_to_datastore(self):
        url = 'http://www.ckan.org/api/3/action/datastore_create'
        httpretty.register_uri(httpretty.POST, url,
                               body='{"success": true}',
                               content_type="application/json")
        jobs.send_resource_to_datastore({'id': 'an_id'}, [], [], False, 'my_key', 'http://www.ckan.org/')


class TestCheckResponse(unittest.TestCase):
    """Unit tests for the check_response() function."""

    @httpretty.activate
    def test_text_409_with_non_json_response(self):
        """It should raise HTTPError for a 409 with a non-JSON body."""
        url = 'http://www.ckan.org/'
        httpretty.register_uri(httpretty.GET, url,
                               body="This is someone's text. With ümlauts.",
                               content_type='html/text',
                               status=409)
        r = requests.get('http://www.ckan.org/')
        try:
            jobs.check_response(r, 'http://www.ckan.org/', 'Me')
            assert False, "check_response() should have raised an exception."
        except jobs.HTTPError as err:
            assert err.status_code == 409
            assert err.request_url == url

    @httpretty.activate
    def test_text_200(self):
        httpretty.register_uri(httpretty.GET, 'http://www.ckan.org/',
                               body='{"success": true}',
                               content_type='html/text',
                               status=200)
        r = requests.get('http://www.ckan.org/')
        jobs.check_response(r, 'http://www.ckan.org/', 'Me')

    @httpretty.activate
    def test_text_500_with_false_success(self):
        """It should raise HTTPError if given a 500 with "success": false."""
        url = 'http://www.ckan.org/'
        httpretty.register_uri(httpretty.GET, url,
                               body='{"success": false}',
                               content_type='html/text',
                               status=500)
        r = requests.get('http://www.ckan.org/')
        try:
            jobs.check_response(r, url, 'Me')
            assert False, "check_response() should have raised an exception"
        except jobs.HTTPError as err:
            assert err.response == '{"success": false}'
            assert err.status_code == 500
            assert err.request_url == url

    @httpretty.activate
    @raises(util.JobError)
    def test_text_404(self):
        httpretty.register_uri(httpretty.GET, 'http://www.ckan.org/',
                               body='{"success": true}',
                               content_type='html/text',
                               status=404)
        r = requests.get('http://www.ckan.org/')
        jobs.check_response(r, 'http://www.ckan.org/', 'Me')

    @httpretty.activate
    def test_text_404_ignore(self):
        httpretty.register_uri(httpretty.GET, 'http://www.ckan.org/',
                               body='{"success": true}',
                               content_type='html/text',
                               status=404)
        r = requests.get('http://www.ckan.org/')
        jobs.check_response(r, 'http://www.ckan.org/', 'Me', good_status=(200, 201, 404))
