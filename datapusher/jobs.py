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
import tempfile
import subprocess
from threading import Timer
import re
from random import randint
import glob
import os

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
DOWNLOAD_TIMEOUT = 30
DROP_INDEXES = web.app.config.get('DROP_INDEXES', True)

if web.app.config.get('SSL_VERIFY') in ['False', 'FALSE', '0']:
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
        return u'{} status={} url={} response={}'.format(
            self.message, self.status_code, self.request_url, self.response) \
            .encode('ascii', 'replace')


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
                                 params={'id': resource_id,
                                         'limit': 0},
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
                response.status_code, search_url, reponse,
            )
    except requests.exceptions.RequestException as e:
        raise util.JobError(
            'Error getting datastore resource ({!s}).'.format(e))


def send_resource_to_datastore(resource_id, headers, records, api_key, ckan_url):
    """
    Stores records in CKAN datastore
    """
    request = {'resource_id': resource_id,
               'fields': headers,
               'force': True,
               'records': records}

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
    Update the given CKAN resource to say that it has been stored in datastore
    ok.
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
    logger.addHandler(handler)  # saves logs to the db
    logger.addHandler(logging.StreamHandler())  # also show them on stderr
    logger.setLevel(logging.DEBUG)

    validate_input(input)

    data = input['metadata']

    ckan_url = data['ckan_url']
    resource_id = data['resource_id']
    api_key = input.get('api_key')

    try:
        resource = get_resource(resource_id, ckan_url, api_key)
    except util.JobError, e:
        # try again in 5 seconds just in case CKAN is slow at adding resource
        time.sleep(5)
        resource = get_resource(resource_id, ckan_url, api_key)

    # check if the resource url_type is a datastore
    if resource.get('url_type') == 'datastore':
        logger.info('Ignoring resource - url_type=datastore - dump files are '
                    'managed with the Datastore API')
        return

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
        logger.info('Ignoring resource - the file hash hasn\'t changed: '
                    '{hash}.'.format(hash=file_hash))
        return

    resource['hash'] = file_hash

    try:
        table_set = messytables.any_tableset(f, mimetype=ct, extension=ct)
    except messytables.ReadError as e:
        # try again with format
        f.seek(0)
        try:
            format = resource.get('format')
            table_set = messytables.any_tableset(f, mimetype=format,
                                                 extension=format)
        except Exception:
            raise util.JobError(e)

    row_set = table_set.tables.pop()
    header_offset, headers = messytables.headers_guess(row_set.sample)

    # Some headers might have been converted from strings to floats and such.
    headers = [unicode(header) for header in headers]

    # Setup the converters that run when you iterate over the row_set.
    # With pgloader only the headers will be iterated over.
    row_set.register_processor(messytables.headers_processor(headers))
    row_set.register_processor(
        messytables.offset_processor(header_offset + 1))
    types = messytables.type_guess(row_set.sample, types=TYPES, strict=True)

    headers = [header.strip() for header in headers if header.strip()]
    headers_dicts = [dict(id=field[0], type=TYPE_MAPPING[str(field[1])])
                     for field in zip(headers, types)]

    # pgloader only handles csv
    use_pgloader = web.app.config.get('USE_PGLOADER', True) and \
        isinstance(row_set, messytables.CSVRowSet)

    # Delete existing datastore resource before proceeding. Otherwise
    # 'datastore_create' will append to the existing datastore. And if
    # the fields have significantly changed, it may also fail.
    existing = datastore_resource_exists(resource_id, api_key, ckan_url)
    if existing:
        if not dry_run:
            logger.info('Deleting "{res_id}" from datastore.'.format(
                res_id=resource_id))
            delete_datastore_resource(resource_id, api_key, ckan_url)
    elif use_pgloader:
        # Create datastore table - pgloader needs this
        logger.info('Creating datastore table for resource: %s',
                    resource['id'])
        # create it by calling update with 0 records
        send_resource_to_datastore(resource['id'], headers_dicts,
                                   [], api_key, ckan_url)
        # it also sets "datastore_active=True" on the resource

    # Maintain data dictionaries from matching column names
    if existing:
        existing_info = dict(
            (f['id'], f['info'])
            for f in existing.get('fields', []) if 'info' in f)
        for h in headers_dicts:
            if h['id'] in existing_info:
                h['info'] = existing_info[h['id']]

    logger.info('Determined headers and types: {headers}'.format(
        headers=headers_dicts))

    if use_pgloader:
        csv_dialect = row_set._dialect()
        f.seek(0)
        # Save CSV to a file
        # TODO rather than save it, pipe in the data:
        # http://stackoverflow.com/questions/163542/python-how-do-i-pass-a-string-into-subprocess-popen-using-the-stdin-argument
        # then it won't be all in memory at once.
        with tempfile.NamedTemporaryFile() as saved_file:
            # csv_buffer = f.read()
            # pgloader doesn't detect encoding. Use chardet then. It is easier
            # to reencode it as UTF8 than convert the name of the encoding to
            # one that pgloader will understand.
            csv_decoder = messytables.commas.UTF8Recoder(f, encoding=None)
            csv_unicode = csv_decoder.reader.read()
            csv_buffer = csv_unicode.encode('utf8')
            # pgloader only allows a single character line terminator. See:
            # https://github.com/dimitri/pgloader/issues/508#issuecomment-275878600
            # However we can't use that solution because the last column may
            # not be of type text. Therefore change the line endings before
            # giving it to pgloader.
            if len(csv_dialect.lineterminator) > 1:
                csv_buffer = csv_buffer.replace(
                    csv_dialect.lineterminator, b'\n')
                csv_dialect.lineterminator = b'\n'
            saved_file.write(csv_buffer)
            saved_file.flush()
            csv_filepath = saved_file.name
            skip_header_rows = header_offset + 1
            load_data_with_pgloader(
                resource['id'], csv_filepath, headers, skip_header_rows,
                csv_dialect, ckan_url, api_key, dry_run, logger)
    else:
        row_set.register_processor(messytables.types_processor(types))

        ret = convert_and_load_data(
            resource['id'], row_set, headers, headers_dicts,
            ckan_url, api_key, dry_run, logger)
        if dry_run:
            return ret

    if data.get('set_url_type', False):
        update_resource(resource, api_key, ckan_url)


