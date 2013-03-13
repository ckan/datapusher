import json
import urllib2
import requests
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


TYPE_MAPPING = {
    'String': 'text',
    # 'int' may not be big enough,
    # and type detection may not realize it needs to be big
    'Integer': 'numeric',
    'Float': 'float',
    'Decimal': 'numeric',
    'DateTime': 'timestamp'
}


def extract_content(response):
    # get the error messaage or error json out of response
    try:
        content = response.json()
    except:
        content = response.content[:200]
    return content


def check_response(response, request_url, who):
    if not response.status_code:
        raise util.JobError('%s is not reponding, At %s  '
                'Response %s' % (who, request_url, response))

    if response.status_code not in (201, 200) or not response.json().get('success'):
        raise util.JobError('%s bad response. Status code: %s, At: %s, Response: %s' %
                (who, response.status_code, request_url, extract_content(response)))


def delete_datastore_resource(input, resource):
    '''Delete existing datstore resource before proceeding. Otherwise 'datastore_create' will
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


def update_resource(input, resource):
    # Update webstore_url and webstore_last_updated
    ckan_url = input['metadata']['ckan_url'].rstrip('/')
    ckan_request_url = '%s/api/action/resource_update' % (ckan_url)

    resource.update({
        'webstore_url': 'active',
        'webstore_last_updated': datetime.datetime.now().isoformat()
    })

    print ckan_request_url

    r = requests.post(
        ckan_request_url,
        data=json.dumps(resource),
        headers={'Content-Type': 'application/json',
                 'Authorization': input['apikey']})

    check_response(r, ckan_request_url, 'CKAN')


def get_parser(resource, content_type):
    excel_types = ['xls', 'application/ms-excel', 'application/xls',
                   'application/vnd.ms-excel']
    excel_xml_types = ['xlsx']
    tsv_types = ['tsv', 'text/tsv', 'text/tab-separated-values']
    csv_types = ['csv', 'text/csv', 'text/comma-separated-values']
    #zipped_types = ['application/zip']

    def is_of_type(types):
        return content_type in types or resource['format'].lower() in types

    parser = None
    if is_of_type(excel_types):
        parser = dataconverters.xls
    elif is_of_type(excel_xml_types):
        pass
    elif is_of_type(csv_types):
        parser = dataconverters.commas
    elif is_of_type(tsv_types):
        parser = dataconverters.commas
    else:
        raise util.JobError('No parser for {} or {} found.'.format(
            content_type, resource['format']))
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
    # Custon JSON encoder
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)


def validate_input(input):
    # Especially validate metdata which is provided by the user
    data = input['metadata']

    if not 'resource_id' in data:
        raise util.JobError("No id provided.")
    if not 'ckan_url' in data:
        raise util.JobError("No ckan_url provided.")
    if not data['ckan_url'].startswith('http'):
        raise util.JobError('Schema in ckan_url missing (add http(s)://')


@job.async
def push_to_datastore(task_id, input):
    print "Input:", input

    data = input['metadata']
    validate_input(input)

    ckan_url = data['ckan_url'].rstrip('/')
    datastore_create_request_url = '%s/api/action/datastore_create' % (ckan_url)
    resource_show_url = '%s/api/action/resource_show' % (ckan_url)

    # get the metdata of the ckan resource
    r = requests.post(
        resource_show_url,
        data=json.dumps({'id': data['resource_id']}),
        headers={'Content-type': 'application/json'})
    check_response(r, resource_show_url, 'CKAN')
    resource = r.json()['result']

    # make a request to get actual data
    print "Fetching from:", resource.get('url')
    response = urllib2.urlopen(resource.get('url'))
    content_type = response.info().getheader('content-type').split(';', 1)[0]  # remove parameters

    parser = get_parser(resource, content_type)
    result, metadata = parser.parse(response)

    delete_datastore_resource(input, resource)

    headers = [dict(id=field['id'], type=TYPE_MAPPING.get(field['type'])) for field in metadata['fields']]
    print 'Headers:', headers

    def send_request(records):
        request = {'resource_id': data['resource_id'],
                   'fields': headers,
                   'records': records}
        r = requests.post(datastore_create_request_url,
                          data=json.dumps(request, cls=DatastoreEncoder),
                          headers={'Content-Type': 'application/json',
                                   'Authorization': input['apikey']},
                          )
        check_response(r, datastore_create_request_url, 'CKAN DataStore')

    count = 0
    for records in chunky(result, 100):
        count += len(records)
        send_request(records)

    #logger.info("There should be {n} entries in {res_id}.".format(n=count, res_id=resource['id']))

    print 'Update:', data['resource_id']
    update_resource(input, resource)
