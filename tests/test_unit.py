import json
import unittest

from nose.tools import assert_equal

from httpretty import HTTPretty
from httpretty import httprettified

import datapusher.jobs as jobs
import ckanserviceprovider.util as util


class TestMethods(unittest.TestCase):
    def test_chuncky(self):
        r = jobs.chunky('abcdefg', 3)
        l = list(r)
        assert_equal(l, [['a', 'b', 'c'], ['d', 'e', 'f'], ['g']])

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