def load_data_with_pgloader(resource_id, csv_filepath, headers,
                            skip_header_rows, csv_dialect,
                            ckan_url, api_key, dry_run, logger):
    datastore_postgres_url = web.app.config.get('CKAN_DATASTORE_WRITE_URL')
    if not datastore_postgres_url:
        raise util.JobError(
            'You need to configure a value for: CKAN_DATASTORE_WRITE_URL')
    pgloader_command_file_buffer = get_csv_pgloader_command_file_buffer(
        datastore_postgres_url, resource_id,
        csv_filepath, headers, skip_header_rows, csv_dialect)

    pgloader_options_filepath = '/tmp/pgloader_options'
    with open(pgloader_options_filepath, 'w') as f:
        f.write(pgloader_command_file_buffer)
    logger.info('pgloader command file:\n%s', pgloader_command_file_buffer)
    cmd = ['pgloader']
    # specify a unique pgloader_log_dir so it isn't confused with other runs
    # of it, which may be concurrent
    pgloader_log_dir = '/tmp/pgloader/{}'.format(randint(1000, 100000))
    cmd.extend(['--root-dir', pgloader_log_dir])
    cmd.append(pgloader_options_filepath)
    logger.info('pgloader command-line: %s', ' '.join(cmd))

    # run pgloader itself
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            universal_newlines=True)

    # read stdout as it is produced, so we can keep track
    log_messages = PgLoaderLogMessages(logger)
    for stdout_line in iter(proc.stdout.readline, ''):
        log_messages.add_line(stdout_line)
        if 'ERROR' in stdout_line or 'FATAL' in stdout_line:
            # pgloader is liable to hang after errors. So get any remaining
            # lines and if it doesn't finish within a timeout, kill it.
            timer = Timer(1, lambda p: p.kill(), [proc])
            try:
                timer.start()
                for stdout_line in iter(proc.stdout.readline, ''):
                    log_messages.add_line(stdout_line)
            finally:
                timer.cancel()
            proc.stdout.close()
            proc.kill()
            logger.error('pgloader killed, following the error.')
            break
    else:
        # pgloader finished naturally
        proc.stdout.close()
        return_code = proc.wait()
        if return_code:
            log_messages.log_current_message()
            if not log_messages.errored:
                # pgloader didn't print an error, so we need to
                logger.error('pgloader exited with error code: %s',
                             return_code)
    log_messages.log_current_message()

    # look at the pgloader log files for a clear list of rejected rows
    log_files = []
    for folder, subs, files in os.walk(pgloader_log_dir):
        for file in files:
            if file.endswith('.log') and file != 'pgloader.log':
                log_files.append(os.path.join(folder, file))
    if len(log_files) != 1:
        logger.error('Expected 1 pgloader log file with rejected rows, '
                     'but instead found: %s', len(log_files))
    for log_file in log_files:
        with open(log_file) as f:
            rejected = parse_pgloader_rejected_rows_log(f, logger,
                                                        skip_header_rows)
        if rejected['num_rows']:
            logger.error('%s rows were rejected: %s '
                         'The errors related to these columns: %s',
                         rejected['num_rows'],
                         ', '.join(str(row) for row in rejected['rows'][:5]) +
                         ' etc.' if len(rejected['rows']) > 5 else '',
                         ', '.join(rejected['cols']))

    # look at the report summary
    for msg in log_messages.all_messages[::-1]:
        if msg.startswith('Total import time'):
            # Total import time   6    6    0   0.256s   0.003s  0.004s
            match = re.match(
                '^Total import time\s+'
                '(?P<read>\d+)\s+(?P<imported>\d+)\s+(?P<errors>\d+)\s+'
                '(?P<total_time>[0-9.]+)s\s+(?P<read_time>[0-9.]+)s\s+'
                '(?P<write_time>[0-9.]+)s$', msg)
            if not match:
                logger.error('Could not parse pgloader summary: %s', msg)
    else:
        logger.error('pgloader summary not found - this happens after errors '
                     'and it gets killed. Rather than '
                     'leave only a small fraction of the data in DataStore, '
                     'remove it all.')
        logger.info('Deleting "{res_id}" from datastore.'.format(
                    res_id=resource_id))
        delete_datastore_resource(resource_id, api_key, ckan_url)


