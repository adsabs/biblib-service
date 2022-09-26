# encoding: utf-8
"""
Configuration file. Please prefix application specific config values with
the application name.
"""

import os
import pwd

LOG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), './')
)
LOG_PATH = '{home}/logs/'.format(home=LOG_PATH)
LOG_STDOUT = True

if not os.path.isdir(LOG_PATH):
    os.mkdir(LOG_PATH)

# For running tests on TravisCI
SQLALCHEMY_BINDS = {
    'libraries': 'postgresql+psycopg2://postgres:postgres@localhost:5432/test_biblib'
}

ENVIRONMENT = os.getenv('ENVIRONMENT', 'unset-env').lower()

# These lines are necessary only if the app needs to be a client of the
# adsws-api
BIBLIB_TWOPOINTOH_SERVICE_URL = 'https://api.adsabs.edu/v1/harbour'
BIBLIB_CLASSIC_SERVICE_URL = 'https://api.adsabs.edu/v1/harbour'
BIBLIB_SOLR_BIG_QUERY_URL = 'https://api.adsabs.search/v1/bigquery'
BIBLIB_SOLR_SEARCH_URL = 'https://api.adsabs.harvard.edu/v1/search/query'
BIBLIB_USER_EMAIL_ADSWS_API_URL = 'https://api.adsabs.harvard.edu/v1/user'
BIBLIB_ADSWS_API_DB_URI = 'sqlite:////tmp/test.db'
BIBLIB_MAX_ROWS = 2000
BIGQUERY_MAX_ROWS = 200
BIBLIB_SOLR_BIG_QUERY_MIN = 10

MAIL_DEFAULT_SENDER = 'no-reply@adslabs.org'

# when set, the service will use it instead of the user's token
# (for requests where it makes sense - not all)
SERVICE_TOKEN = None

# myADS token to allow general notifications that contain docs(library/<id>)
READONLY_ALL_LIBRARIES_TOKEN = None
