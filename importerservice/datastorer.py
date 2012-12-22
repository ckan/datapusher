import json
import requests
import itertools
import tempfile

import ckanserviceprovider.job as job
import ckanserviceprovider.util as util
import dataconverters.csv as csv


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
            response.content = json.loads(response.content)
            raise util.JobError('Datastorer bad response code (%s) on %s. Response was %s' %
                (response.status_code, datastore_create_request_url, response.content))
        except:
            raise util.JobError('Datastorer bad response code (%s) on %s.' %
                (response.status_code, datastore_create_request_url))


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


def check_provided_data(data):
    if not 'url' in data:
        raise util.JobError("Did not provide URL to resource.")


@job.async
def import_into_datastore(task_id, input):
    """
    Expected input dictionary with keys:
        'url'
    """

    data = input['data']
    check_provided_data(data)

    ckan_url = data['ckan_url'].rstrip('/')
    datastore_create_request_url = '%s/api/action/datastore_create' % (ckan_url)

    excel_types = ['xls', 'application/ms-excel', 'application/xls',
                   'application/vnd.ms-excel']
    excel_xml_types = ['xlsx']
    tsv_types = ['tsv', 'text/tsv', 'text/tab-separated-values']
    csv_types = ['csv', 'text/csv', 'text/comma-separated-values']

    requested_resource = requests.get(data['url'])

    content_type = requested_resource.headers['content-type']\
                                    .split(';', 1)[0]  # remove parameters

    def is_of_type(types):
        return content_type in types or data['format'] in types

    with tempfile.NamedTemporaryFile() as f:
        f.write(requested_resource.text)
        f.flush()
        f.seek(0)

        # TODO: refactor
        if is_of_type(excel_types):
            pass
        elif is_of_type(excel_xml_types):
            pass
        elif is_of_type(csv_types):
            result, metadata = csv.csv_parse(f, header_type=1)
        elif is_of_type(tsv_types):
            pass

        headers = [dict(id=field['id'], type=TYPE_MAPPING.get(field['type'])) for field in metadata['fields']]
        print 'headers', headers
        print 'result', result

        def send_request(records):
            request = {'resource_id': data['resource_id'],
                       'fields': headers,
                       'records': records}
            response = requests.post(datastore_create_request_url,
                             data=json.dumps(request),
                             headers={'Content-Type': 'application/json',
                                      'Authorization': input['apikey']},
                             )
            check_response(response, datastore_create_request_url)

        #logger.info('Creating: {0}.'.format(resource['id']))

        count = 0
        for records in chunky(result, 100):
            count += len(records)
            send_request(records)

        #from nose.tools import set_trace; set_trace()

        #logger.info("There should be {n} entries in {res_id}.".format(n=count, res_id=resource['id']))
