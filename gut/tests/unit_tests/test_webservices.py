"""
Test webservices
"""

__author__ = 'V. Sudilovsky'
__maintainer__ = 'V. Sudilovsky'
__copyright__ = 'ADS Copyright 2014, 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__license__ = 'MIT'

import sys
import os
PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import unittest
import time
import json
import app
from flask.ext.testing import TestCase
from flask import url_for
from httpretty import HTTPretty


class MockADSWSAPI:
    """
    Mock the ADSWS API
    """
    def __init__(self, api_endpoint):
        """
        Constructor

        :param api_endpoint: name of the API end point
        :return: no return
        """

        self.api_endpoint = api_endpoint

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


class TestWebservices(TestCase):
    """
    Tests that each route is an http response
    """
  
    def create_app(self):
        """
        Create the wsgi application

        :return: application instance
        """
        app_ = app.create_app()
        return app_

    def test_create_library_resource(self):
        """
        Test the /create route

        :return: no return
        """

        # Make the library
        url = url_for('gut.createlibrary', user=1234)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn('user', r.json)

        # Check the library exists in the database


if __name__ == '__main__':
    unittest.main(verbosity=2)
