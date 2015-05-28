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

SAMPLE_APPLICATION_PARAM = {
    'message': 'config params should be prefixed with the application name',
    'reason': 'this will allow easier integration if this app is incorporated'
              ' as a python module',
}

# Database for microservice
try:
    # For working on a VM as user vagrant
    pwd.getpwnam('vagrant')
    SQLALCHEMY_DATABASE_URI = \
        'postgresql+psycopg2://vagrant:vagrant@localhost/testdb'

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
            'file': {
                'formatter': 'default',
                'level': 'DEBUG',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'filename': 'app.log',
            },
            'console': {
                'formatter': 'default',
                'level': 'DEBUG',
                'class': 'logging.StreamHandler'
            },
            'syslog': {
                'formatter': 'default',
                'level': 'DEBUG',
                'class': 'logging.handlers.SysLogHandler',
                'address': '/dev/log'
            }
        },
        'loggers': {
            '': {
                'handlers': ['file'],
                'level': 'DEBUG',
                'propagate': True,
            },
        },
    }

except KeyError:
    # For running tests on TravisCI
    SQLALCHEMY_DATABASE_URI = \
        'postgresql+psycopg2://postgres:@localhost/testdb'

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
USER_EMAIL_ADSWS_API_URL = 'https://api.adsabs.harvard.edu/v1/user'
BIBLIB_ADSWS_API_TOKEN = 'this is a secret api token!'
