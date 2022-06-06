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
    body='User does not have an ADS account',
    number=404
)
API_MISSING_USER_UID = dict(
    body='User does not have an ADS account',
    number=404
)
SOLR_RESPONSE_MISMATCH_ERROR = dict(
    body='Solr response does not contain the same number of bibcodes as the '
         'request.',
    number=404
)
NO_CLASSIC_ACCOUNT = dict(
    body='This user has not setup an ADS Classic account',
    number=400
)
NO_LIBRARY_SPECIFIED_ERROR = dict(
    body='You did not specify the secondary libraries needed to perform the operation.',
    number=400
)
TOO_MANY_LIBRARIES_SPECIFIED_ERROR = dict(
    body='Too many secondary libraries specified; only one secondary library allowed.',
    number=400
)
BAD_LIBRARY_ID_ERROR = dict(
    body='Bad library ID was passed',
    number=400
)
def INVALID_BIBCODE_SPECIFIED_ERROR(bad_bibcodes, full_error):
    #If some bibcodes are added, we do not want to return an error, but we still want to inform the user.
    if not full_error:
        err = 200
    #If no bibcodes are added, then we want to return an error.
    else:
        err = 400
    
    return dict(
        body='The following idenitifers were not found in ADS: {}.'.format(bad_bibcodes),
        action=err
    )