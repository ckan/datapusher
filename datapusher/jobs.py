# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import urllib2
import socket
import requests
import urlparse
import itertools
import datetime
import locale
import pprint
import logging
import decimal
import hashlib
import cStringIO
import time

import messytables
from slugify import slugify

import ckanserviceprovider.job as job
import ckanserviceprovider.util as util
from ckanserviceprovider import web

if not locale.getlocale()[0]:
    locale.setlocale(locale.LC_ALL, '')

MAX_CONTENT_LENGTH = web.app.config.get('MAX_CONTENT_LENGTH') or 10485760
SSL_VERIFY = web.app.config.get('SSL_VERIFY', True)

# Added to disable InsecureRequestWarning
# link: https://urllib3.readthedocs.org/en/latest/security.html#insecurerequestwarning
if not SSL_VERIFY:
    requests.packages.urllib3.disable_warnings()

DOWNLOAD_TIMEOUT = 30

_TYPE_MAPPING = {
    'String': 'text',
    # 'int' may not be big enough,
    # and type detection may not realize it needs to be big
    'Integer': 'numeric',
    'Decimal': 'numeric',
    'DateUtil': 'timestamp'
}

_TYPES = [messytables.StringType, messytables.DecimalType,
          messytables.IntegerType, messytables.DateUtilType]

TYPE_MAPPING = web.app.config.get('TYPE_MAPPING', _TYPE_MAPPING)
TYPES = web.app.config.get('TYPES', _TYPES)

DATASTORE_URLS = {
    'datastore_delete': '{ckan_url}/api/action/datastore_delete',
    'resource_update': '{ckan_url}/api/action/resource_update'
}


class HTTPError(util.JobError):
    """Exception that's raised if a job fails due to an HTTP problem."""

    def __init__(self, message, status_code, request_url, response):
        """Initialise a new HTTPError.

        :param message: A human-readable error message
        :type message: string

        :param status_code: The status code of the errored HTTP response,
            e.g. 500
        :type status_code: int

        :param request_url: The URL that was requested
        :type request_url: string

        :param response: The body of the errored HTTP response as unicode
            (if you have a requests.Response object then response.text will
            give you this)
        :type response: unicode

        """
        super(HTTPError, self).__init__(message)
        self.status_code = status_code
        self.request_url = request_url
        self.response = response

    def as_dict(self):
        """Return a JSON-serializable dictionary representation of this error.

        Suitable for ckanserviceprovider to return to the client site as the
        value for the "error" key in the job dict.

        """
        if self.response and len(self.response) > 200:
            response = self.response[:200] + '...'
        else:
            response = self.response
        return {
            "message": self.message,
            "HTTP status code": self.status_code,
            "Requested URL": self.request_url,
            "Response": response,
        }


def get_url(action, ckan_url):
    """
    Get url for ckan action
    """
    if not urlparse.urlsplit(ckan_url).scheme:
        ckan_url = 'http://' + ckan_url.lstrip('/')
    ckan_url = ckan_url.rstrip('/')
    return '{ckan_url}/api/3/action/{action}'.format(
        ckan_url=ckan_url, action=action)


def check_response(response, request_url, who, good_status=(201, 200), ignore_no_success=False):
    """
    Checks the response and raises exceptions if something went terribly wrong

    :param who: A short name that indicated where the error occurred
                (for example "CKAN")
    :param good_status: Status codes that should not raise an exception

    """
    if not response.status_code:
        raise HTTPError(
            'DataPusher received an HTTP response with no status code',
            status_code=None, request_url=request_url, response=response.text)

    message = '{who} bad response. Status code: {code} {reason}. At: {url}.'
    try:
        if not response.status_code in good_status:
            json_response = response.json()
            if not ignore_no_success or json_response.get('success'):
                try:
                    message = json_response["error"]["message"]
                except Exception:
                    message = message.format(
                        who=who, code=response.status_code,
                        reason=response.reason, url=request_url)
                raise HTTPError(
                    message, status_code=response.status_code,
                    request_url=request_url, response=response.text)
    except ValueError as err:
        message = message.format(
            who=who, code=response.status_code, reason=response.reason,
            url=request_url, resp=response.text[:200])
        raise HTTPError(
            message, status_code=response.status_code, request_url=request_url,
            response=response.text)


