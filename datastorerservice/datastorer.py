import os
import json
import requests
import datetime
import itertools
import tempfile

import messytables
from messytables import (CSVTableSet, XLSTableSet, types_processor,
                         headers_guess, headers_processor, type_guess,
                         offset_processor)

import ckanserviceprototype.web as web
import ckanserviceprototype.job as job
import ckanserviceprototype.util as util


TYPE_MAPPING = {
    messytables.types.StringType: 'text',
    messytables.types.IntegerType: 'numeric',  # 'int' may not be big enough,
                    # and type detection may not realize it needs to be big
    messytables.types.FloatType: 'float',
    messytables.types.DecimalType: 'numeric',
    messytables.types.DateType: 'timestamp',
    messytables.types.DateUtilType: 'timestamp'
}


def check_response(response, datastore_create_request_url):
    try:
        if not response.status_code:
            raise util.JobError('Datastore is not reponding at %s with '
                    'response %s' % (datastore_create_request_url, response))
    except Exception, e:
        pass
        #datastorer_upload.retry(exc=e)

    if response.status_code not in (201, 200):
        try:
            # try logging a json response but ignore it if the content is not json
            response.content = json.loads(response.content)
        except:
            pass
        raise util.JobError('Datastorer bad response code (%s) on %s. Response was %s' %
                (response.status_code, datastore_create_request_url, response.content))


def stringify_processor():
    def to_string(row_set, row):
        for cell in row:
            if not cell.value:
                cell.value = None
            else:
                cell.value = unicode(cell.value)
        return row
    return to_string


def datetime_procesor():
    ''' Stringifies dates so that they can be parsed by the db
    '''
    def datetime_convert(row_set, row):
        for cell in row:
            if isinstance(cell.value, datetime.datetime):
                cell.value = cell.value.isoformat()
                cell.type = messytables.StringType()
        return row
    return datetime_convert


def check_provided_data(data):
    if not 'url' in data:
        raise util.JobError("Did not provide URL to resource.")


@job.async
def upload(task_id, input):
    """
    Expected input dictionary with keys:
        'url'
    """

    data = input['data']
    check_provided_data(data)

    excel_types = ['xls', 'application/ms-excel', 'application/xls',
                   'application/vnd.ms-excel']
    tsv_types = ['tsv', 'text/tsv', 'text/tab-separated-values']

    result = requests.get(data['url'])

    content_type = result.headers['content-type']\
                                    .split(';', 1)[0]  # remove parameters

    with tempfile.NamedTemporaryFile() as f:
        f.write(result.text)
        f.flush()
        f.seek(0)

        if content_type in excel_types or data['format'] in excel_types:
            table_sets = XLSTableSet(f)
        else:
            is_tsv = (content_type in tsv_types or
                      data['format'] in tsv_types)
            delimiter = '\t' if is_tsv else ','
            table_sets = CSVTableSet(f, delimiter=delimiter, encoding='utf-8')

        ##only first sheet in xls for time being
        row_set = table_sets.tables[0]
        offset, headers = headers_guess(row_set.sample)
        row_set.register_processor(headers_processor(headers))
        row_set.register_processor(offset_processor(offset + 1))
        row_set.register_processor(datetime_procesor())

        #logger.info('Header offset: {0}.'.format(offset))

        guessed_types = type_guess(
            row_set.sample,
            [
                messytables.types.StringType,
                messytables.types.IntegerType,
                messytables.types.FloatType,
                messytables.types.DecimalType,
                messytables.types.DateUtilType
            ],
            strict=True
        )
        #logger.info('Guessed types: {0}'.format(guessed_types))
        row_set.register_processor(types_processor(guessed_types, strict=True))
        row_set.register_processor(stringify_processor())

        ckan_url = data['ckan_url'].rstrip('/')

        datastore_create_request_url = '%s/api/action/datastore_create' % (ckan_url)

        guessed_type_names = [TYPE_MAPPING[type(gt)] for gt in guessed_types]

        def send_request(records):
            request = {'resource_id': data['resource_id'],
                       'fields': [dict(id=name, type=typename) for name, typename in zip(headers, guessed_type_names)],
                       'records': records}
            response = requests.post(datastore_create_request_url,
                             data=json.dumps(request),
                             headers={'Content-Type': 'application/json',
                                      'Authorization': input['apikey']},
                             )
            check_response(response, datastore_create_request_url)

        #logger.info('Creating: {0}.'.format(resource['id']))

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

        count = 0
        for records in chunky(row_set.dicts(), 100):
            count += len(records)
            send_request(records)

        #logger.info("There should be {n} entries in {res_id}.".format(n=count, res_id=resource['id']))

        ckan_request_url = ckan_url + '/api/action/resource_update'

        ckan_resource_data = {
            'id': data["resource_id"],
            'webstore_url': 'active',
            'webstore_last_updated': datetime.datetime.now().isoformat(),
            'url': data['url']
        }

        response = requests.post(
            ckan_request_url,
            data=json.dumps(ckan_resource_data),
            headers={'Content-Type': 'application/json',
                     'Authorization': input['apikey']})

        if response.status_code not in (201, 200):
            raise util.JobError('Ckan bad response code (%s). Response was %s' %
                                 (response.status_code, response.content))


if __name__ == '__main__':
    import argparse

    argparser = argparse.ArgumentParser(
        description='Service that allows automatic migration of data to the CKAN DataStore',
        epilog='"He reached out and pressed an invitingly large red button on a nearby panel. The panel lit up with the words Please do not press this button again."')

    argparser.add_argument('config', metavar='CONFIG', type=file,
                       help='configuration file')
    args = argparser.parse_args()

    os.environ['JOB_CONFIG'] = args.config.name

    web.configure()
    web.app.run()