def parse_pgloader_rejected_rows_log(f, logger, skip_header_rows):
    '''
    e.g.
    Database error 22P02: invalid input syntax for type numeric: "6,200.00"
    CONTEXT: COPY foo-bar-42, line 5, column Grand Total: "6,200.00"
    Database error 22P02: invalid input syntax for type numeric: "1,500.00"
    CONTEXT: COPY foo-bar-42, line 3, column Grand Total: "1,500.00"
    '''
    state = 'Database error'
    result = dict(row_details=[], rows=[], cols=set())
    line_num = 1  # start row numbering at 1, just like Excel
    line_num += skip_header_rows - 1
    for line in f.readlines():
        line = line.strip()
        if not line:
            continue
        if state == 'Database error':
            match = re.match('Database error [^:]+: (.+)', line)
            row_error = ''
            if not match:
                logger.error('Could not parse log of rejected rows line: %s',
                             line.strip())
            else:
                row_error = match.groups()[0]
            state = 'context'
        elif state == 'context':
            match = re.match('CONTEXT: .+, line (\d+), column (.+): .+', line)
            # NB the line number is relative to the previous error, because the
            # line number comes from the response to postgres COPY, and after
            # an error, pgloader resubmits the data after the error line.
            if not match:
                logger.error('Could not parse log of rejected rows context '
                             'line: %s', line.strip())
            else:
                rel_line_num, column = match.groups()
                line_num += int(rel_line_num)
                result['row_details'].append(
                    (int(line_num), column, row_error))
                result['rows'].append(line_num)
                result['cols'].add(column)
            state = 'Database error'
        else:
            logger.error('Parsing of rejected rows log invalid state: %s',
                         state)
            break
    result['num_rows'] = len(result['rows'])
    result['num_cols'] = len(result['cols'])
    result['rows'] = result['rows']
    result['row_details'] = result['row_details']
    return result

