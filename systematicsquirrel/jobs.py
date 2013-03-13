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
    'Integer': 'numeric',  # 'int' may not be big enough,
            # and type detection may not realize it needs to be big
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
    if not 'url' in input['metadata']:
        raise util.JobError("Did not provide URL to resource.")


@job.async
def import_into_datastore(task_id, input):
    print "Input", input

    data = input['metadata']
    validate_input(input)

    ckan_url = data['ckan_url'].rstrip('/')
    datastore_create_request_url = '%s/api/action/datastore_create' % (ckan_url)

    excel_types = ['xls', 'application/ms-excel', 'application/xls',
                   'application/vnd.ms-excel']
    excel_xml_types = ['xlsx']
    tsv_types = ['tsv', 'text/tsv', 'text/tab-separated-values']
    csv_types = ['csv', 'text/csv', 'text/comma-separated-values']

    response = urllib2.urlopen(data['url'])

    content_type = response.info().getheader('content-type').split(';', 1)[0]  # remove parameters

    def is_of_type(types):
        return content_type in types or data['format'] in types

    parser = None
    if is_of_type(excel_types):
        parser = dataconverters.xls
    elif is_of_type(excel_xml_types):
        pass
    elif is_of_type(csv_types):
        parser = dataconverters.commas
    elif is_of_type(tsv_types):
        parser = dataconverters.commas

    if parser:
        result, metadata = parser.parse(response)
    else:
        raise util.JobError('No parser for {} found.'.format(content_type))

    headers = [dict(id=field['id'], type=TYPE_MAPPING.get(field['type'])) for field in metadata['fields']]
    print 'headers', headers
    print 'result', result

    def send_request(records):
        print 'send request to', datastore_create_request_url
        request = {'resource_id': data['resource_id'],
                   'fields': headers,
                   'records': records}
        r = requests.post(datastore_create_request_url,
                          data=json.dumps(request, cls=DatastoreEncoder),
                          headers={'Content-Type': 'application/json',
                                   'Authorization': input['apikey']},
                          )
        check_response(r, datastore_create_request_url)

    #logger.info('Creating: {0}.'.format(resource['id']))

    count = 0
    for records in chunky(result, 100):
        count += len(records)
        send_request(records)

    #from nose.tools import set_trace; set_trace()

    #logger.info("There should be {n} entries in {res_id}.".format(n=count, res_id=resource['id']))
