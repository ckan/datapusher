# -*- coding: utf-8 -*-


import json
import requests
try:
    from urllib.parse import urlsplit
except ImportError:
    from urlparse import urlsplit

import itertools
import datetime
import locale
import logging
import decimal
import hashlib
import time
import tempfile

import messytables

import ckanserviceprovider.job as job
import ckanserviceprovider.util as util
from ckanserviceprovider import web

if locale.getdefaultlocale()[0]:
    lang, encoding = locale.getdefaultlocale()
    locale.setlocale(locale.LC_ALL, locale=(lang, encoding))
else:
    locale.setlocale(locale.LC_ALL, '')

MAX_CONTENT_LENGTH = web.app.config.get('MAX_CONTENT_LENGTH') or 10485760
CHUNK_SIZE = 16 * 1024  # 16kb
DOWNLOAD_TIMEOUT = 30

if web.app.config.get('SSL_VERIFY') in ['False', 'FALSE', '0', False, 0]:
    SSL_VERIFY = False
else:
    SSL_VERIFY = True

if not SSL_VERIFY:
    requests.packages.urllib3.disable_warnings()

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

    def __str__(self):
        return '{} status={} url={} response={}'.format(
            self.message, self.status_code, self.request_url, self.response) \
            .encode('ascii', 'replace')


def get_url(action, ckan_url):
    """
    Get url for ckan action
    """
    if not urlsplit(ckan_url).scheme:
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
        if response.status_code not in good_status:
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
    except ValueError:
        message = message.format(
            who=who, code=response.status_code, reason=response.reason,
            url=request_url, resp=response.text[:200])
        raise HTTPError(
            message, status_code=response.status_code, request_url=request_url,
            response=response.text)


def chunky(items, num_items_per_chunk):
    """
    Breaks up a list of items into chunks - multiple smaller lists of items.
    The last chunk is flagged up.

    :param items: Size of each chunks
    :type items: iterable
    :param num_items_per_chunk: Size of each chunks
    :type num_items_per_chunk: int

    :returns: multiple tuples: (chunk, is_it_the_last_chunk)
    :rtype: generator of (list, bool)
    """
    items_ = iter(items)
    chunk = list(itertools.islice(items_, num_items_per_chunk))
    while chunk:
        next_chunk = list(itertools.islice(items_, num_items_per_chunk))
        chunk_is_the_last_one = not next_chunk
        yield chunk, chunk_is_the_last_one
        chunk = next_chunk


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
        response = requests.post(delete_url,
                                 verify=SSL_VERIFY,
                                 data=json.dumps({'id': resource_id,
                                                  'force': True}),
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': api_key}
                                 )
        check_response(response, delete_url, 'CKAN',
                       good_status=(201, 200, 404), ignore_no_success=True)
    except requests.exceptions.RequestException:
        raise util.JobError('Deleting existing datastore failed.')


def datastore_resource_exists(resource_id, api_key, ckan_url):
    try:
        search_url = get_url('datastore_search', ckan_url)
        response = requests.post(search_url,
                                 verify=SSL_VERIFY,
                                 data=json.dumps({'id': resource_id,
                                         'limit': 0}),
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': api_key}
                                 )
        if response.status_code == 404:
            return False
        elif response.status_code == 200:
            return response.json().get('result', {'fields': []})
        else:
            raise HTTPError(
                'Error getting datastore resource.',
                response.status_code, search_url, response,
            )
    except requests.exceptions.RequestException as e:
        raise util.JobError(
            'Error getting datastore resource ({!s}).'.format(e))


