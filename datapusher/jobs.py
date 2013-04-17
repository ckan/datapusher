# -*- coding: utf-8 -*-
import json
import urllib2
import socket
import requests
import urlparse
import itertools
import datetime
import logging
import locale

import ckanserviceprovider.job as job
import ckanserviceprovider.util as util
import dataconverters.commas
import dataconverters.xls

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

if not locale.getlocale()[0]:
    locale.setlocale(locale.LC_ALL, '')

MAX_CONTENT_LENGTH = 10485760  # 10MB
DOWNLOAD_TIMEOUT = 30

TYPE_MAPPING = {
    'String': 'text',
    # 'int' may not be big enough,
    # and type detection may not realize it needs to be big
    'Integer': 'numeric',
    'Float': 'float',
    'Decimal': 'numeric',
    'DateTime': 'timestamp'
}

DATASTORE_URLS = {
    'datastore_delete': '{ckan_url}/api/action/datastore_delete',
    'resource_update': '{ckan_url}/api/action/resource_update'
}


def get_url(action, ckan_url):
    """
    Get url for ckan action
    """
    if not urlparse.urlsplit(ckan_url).scheme:
        ckan_url = u'http://' + ckan_url.lstrip('/')
    ckan_url = ckan_url.rstrip('/')
    return '{ckan_url}/api/3/action/{action}'.format(
        ckan_url=ckan_url, action=action)


def check_response(response, request_url, who):
    """
    Checks the response and raises exceptions if something went terribly wrong
    """
    if not response.status_code:
        raise util.JobError('%s is not reponding, At: %s '
                            'Response: %s' % (who, request_url, response))

    try:
        json_response = response.json()
        if not (response.status_code in (201, 200) and json_response.get('success')):
            raise util.JobError('%s bad response. Status code: %s, At: %s, Response: %s' % (
                                who,
                                response.status_code,
                                request_url,
                                json_response))
    except ValueError:
        raise util.JobError('%s bad response. Could not decode JSON. Status code: %s, At: %s, Response: %s' % (
                            who,
                            response.status_code,
                            request_url,
                            response.content[:200]))


def get_parser(resource, content_type):
    """
    Get tuple of parser and additional arguments that should be passed
    to the parse call.
    """
    excel_types = ['xls', 'application/ms-excel', 'application/xls',
                   'application/vnd.ms-excel']
    excel_xml_types = ['xlsx',
                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
    tsv_types = ['tsv', 'text/tsv', 'text/tab-separated-values']
    csv_types = ['csv', 'text/csv', 'text/comma-separated-values']
    #zipped_types = ['application/zip']

    def is_of_type(types):
        return content_type in types or resource['format'].lower() in types

    parser = None
    kwargs = {}
    if is_of_type(excel_types):
        parser = dataconverters.xls
    elif is_of_type(excel_xml_types):
        parser = dataconverters.xls
        kwargs = {'excel_type': 'xlsx'}
    elif is_of_type(csv_types):
        parser = dataconverters.commas
    elif is_of_type(tsv_types):
        parser = dataconverters.commas
    else:
        raise util.JobError('No parser for {} or {} found.'.format(
            content_type, resource['format']))
    return parser, kwargs


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

        return json.JSONEncoder.default(self, obj)


def delete_datastore_resource(resource_id, api_key, ckan_url):
    try:
        response = requests.post(get_url('datastore_delete', ckan_url),
                                 data=json.dumps({'resource_id': resource_id}),
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': api_key}
                                 )
        if not response.status_code or response.status_code not in (200, 404):
            # skips 200 (OK)
            # or 404 (datastore does not exist, no need to delete it)
            raise util.JobError("Deleting existing datastore failed.")
    except requests.exceptions.RequestException:
        raise util.JobError("Deleting existing datastore failed.")


def send_resource_to_datastore(resource_id, headers, records, api_key, ckan_url):
    """
    Stores records in CKAN datastore
    """
    request = {'resource_id': resource_id,
               'fields': headers,
               'records': records}
    url = get_url('datastore_create', ckan_url)
    r = requests.post(url,
                      data=json.dumps(request, cls=DatastoreEncoder),
                      headers={'Content-Type': 'application/json',
                               'Authorization': api_key},
                      )
    check_response(r, url, 'CKAN DataStore')


def update_resource(resource, api_key, ckan_url):
    """
    Update webstore_url and webstore_last_updated in CKAN
    """

    resource.update({
        'webstore_url': 'active',
        'webstore_last_updated': datetime.datetime.now().isoformat()
    })

    url = get_url('resource_update', ckan_url)
    r = requests.post(
        url,
        data=json.dumps(resource),
        headers={'Content-Type': 'application/json',
                 'Authorization': api_key})

    check_response(r, url, 'CKAN')


def get_resource(resource_id, ckan_url):
    """
    Gets available information about the resource from CKAN
    """
    url = get_url('resource_show', ckan_url)
    r = requests.post(url,
                      data=json.dumps({'id': resource_id}),
                      headers={'Content-type': 'application/json'})
    check_response(r, url, 'CKAN')

    return r.json()['result']


def validate_input(input):
    # Especially validate metdata which is provided by the user
    if not 'metadata' in input:
        raise util.JobError('Metadata missing')

    data = input['metadata']

    if not 'resource_id' in data:
        raise util.JobError("No id provided.")
    if not 'ckan_url' in data:
        raise util.JobError("No ckan_url provided.")


@job.async
def push_to_datastore(task_id, input, dry_run=False):
    '''Show link to documentation.

    :param dry_run: Only fetch and parse the resource and return the results
                    instead of storing it in the datastore (for testing)
    :type dry_run: boolean
    '''
    print "Input:", input
    validate_input(input)

    data = input['metadata']

    ckan_url = data['ckan_url']
    resource_id = data['resource_id']
    api_key = data.get('api_key')

    resource = get_resource(resource_id, ckan_url)

    # fetch the resource data
    print "Fetching from:", resource.get('url')
    try:
        response = urllib2.urlopen(resource.get('url'), timeout=DOWNLOAD_TIMEOUT)
    except urllib2.HTTPError, e:
        raise util.JobError('Invalid HTTP response: %s' % e)
    except urllib2.URLError, e:
        if isinstance(e.reason, socket.timeout):
            raise util.JobError('Connection timed out after %ss' % DOWNLOAD_TIMEOUT)

    cl = response.info().getheader('content-length')
    if cl and int(cl) > MAX_CONTENT_LENGTH:
        raise util.JobError(
            'Resource too large to download: {cl} > max ({max_cl}).'.format(
            cl=cl, max_cl=MAX_CONTENT_LENGTH))

    ct = response.info().getheader('content-type').split(';', 1)[0]

    parser, kwargs = get_parser(resource, ct)
    result, metadata = parser.parse(response, strict_type_guess=True, **kwargs)

    '''
    Delete existing datstore resource before proceeding. Otherwise
    'datastore_create' will append to the existing datastore. And if
    the fields have significantly changed, it may also fail.
    '''
    delete_datastore_resource(resource_id, api_key, ckan_url)

    fields = metadata['fields']
    headers = [dict(id=field['id'], type=TYPE_MAPPING.get(field['type'])) for field in fields]

    print 'Headers:', headers

    if dry_run:
        return headers, result

    count = 0
    for records in chunky(result, 100):
        count += len(records)
        send_resource_to_datastore(resource_id, headers, records, api_key, ckan_url)

    #logger.info("There should be {n} entries in {res_id}.".format(n=count, res_id=resource['id']))

    update_resource(resource, api_key, ckan_url)