def get_csv_pgloader_command_file_buffer(
        postgres_url, table_name,
        csv_filepath, header_names, skip_header_rows, csv_dialect):
    postgres_table_param = '?tablename={}'.format(table_name)
    # We need to call identifier to double quote the field names, since
    # that makes them case sensitive, as was done when creating the columns
    fields = ','.join(identifier(field_name)
                      for field_name in header_names)
    # convert '\n' -> '0x0a'
    line_terminator = '0x' + csv_dialect.lineterminator.encode('hex')
    options = '''
    LOAD CSV
         FROM '{filepath}'
             HAVING FIELDS ({fields})
         INTO {postgres_url}
             TARGET COLUMNS ({target_fields})

    WITH skip header = {skip_header},
         batch rows = 10000,
         {drop_indexes}
         quote identifiers,
         fields terminated by '{delimiter}',
         fields optionally enclosed by '{quote_char}',
         lines terminated by '{line_terminator}'
    ;'''.format(
        filepath=csv_filepath,
        fields=fields,
        postgres_url=postgres_url + postgres_table_param,
        target_fields=fields,
        skip_header=skip_header_rows,
        drop_indexes='drop indexes,' if DROP_INDEXES else '',
        delimiter=csv_dialect.delimiter,
        quote_char=csv_dialect.quotechar,
        line_terminator=line_terminator,
        )
    return options

def identifier(s):
    """
    Return s as a quoted postgres identifier.
    Copied from ckan.datastore.helpers
    """
    return u'"' + s.replace(u'"', u'""').replace(u'\0', '') + u'"'

class PgLoaderLogMessages(object):
    '''Given lines of pgloader's output, it stitches multi-line log
    messages together and logs them as you go.
    '''
    def __init__(self, logger):
        self.current_message = 'pgloader output:\n'
        self.errored = False
        self.all_messages = []
        self.logger = logger

    def add_line(self, line):
        # 2017-04-06T11:19:44.045000Z LOG Main logs in ...
        log_msg_match = re.match(r'^[0-9-:T.]+Z (.+)$',
                                 line)
        if log_msg_match:
            # this is the start of a new log message
            # which means the end of the previous message
            if self.current_message:
                self.log_current_message()
            # strip off the timestamp
            line = log_msg_match.groups()[0]
            line = line.lstrip('LOG ')  # but keep other levels eg errors
        self.current_message += line

    def log_current_message(self):
        if self.current_message:
            errored = 'ERROR' in self.current_message \
                or 'FATAL' in self.current_message
            self.errored |= errored
            log_function = self.logger.error \
                if errored else self.logger.info
            self.current_message = self.current_message.strip()  # remove \n
            log_function(self.current_message)
            self.all_messages.append(self.current_message)
            self.current_message = ''

def convert_and_load_data(resource_id, data_rows, headers, headers_dicts,
                          ckan_url, api_key, dry_run, logger):
    '''DEPRECATED in favour of pgloader, although currently still needed for
    XLS files.

    Converts the data to JSON and then pushes it in chunks of 250 rows to
    datastore.
    '''
    def row_iterator():
        unknown_columns = set()
        for row in data_rows:
            data_row = {}
            for cell in row:
                column_name = cell.column.strip()
                if column_name not in headers and \
                        column_name not in unknown_columns:
                    logger.warn('Dropping data from cell of unknown column %s',
                                column_name)
                    unknown_columns.add(column_name)
                    continue
                data_row[column_name] = cell.value
            yield data_row
    row_dicts = row_iterator()

    if dry_run:
        return headers_dicts, row_dicts

    count = 0
    for i, records in enumerate(chunky(row_dicts, 250)):
        count += len(records)
        logger.info('Saving chunk {number}'.format(number=i))
        send_resource_to_datastore(resource_id, headers_dicts,
                                   records, api_key, ckan_url)

    logger.info('Successfully pushed {n} entries to "{res_id}".'.format(
        n=count, res_id=resource_id))
