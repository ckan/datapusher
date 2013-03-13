import json
import urllib2
import requests
import itertools
import datetime
import logging

import ckanserviceprovider.job as job
import ckanserviceprovider.util as util
import dataconverters.commas
import dataconverters.xls

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


TYPE_MAPPING = {
    'String': 'text',
    # 'int' may not be big enough,
    # and type detection may not realize it needs to be big
    'Integer': 'numeric',
    'Float': 'float',
    'Decimal': 'numeric',
    'DateTime': 'timestamp'
}


def check_response(response, datastore_create_request_url):
    if not response.status_code:
        raise util.JobError('Datastore is not reponding at %s with '
                'response %s' % (datastore_create_request_url, response))

    if response.status_code not in (201, 200):
        try:
            content = response.json()
            raise util.JobError('Datastorer bad response. Status code: %s, At: %s, Response: %s' %
                (response.status_code, datastore_create_request_url, content))
        except:
            raise util.JobError('Datastorer bad response. Status code: %s, At: %s.' %
                (response.status_code, datastore_create_request_url))

    if not response.json()['success']:
        raise util.JobError('Datastorer bad response. Status code: %s, At: %s, Response: %s' %
                (response.status_code, datastore_create_request_url, response.json()))


def delete_resource(input, resource):
    '''Delete any existing data before proceeding. Otherwise 'datastore_create' will
    append to the existing datastore. And if the fields have significantly changed,
    it may also fail. '''
    ckan_url = input['metadata']['ckan_url'].rstrip('/')
    res_id = input['metadata']['resource_id']
    try:
        response = requests.post('%s/api/action/datastore_delete' % (ckan_url),
                                 data=json.dumps({'resource_id': res_id}),
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': input['apikey']}
                                 )
        if not response.status_code or response.status_code not in (200, 404):
            # skips 200 (OK)
            # or 404 (datastore does not exist, no need to delete it)
            raise util.JobError("Deleting existing datastore failed.")
    except requests.exceptions.RequestException:
        raise util.JobError("Deleting existing datastore failed.")


def get_parser(resource, content_type):
    excel_types = ['xls', 'application/ms-excel', 'application/xls',
                   'application/vnd.ms-excel']
    excel_xml_types = ['xlsx']
    tsv_types = ['tsv', 'text/tsv', 'text/tab-separated-values']
    csv_types = ['csv', 'text/csv', 'text/comma-separated-values']

    def is_of_type(types):
        return content_type in types or resource['format'] in types

    parser = None
    if is_of_type(excel_types):
        parser = dataconverters.xls
    elif is_of_type(excel_xml_types):
        pass
    elif is_of_type(csv_types):
        parser = dataconverters.commas
    elif is_of_type(tsv_types):
        parser = dataconverters.commas

    return parser


# generates chunks of data that can be loaded into ckan
# n is the maximum size of a chunk
def chunky(iterable, n):
    it = iter(iterable)
    while True:
        chunk = list(
            itertools.imap(
                dict, itertools.islice(it, n)))
        if not chunk:
            return
        yield chunk


class DatastoreEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)


def validate_input(input):
    data = input['metadata']

    if not 'resource_id' in data:
        raise util.JobError("No id provided.")
    if not 'ckan_url' in data:
        raise util.JobError("No ckan_url provided.")


@job.async
def push_to_datastore(task_id, input):
    print "Input:", input

    data = input['metadata']
    validate_input(input)

    ckan_url = data['ckan_url'].rstrip('/')
    datastore_create_request_url = '%s/api/action/datastore_create' % (ckan_url)
    resource_show_url = '%s/api/action/resource_show' % (ckan_url)

    r = requests.post(resource_show_url, data={'id': data['resource_id']})
    resource = r.json()

    response = urllib2.urlopen(resource['url'])
    content_type = response.info().getheader('content-type').split(';', 1)[0]  # remove parameters

    parser = get_parser(resource, content_type)

    if parser:
        result, metadata = parser.parse(response)
    else:
        raise util.JobError('No parser for {} found.'.format(content_type))

    delete_resource(input, resource)

    headers = [dict(id=field['id'], type=TYPE_MAPPING.get(field['type'])) for field in metadata['fields']]
    print 'Headers:', headers
    print 'Result:', result

    def send_request(records):
        request = {'resource_id': data['resource_id'],
                   'fields': headers,
                   'records': records}
        r = requests.post(datastore_create_request_url,
                          data=json.dumps(request, cls=DatastoreEncoder),
                          headers={'Content-Type': 'application/json',
                                   'Authorization': input['apikey']},
                          )
        check_response(r, datastore_create_request_url)

    count = 0
    for records in chunky(result, 100):
        count += len(records)
        send_request(records)

    #logger.info("There should be {n} entries in {res_id}.".format(n=count, res_id=resource['id']))
