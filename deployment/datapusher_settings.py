import uuid
import messytables

DEBUG = False
TESTING = False
SECRET_KEY = str(uuid.uuid4())
USERNAME = str(uuid.uuid4())
PASSWORD = str(uuid.uuid4())

NAME = 'datapusher'

# database

SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/job_store.db'

# webserver host and port

HOST = '0.0.0.0'
PORT = 8800

# logging

#FROM_EMAIL = 'server-error@example.com'
#ADMINS = ['yourname@example.com']  # where to send emails

#LOG_FILE = '/tmp/ckan_service.log'
STDERR = True

TYPES = [messytables.StringType, messytables.DecimalType, messytables.IntegerType, messytables.DateType, messytables.BoolType]
TYPE_MAPPING = {
    'String': 'text',
    # 'int' may not be big enough,
    # and type detection may not realize it needs to be big
    'Integer': 'numeric',
    'Decimal': 'numeric',
    # Date guessing is very aggressive, with '00:10' being transformed in a
    # timestamp with date.now().
    # Disabling for now.
    # 'Date': 'timestamp',
    'Bool': 'boolean'
}