def chunky(iterable, n):
    """
    Generates chunks of data that can be loaded into ckan

    :param n: Size of each chunks
    :type n: int
    """
    it = iter(iterable)
    item = list(itertools.islice(it, n))
    while item:
        yield item
        item = list(itertools.islice(it, n))


class DatastoreEncoder(json.JSONEncoder):
    # Custon JSON encoder
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return str(obj)

        return json.JSONEncoder.default(self, obj)


def delete_datastore_resource(resource_id, api_key, ckan_url):
    try:
        delete_url = get_url('datastore_delete', ckan_url)
        if not SSL_VERIFY:
            response = requests.post(delete_url,
                                     data=json.dumps({'id': resource_id,
                                                      'force': True}),
                                     headers={'Content-Type': 'application/json',
                                              'Authorization': api_key},
                                     verify=False
                                     )
        else:
            response = requests.post(delete_url,
                                 data=json.dumps({'id': resource_id,
                                                  'force': True}),
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': api_key}
                                 )
        check_response(response, delete_url, 'CKAN',
                       good_status=(201, 200, 404), ignore_no_success=True)
    except requests.exceptions.RequestException:
        raise util.JobError('Deleting existing datastore failed.')


def send_resource_to_datastore(resource, headers, records, api_key, ckan_url):
    """
    Stores records in CKAN datastore
    """
    request = {'resource_id': resource['id'],
               'fields': headers,
               'force': True,
               'records': records}

    name = resource.get('name')
    url = get_url('datastore_create', ckan_url)
    if not SSL_VERIFY:
        r = requests.post(url,
                          data=json.dumps(request, cls=DatastoreEncoder),
                          headers={'Content-Type': 'application/json',
                                   'Authorization': api_key},
                          verify=False
                          )
    else:
        r = requests.post(url,
                          data=json.dumps(request, cls=DatastoreEncoder),
                          headers={'Content-Type': 'application/json',
                                   'Authorization': api_key}
                          )
    check_response(r, url, 'CKAN DataStore')


def update_resource(resource, api_key, ckan_url):
    """
    Update webstore_url and webstore_last_updated in CKAN
    """

    resource['url_type'] = 'datapusher'

    url = get_url('resource_update', ckan_url)
    if not SSL_VERIFY:
        r = requests.post(
            url,
            data=json.dumps(resource),
            headers={'Content-Type': 'application/json',
                     'Authorization': api_key},
            verify=False
            )
    else:
        r = requests.post(
        url,
        data=json.dumps(resource),
        headers={'Content-Type': 'application/json',
                 'Authorization': api_key}
        )

    check_response(r, url, 'CKAN')


def get_resource(resource_id, ckan_url, api_key):
    """
    Gets available information about the resource from CKAN
    """
    url = get_url('resource_show', ckan_url)
    if not SSL_VERIFY:
        r = requests.post(url,
                          data=json.dumps({'id': resource_id}),
                          headers={'Content-Type': 'application/json',
                                   'Authorization': api_key},
                          verify=False
                          )
    else:
        r = requests.post(url,
                      data=json.dumps({'id': resource_id}),
                      headers={'Content-Type': 'application/json',
                               'Authorization': api_key}
                      )
    check_response(r, url, 'CKAN')

    return r.json()['result']


def validate_input(input):
    # Especially validate metdata which is provided by the user
    if not 'metadata' in input:
        raise util.JobError('Metadata missing')

    data = input['metadata']

    if not 'resource_id' in data:
        raise util.JobError('No id provided.')
    if not 'ckan_url' in data:
        raise util.JobError('No ckan_url provided.')
    if not input.get('api_key'):
        raise util.JobError('No CKAN API key provided')


