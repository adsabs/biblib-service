# encoding: utf-8
"""
HTTP Error messages
"""

API_HELP = 'http://adsabs.github.io/help/api/'

# Some user defined HTTP errors
DUPLICATE_LIBRARY_NAME_ERROR = dict(
    body='Library name given already exists and must be unique.',
    number=409
)
MISSING_LIBRARY_ERROR = dict(
    body='Library specified does not exist.',
    number=410
)
MISSING_DOCUMENT_ERROR = dict(
    body='Document specified does not exist.',
    number=410
)
MISSING_USERNAME_ERROR = dict(
    body='You did not supply enough user details. '
         'See the API documentation: {0}'.format(API_HELP),
    number=400
)
NO_PERMISSION_ERROR = dict(
    body='You do not have the correct permissions or the library does not '
         'exist.',
    number=403
)
WRONG_TYPE_ERROR = dict(
    body='You passed the wrong type. See the API documentation: {0}'
         .format(API_HELP),
    number=400
)
API_MISSING_USER_EMAIL = dict(
    body='User does not exist in the API database',
    number=404
)
API_MISSING_USER_UID = dict(
    body='User does not exist in the API database',
    number=404
)
SOLR_RESPONSE_MISMATCH_ERROR = dict(
    body='Solr response does not contain the same number of bibcodes as the '
         'request.',
    number=404
)