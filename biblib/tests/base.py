"""
Common utilities used by the test classes
"""

import re
import app
import json
from flask import current_app
from flask.ext.testing import TestCase
from httpretty import HTTPretty
from models import db


class MockADSWSAPI(object):
    """
    Mock of the ADSWS API
    """
    def __init__(self, api_endpoint, response_kwargs={}):
        """
        Constructor
        :param api_endpoint: name of the API end point
        :param user_uid: unique API user ID to be returned
        :return: no return
        """

        self.api_endpoint = api_endpoint
        self.response_kwargs = response_kwargs

        def request_callback(request, uri, headers):
            """
            :param request: HTTP request
            :param uri: URI/URL to send the request
            :param headers: header of the HTTP request
            :return:
            """

            resp_dict = {
                'api-response': 'success',
                'token': request.headers.get(
                    'Authorization', 'No Authorization header passed!'
                )
            }

            for key in self.response_kwargs:
                resp_dict[key] = self.response_kwargs[key]

            resp = json.dumps(resp_dict)

            if self.response_kwargs['fail']:
                return 404, headers, {}
            else:
                return 200, headers, resp

        HTTPretty.register_uri(
            HTTPretty.GET,
            self.api_endpoint,
            body=request_callback,
            content_type='application/json'
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

class MockSolrBigqueryService(MockADSWSAPI):
    """
    Thin wrapper around the MockADSWSAPI class specficically for the Solr
    Bigquery end point.
    """

    def __init__(self, **kwargs):

        """
        Constructor
        :param api_endpoint: name of the API end point
        :param user_uid: unique API user ID to be returned
        :return: no return
        """

        self.kwargs = kwargs
        self.api_endpoint = current_app.config['BIBLIB_SOLR_BIG_QUERY_URL']

        def request_callback(request, uri, headers):
            """
            :param request: HTTP request
            :param uri: URI/URL to send the request
            :param headers: header of the HTTP request
            :return:
            """

            resp = {
                'responseHeader': {
                    'status': 0,
                    'QTime': 152,
                    'params': {
                        'fl': 'bibcode',
                        'q': '*:*',
                        'wt': 'json'
                    }
                },
                'response': {
                    'numFound': 1,
                    'start': 0,
                    'docs': [
                        {
                            'bibcode': 'bibcode'
                        }
                    ]
                }
            }

            resp = json.dumps(resp)

            status = self.kwargs.get('status', 200)
            return status, headers, resp

        HTTPretty.register_uri(
            HTTPretty.POST,
            self.api_endpoint,
            body=request_callback,
            content_type='application/json'
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

class MockEmailService(MockADSWSAPI):

    """
    Very thin wrapper around MockADSWSAPI given that I may want to use the
    default class later.
    """
    def __init__(self, stub_user, end_type='email'):

        if end_type == 'email':
            ep = stub_user.email
        elif end_type == 'uid':
            ep = stub_user.absolute_uid

        endpoint = '{api}/{ep}'.format(
            api=current_app.config['BIBLIB_USER_EMAIL_ADSWS_API_URL'],
            ep=ep
        )

        fail = False
        if stub_user.name == 'fail':
            fail = True

        response_kwargs = {
            'uid': stub_user.absolute_uid,
            'email': stub_user.email,
            'fail': fail,
        }

        super(MockEmailService, self).__init__(
            api_endpoint=endpoint,
            response_kwargs=response_kwargs
        )


class TestCaseDatabase(TestCase):
    """
    Base test class for when databases are being used.
    """

    def create_app(self):
        """
        Create the wsgi application

        :return: application instance
        """
        app_ = app.create_app(config_type='TEST')
        return app_

    def setUp(self):
        """
        Set up the database for use

        :return: no return
        """
        db.create_all()

    def tearDown(self):
        """
        Remove/delete the database and the relevant connections

        :return: no return
        """
        db.session.remove()
        db.drop_all()

class MockEndPoint(object):
    """
    Mock of the ADSWS API
    """
    def __init__(self, user_list):
        """
        Constructor
        :param api_endpoint: name of the API end point
        :param user_uid: unique API user ID to be returned
        :return: no return
        """

        def request_callback(request, uri, headers):
            """
            :param request: HTTP request
            :param uri: URI/URL to send the request
            :param headers: header of the HTTP request
            :return:
            """

            user_email = None
            user_uid = None
            try:
                user_info = int(uri.split('/')[-1])

                for user in user_list:
                    if user.absolute_uid == user_info:
                        user_email = user.email
                        user_uid = user.absolute_uid
                        break
            except TypeError:
                user_info = uri.split('/')[-1]

                for user in user_list:
                    if user.absolute_uid == user_info:
                        user_email = user.email
                        user_uid = user.absolute_uid
                        break

            resp_dict = {
                'api-response': 'success',
                'token': request.headers.get(
                    'Authorization', 'No Authorization header passed!'
                ),
                'email': user_email,
                'uid': user_uid,
            }

            return 200, headers, json.dumps(resp_dict)

        HTTPretty.register_uri(
            HTTPretty.GET,
            re.compile('{0}/\w+'.format(
                current_app.config['BIBLIB_USER_EMAIL_ADSWS_API_URL'])
            ),
            body=request_callback,
            content_type='application/json'
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