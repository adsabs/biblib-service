# encoding: utf-8
"""
Configuration file. Please prefix application specific config values with
the application name.
"""

import os
import pwd

LOG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../')
)
LOG_PATH = '{home}/logs/'.format(home=LOG_PATH)

if not os.path.isdir(LOG_PATH):
    os.mkdir(LOG_PATH)

# For running tests on TravisCI
SQLALCHEMY_BINDS = {
    'libraries': 'postgresql+psycopg2://postgres:@localhost/testdb'
}

BIBLIB_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(levelname)s\t%(process)d '
                      '[%(asctime)s]:\t%(message)s',
            'datefmt': '%m/%d/%Y %H:%M:%S',
        }
    },
    'handlers': {
        'console': {
            'formatter': 'default',
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# These lines are necessary only if the app needs to be a client of the
# adsws-api
BIBLIB_TWOPOINT_OH_SERVICE_URL = 'https://api.adsabs.edu/v1/harbour'
BIBLIB_CLASSIC_SERVICE_URL = 'https://api.adsabs.edu/v1/harbour'
BIBLIB_SOLR_BIG_QUERY_URL = 'https://api.adsabs.search/v1/bigquery'
BIBLIB_USER_EMAIL_ADSWS_API_URL = 'https://api.adsabs.harvard.edu/v1/user'
BIBLIB_ADSWS_API_TOKEN = 'this is a secret api token!'
BIBLIB_ADSWS_API_DB_URI = 'sqlite:////tmp/test.db'
