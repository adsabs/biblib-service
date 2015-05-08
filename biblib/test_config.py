"""
Configuration file
"""

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__credit__ = ['V. Sudilovsky']
__license__ = 'MIT'

import pwd

SAMPLE_APPLICATION_PARAM = {
    'message': 'config params should be prefixed with the application name',
    'reason': 'this will allow easier integration if this app is incorporated'
              ' as a python module',
}
SAMPLE_APPLICATION_ADSWS_API_URL = 'https://api.adsabs.harvard.edu'

# Database for microservice
try:
    # For working on a VM as user vagrant
    pwd.getpwnam('vagrant')
    SQLALCHEMY_DATABASE_URI = \
        'postgresql+psycopg2://vagrant:vagrant@localhost/testdb'
except KeyError:
    # For running tests on TravisCI
    SQLALCHEMY_DATABASE_URI = \
        'postgresql+psycopg2://postgres:@localhost/testdb'

# These lines are necessary only if the app needs to be a client of the
# adsws-api
from client import Client
SAMPLE_APPLICATION_ADSWS_API_TOKEN = 'this is a secret api token!'
SAMPLE_APPLICATION_CLIENT = Client(
    {'TOKEN': SAMPLE_APPLICATION_ADSWS_API_TOKEN}
)
