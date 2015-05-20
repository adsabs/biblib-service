"""
Common utilities used by the test classes
"""

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__credit__ = ['V. Sudilovsky']
__license__ = 'MIT'

import json
from httpretty import HTTPretty


class MockADSWSAPI(object):
    """
    Mock of the ADSWS API
    """
    def __init__(self, api_endpoint, user_uid=1):
        """
        Constructor
        :param api_endpoint: name of the API end point
        :param user_uid: unique API user ID to be returned
        :return: no return
        """

        self.api_endpoint = api_endpoint
        self.user_uid = user_uid

        def request_callback(request, uri, headers):
            """
            :param request: HTTP request
            :param uri: URI/URL to send the request
            :param headers: header of the HTTP request
            :return:
            """
            resp = json.dumps(
                {
                    'api-response': 'success',
                    'uid': self.user_uid,
                    'token': request.headers.get(
                        'Authorization', 'No Authorization header passed!'
                    )
                }
            )
            return 200, headers, resp

        HTTPretty.register_uri(
            HTTPretty.GET,
            self.api_endpoint,
            body=request_callback,
            content_type="application/json"
        )

    def __enter__(self):
        """
        Defines the behaviour for __enter__
        :return: no return
        """

        HTTPretty.enable()

    def __exit__(self, etype, value, traceback):
        """
        Defines the behaviour for __exit__
        :param etype: exit type
        :param value: exit value
        :param traceback: the traceback for the exit
        :return: no return
        """

        HTTPretty.reset()
        HTTPretty.disable()