@job.async
def push_to_datastore(task_id, input, dry_run=False):
    '''Download and parse a resource push its data into CKAN's DataStore.

    An asynchronous job that gets a resource from CKAN, downloads the
    resource's data file and, if the data file has changed since last time,
    parses the data and posts it into CKAN's DataStore.

    :param dry_run: Fetch and parse the data file but don't actually post the
        data to the DataStore, instead return the data headers and rows that
        would have been posted.
    :type dry_run: boolean

    '''
    handler = util.StoringHandler(task_id, input)
    logger = logging.getLogger(task_id)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    validate_input(input)

    data = input['metadata']
    ckan_url = data['ckan_url']
    resource_id = data['resource_id']
    api_key = input.get('api_key')

    if not SSL_VERIFY:
        logger.info('SSL_VERIFY is set to False. Not recommended in production.')

    try:
        resource = get_resource(resource_id, ckan_url, api_key)
    except util.JobError, e:
        #try again in 5 seconds just incase CKAN is slow at adding resource
        time.sleep(5)
        resource = get_resource(resource_id, ckan_url, api_key)

    # fetch the resource data
    logger.info('Fetching from: {0}'.format(resource.get('url')))
    try:
        request = urllib2.Request(resource.get('url'))

        if resource.get('url_type') == 'upload':
            # If this is an uploaded file to CKAN, authenticate the request,
            # otherwise we won't get file from private resources
            request.add_header('Authorization', api_key)

        response = urllib2.urlopen(request, timeout=DOWNLOAD_TIMEOUT)
    except urllib2.HTTPError as e:
        raise HTTPError(
            "DataPusher received a bad HTTP response when trying to download "
            "the data file", status_code=e.code,
            request_url=resource.get('url'), response=e.read())
    except urllib2.URLError as e:
        if isinstance(e.reason, socket.timeout):
            raise util.JobError('Connection timed out after %ss' %
                                DOWNLOAD_TIMEOUT)
        else:
            raise HTTPError(
                message=str(e.reason), status_code=None,
                request_url=resource.get('url'), response=None)

    cl = response.info().getheader('content-length')
    if cl and int(cl) > MAX_CONTENT_LENGTH:
        raise util.JobError(
            'Resource too large to download: {cl} > max ({max_cl}).'.format(
            cl=cl, max_cl=MAX_CONTENT_LENGTH))

    ct = response.info().getheader('content-type').split(';', 1)[0]

    f = cStringIO.StringIO(response.read())
    file_hash = hashlib.md5(f.read()).hexdigest()
    f.seek(0)

    if (resource.get('hash') == file_hash
            and not data.get('ignore_hash')):
        logger.info("The file hash hasn't changed: {hash}.".format(
            hash=file_hash))
        return

    resource['hash'] = file_hash

    try:
        table_set = messytables.any_tableset(f, mimetype=ct, extension=ct)
    except messytables.ReadError as e:
        ## try again with format
        f.seek(0)
        try:
            format = resource.get('format')
            table_set = messytables.any_tableset(f, mimetype=format, extension=format)
        except:
            raise util.JobError(e)

    row_set = table_set.tables.pop()
    offset, headers = messytables.headers_guess(row_set.sample)
    row_set.register_processor(messytables.headers_processor(headers))
    row_set.register_processor(messytables.offset_processor(offset + 1))
    types = messytables.type_guess(row_set.sample, types=TYPES, strict=True)
    row_set.register_processor(messytables.types_processor(types))

    headers = [header.strip() for header in headers if header.strip()]
    headers_set = set(headers)

    def row_iterator():
        for row in row_set:
            data_row = {}
            for index, cell in enumerate(row):
                column_name = cell.column.strip()
                if column_name not in headers_set:
                    continue
                data_row[column_name] = cell.value
            yield data_row
    result = row_iterator()

    '''
    Delete existing datstore resource before proceeding. Otherwise
    'datastore_create' will append to the existing datastore. And if
    the fields have significantly changed, it may also fail.
    '''
    logger.info('Deleting "{res_id}" from datastore.'.format(
        res_id=resource_id))
    delete_datastore_resource(resource_id, api_key, ckan_url)

    headers_dicts = [dict(id=field[0], type=TYPE_MAPPING[str(field[1])])
                     for field in zip(headers, types)]

    logger.info('Determined headers and types: {headers}'.format(
        headers=headers_dicts))

    if dry_run:
        return headers_dicts, result

    count = 0
    for i, records in enumerate(chunky(result, 250)):
        count += len(records)
        logger.info('Saving chunk {number}'.format(number=i))
        send_resource_to_datastore(resource, headers_dicts,
                                   records, api_key, ckan_url)

    logger.info('Successfully pushed {n} entries to "{res_id}".'.format(
        n=count, res_id=resource_id))

    if data.get('set_url_type', False):
        update_resource(resource, api_key, ckan_url)
