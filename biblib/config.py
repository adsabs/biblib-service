"""
Configuration file. Please prefix application specific config values with
the application name.
"""

SAMPLE_APPLICATION_PARAM = {
    'message': 'config params should be prefixed with the application name',
    'reason': 'this will allow easier integration if this app is incorporated'
              ' as a python module',
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
        'file': {
            'formatter': 'default',
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/tmp/app.log',
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
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Database for microservice
SQLALCHEMY_BINDS = {'libraries': 'sqlite:////tmp/test.db'} 

# These lines are necessary only if the app needs to be a client of the API
BIBLIB_USER_EMAIL_ADSWS_API_URL = 'https://api.adsabs.harvard.edu/v1/user'
BIBLIB_ADSWS_API_TOKEN = 'this is a secret api token!'
