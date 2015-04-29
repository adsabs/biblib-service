"""
Configuration file
"""

__author__ = 'V. Sudilovsky'
__maintainer__ = 'V. Sudilovsky'
__copyright__ = 'ADS Copyright 2014, 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__license__ = 'MIT'

SAMPLE_APPLICATION_PARAM = {
    'message': 'config params should be prefixed with the application name',
    'reason': 'this will allow easier integration if this app is incorporated'
              ' as a python module',
}
SAMPLE_APPLICATION_ADSWS_API_URL = 'https://api.adsabs.harvard.edu'


# These lines are necessary only if the app needs to be a client of the
# adsws-api
from client import Client
SAMPLE_APPLICATION_ADSWS_API_TOKEN = 'this is a secret api token!'
SAMPLE_APPLICATION_CLIENT = Client(
    {'TOKEN': SAMPLE_APPLICATION_ADSWS_API_TOKEN}
)
