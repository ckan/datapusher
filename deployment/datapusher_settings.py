import uuid

DEBUG = False
TESTING = False
SECRET_KEY = str(uuid.uuid4())
USERNAME = str(uuid.uuid4())
PASSWORD = str(uuid.uuid4())

NAME = 'datapusher'

# database to hold the queue (ckan-service-provider)

SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/job_store.db'

# datastore database
# (use the same value as you have in ckan's .ini file ckan.datastore.write_url)

CKAN_DATASTORE_WRITE_URL = \
    'postgresql://ckan_default:pass@localhost/datastore_default'

# webserver host and port

HOST = '0.0.0.0'
PORT = 8800

# Use pgloader or the legacy 'convert and load in chunks' code
USE_PGLOADER = True

# Dropping indexes significantly speeds up pgloader (approx 10x). However it
# requires pgloader version 3.3.0219f55 or later.
DROP_INDEXES = True

# logging

#FROM_EMAIL = 'server-error@example.com'
#ADMINS = ['yourname@example.com']  # where to send emails

#LOG_FILE = '/tmp/ckan_service.log'
STDERR = True