def send_resource_to_datastore(resource, headers, records,
                               is_it_the_last_chunk, api_key, ckan_url):
    """
    Stores records in CKAN datastore
    """
    request = {'resource_id': resource['id'],
               'fields': headers,
               'force': True,
               'records': records,
               'calculate_record_count': is_it_the_last_chunk}

    url = get_url('datastore_create', ckan_url)
    r = requests.post(url,
                      verify=SSL_VERIFY,
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
    r = requests.post(
        url,
        verify=SSL_VERIFY,
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
    r = requests.post(url,
                      verify=SSL_VERIFY,
                      data=json.dumps({'id': resource_id}),
                      headers={'Content-Type': 'application/json',
                               'Authorization': api_key}
                      )
    check_response(r, url, 'CKAN')

    return r.json()['result']


def validate_input(input):
    # Especially validate metdata which is provided by the user
    if 'metadata' not in input:
        raise util.JobError('Metadata missing')

    data = input['metadata']

    if 'resource_id' not in data:
        raise util.JobError('No id provided.')
    if 'ckan_url' not in data:
        raise util.JobError('No ckan_url provided.')
    if not input.get('api_key'):
        raise util.JobError('No CKAN API key provided')


@job.asynchronous
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

    try:
        resource = get_resource(resource_id, ckan_url, api_key)
    except util.JobError as e:
        # try again in 5 seconds just incase CKAN is slow at adding resource
        time.sleep(5)
        resource = get_resource(resource_id, ckan_url, api_key)

    # check if the resource url_type is a datastore
    if resource.get('url_type') == 'datastore':
        logger.info('Dump files are managed with the Datastore API')
        return

    # check scheme
    url = resource.get('url')
    scheme = urlsplit(url).scheme
    if scheme not in ('http', 'https', 'ftp'):
        raise util.JobError(
            'Only http, https, and ftp resources may be fetched.'
        )

    # fetch the resource data
    logger.info('Fetching from: {0}'.format(url))
    headers = {}
    if resource.get('url_type') == 'upload':
        # If this is an uploaded file to CKAN, authenticate the request,
        # otherwise we won't get file from private resources
        headers['Authorization'] = api_key
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=DOWNLOAD_TIMEOUT,
            verify=SSL_VERIFY,
            stream=True,  # just gets the headers for now
        )
        response.raise_for_status()

        cl = response.headers.get('content-length')
        try:
            if cl and int(cl) > MAX_CONTENT_LENGTH:
                raise util.JobError(
                    'Resource too large to download: {cl} > max ({max_cl}).'
                    .format(cl=cl, max_cl=MAX_CONTENT_LENGTH))
        except ValueError:
            pass

        tmp = tempfile.TemporaryFile()
        length = 0
        m = hashlib.md5()
        for chunk in response.iter_content(CHUNK_SIZE):
            length += len(chunk)
            if length > MAX_CONTENT_LENGTH:
                raise util.JobError(
                    'Resource too large to process: {cl} > max ({max_cl}).'
                    .format(cl=length, max_cl=MAX_CONTENT_LENGTH))
            tmp.write(chunk)
            m.update(chunk)

        ct = response.headers.get('content-type', '').split(';', 1)[0]

    except requests.HTTPError as e:
        raise HTTPError(
            "DataPusher received a bad HTTP response when trying to download "
            "the data file", status_code=e.response.status_code,
            request_url=url, response=e.response.content)
    except requests.RequestException as e:
        raise HTTPError(
            message=str(e), status_code=None,
            request_url=url, response=None)

    file_hash = m.hexdigest()
    tmp.seek(0)

    if (resource.get('hash') == file_hash
            and not data.get('ignore_hash')):
        logger.info("The file hash hasn't changed: {hash}.".format(
            hash=file_hash))
        return

    resource['hash'] = file_hash

    try:
        table_set = messytables.any_tableset(tmp, mimetype=ct, extension=ct)
    except messytables.ReadError as e:
        # try again with format
        tmp.seek(0)
        try:
            format = resource.get('format')
            table_set = messytables.any_tableset(tmp, mimetype=format, extension=format)
        except:
            raise util.JobError(e)

    get_row_set = web.app.config.get('GET_ROW_SET',
                                     lambda table_set: table_set.tables.pop())
    row_set = get_row_set(table_set)
    offset, headers = messytables.headers_guess(row_set.sample)

    existing = datastore_resource_exists(resource_id, api_key, ckan_url)
    existing_info = None
    if existing:
        existing_info = dict((f['id'], f['info'])
            for f in existing.get('fields', []) if 'info' in f)

    # Some headers might have been converted from strings to floats and such.
    headers = [str(header) for header in headers]

    row_set.register_processor(messytables.headers_processor(headers))
    row_set.register_processor(messytables.offset_processor(offset + 1))
    types = messytables.type_guess(row_set.sample, types=TYPES, strict=True)

    # override with types user requested
    if existing_info:
        types = [{
            'text': messytables.StringType(),
            'numeric': messytables.DecimalType(),
            'timestamp': messytables.DateUtilType(),
            }.get(existing_info.get(h, {}).get('type_override'), t)
            for t, h in zip(types, headers)]

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
                if isinstance(cell.value, str):
                    try:
                        data_row[column_name] = cell.value.encode('latin-1').decode('utf-8')
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        data_row[column_name] = cell.value
                else:
                    data_row[column_name] = cell.value
            yield data_row
    result = row_iterator()

    '''
    Delete existing datstore resource before proceeding. Otherwise
    'datastore_create' will append to the existing datastore. And if
    the fields have significantly changed, it may also fail.
    '''
    if existing:
        logger.info('Deleting "{res_id}" from datastore.'.format(
            res_id=resource_id))
        delete_datastore_resource(resource_id, api_key, ckan_url)

    headers_dicts = [dict(id=field[0], type=TYPE_MAPPING[str(field[1])])
                     for field in zip(headers, types)]

    # Maintain data dictionaries from matching column names
    if existing_info:
        for h in headers_dicts:
            if h['id'] in existing_info:
                h['info'] = existing_info[h['id']]
                # create columns with types user requested
                type_override = existing_info[h['id']].get('type_override')
                if type_override in list(_TYPE_MAPPING.values()):
                    h['type'] = type_override

    logger.info('Determined headers and types: {headers}'.format(
        headers=headers_dicts))

    if dry_run:
        return headers_dicts, result

    count = 0
    for i, chunk in enumerate(chunky(result, 250)):
        records, is_it_the_last_chunk = chunk
        count += len(records)
        logger.info('Saving chunk {number} {is_last}'.format(
            number=i, is_last='(last)' if is_it_the_last_chunk else ''))
        send_resource_to_datastore(resource, headers_dicts, records,
                                   is_it_the_last_chunk, api_key, ckan_url)

    logger.info('Successfully pushed {n} entries to "{res_id}".'.format(
        n=count, res_id=resource_id))

    if data.get('set_url_type', False):
        update_resource(resource, api_key, ckan_url)
