"""
Common utilities used by the test classes
"""

import re
import json
from flask import current_app
from flask_testing import TestCase
from biblib import app
from biblib.models import Base
from httpretty import HTTPretty
from biblib.utils import assert_unsorted_equal
import testing.postgresql


class HTTPrettyContext(object):

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


class MockClassicService(HTTPrettyContext):

    def __init__(self, **kwargs):
        """
        Constructor
        """
        self.kwargs = kwargs

        def request_callback(request, uri, headers):
            """
            :param request: HTTP request
            :param uri: URI/URL to send the request
            :param headers: header of the HTTP request
            """

            response = {}
            try:
                libraries = self.kwargs['libraries']
                response['libraries'] = []
                for library in libraries:
                    response['libraries'].append({
                        'documents': library.bibcode,
                        'name': library.name,
                        'description': library.description
                    })
            except KeyError:
                response = self.kwargs.get('body', {})

            return self.kwargs.get('status', 200), headers, json.dumps(response)

        HTTPretty.register_uri(
            HTTPretty.GET,
            re.compile('{}.*'.format(current_app.config['BIBLIB_CLASSIC_SERVICE_URL'])),
            body=request_callback,
            content_type='application/json'
        )


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
        self.page = 0
        self.page_size = current_app.config['BIGQUERY_MAX_ROWS']

        def request_callback(request, uri, headers):
            """
            :param request: HTTP request
            :param uri: URI/URL to send the request
            :param headers: header of the HTTP request
            :return:
            """

            if self.kwargs.get('solr_docs'):
                docs = self.kwargs['solr_docs']
                
            elif self.kwargs.get('canonical_bibcode'):
                if not self.kwargs.get('invalid'):
                    docs = []
                    canonical_bibcodes = self.kwargs.get('canonical_bibcode')
                    for i in range(self.page*self.page_size, min(len(canonical_bibcodes), (self.page + 1)*self.page_size)):
                        docs.append({'bibcode': canonical_bibcodes[i]})
                else:
                    #This treats every other odd bibcode as valid.
                    docs = []
                    canonical_bibcodes = self.kwargs.get('canonical_bibcode')
                    i = self.page*self.page_size
                    while len(docs) <  min(len(canonical_bibcodes), (self.page + 1)*self.page_size) and i < len(canonical_bibcodes):
                        if i%4-1 == 0:                        
                            docs.append({'bibcode': canonical_bibcodes[i]})
                        i+=1
            else:
                docs = [{'bibcode': 'bibcode'} for i
                        in range(self.kwargs.get('number_of_bibcodes', 1))]
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
                    'numFound': len(docs),
                    'start': self.page*self.page_size,
                    'docs': docs
                }
            }

            if self.kwargs.get('fail', False):
                resp.pop('response')

            resp = json.dumps(resp)

            status = self.kwargs.get('status', 200)
            self.page += 1
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
        #adding this allows for checking pagination calls.
        return self.page
        HTTPretty.reset()
        HTTPretty.disable()

class MockSolrQueryService(MockADSWSAPI):
    """
    Thin wrapper around the MockADSWSAPI class specficically for the Solr
    Query end point.
    """

    def __init__(self, **kwargs):

        """
        Constructor
        :param api_endpoint: name of the API end point
        :param user_uid: unique API user ID to be returned
        :return: no return
        """

        self.kwargs = kwargs
        self.api_endpoint = current_app.config['BIBLIB_SOLR_SEARCH_URL']

        def request_callback(request, uri, headers):
            """
            :param request: HTTP request
            :param uri: URI/URL to send the request
            :param headers: header of the HTTP request
            :return:
            """
            if not self.kwargs.get('invalid'):
                #Sets all generated bibcodes as valid
                if self.kwargs.get('canonical_bibcode'):
                    docs = []
                    canonical_bibcodes = self.kwargs.get('canonical_bibcode')
                    for i in range(len(canonical_bibcodes)):
                        docs.append({'bibcode': canonical_bibcodes[i]})
                    input_query ="identifier:(" + " OR ".join(canonical_bibcodes)+")"
                else:
                    docs = [{'bibcode': 'bibcode'} for i
                            in range(self.kwargs.get('number_of_bibcodes', 1))]
                    input_query = ""
            
            else:
                if self.kwargs.get('canonical_bibcode'):
                    docs = []
                    canonical_bibcodes = self.kwargs.get('canonical_bibcode')
                    #Sets all odd indexed bibcodes as valid, all other bibcodes are invalid.        
                    for i in range(len(canonical_bibcodes)):
                        if i%2-1 == 0:
                            docs.append({'bibcode': canonical_bibcodes[i]})
                    input_query ="identifier:(" + " OR ".join(canonical_bibcodes)+")"
                else:
                    docs = [{'bibcode': 'bibcode'} for i
                            in range(self.kwargs.get('number_of_bibcodes', 1))]
                    input_query = ""

            resp = {
                'responseHeader': {
                    'status': 0,
                    'QTime': 152,
                    'params': {
                        'fl': 'bibcode',
                        'q': input_query,
                        'wt': 'json'
                    }
                },
                'response': {
                    'numFound': len(docs),
                    'start': 0,
                    'docs': docs
                }
            }

            if self.kwargs.get('fail', False):
                resp.pop('response')

            resp = json.dumps(resp)

            status = self.kwargs.get('status', 200)
            return status, headers, resp

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

class MockSolrQueryService(MockADSWSAPI):
    """
    Thin wrapper around the MockADSWSAPI class specficically for the Solr
    Query end point.
    """

    def __init__(self, **kwargs):

        """
        Constructor
        :param api_endpoint: name of the API end point
        :param user_uid: unique API user ID to be returned
        :return: no return
        """

        self.kwargs = kwargs
        self.api_endpoint = current_app.config['BIBLIB_SOLR_SEARCH_URL']

        def request_callback(request, uri, headers):
            """
            :param request: HTTP request
            :param uri: URI/URL to send the request
            :param headers: header of the HTTP request
            :return:
            """
            if not self.kwargs.get('invalid'):
                if self.kwargs.get('canonical_bibcode'):
                    docs = []
                    canonical_bibcodes = kwargs.get('canonical_bibcode')
                    for i in range(len(canonical_bibcodes)):
                        docs.append({'bibcode': canonical_bibcodes[i]})
                        print(docs)
                    input_query ="identifier:("+" OR ".join(canonical_bibcodes)+")"
                    params = {
                        'fl': 'bibcode',
                        'q': input_query,
                        'wt': 'json'
                    }
                else:
                    docs = [{'bibcode': 'bibcode'} for i
                            in range(kwargs.get('number_of_bibcodes', 1))]
                    input_query = ""
                    params = {
                        'fl': 'bibcode',
                        'q': input_query,
                        'wt': 'json'
                    }
            
            else:
                if self.kwargs.get('canonical_bibcode'):
                    docs = []
                    canonical_bibcodes = kwargs.get('canonical_bibcode')
                    for i in range(len(canonical_bibcodes)):
                        if i%2-1 == 0:
                            docs.append({'bibcode': canonical_bibcodes[i]})
                            print(docs)
                    input_query ="identifier:("+" OR ".join(canonical_bibcodes)+")"
                    params = {
                        'fl': 'bibcode',
                        'q': input_query,
                        'wt': 'json'
                    }
                else:
                    docs = [{'bibcode': 'bibcode'} for i
                            in range(kwargs.get('number_of_bibcodes', 1))]
                    input_query = ""
                    params = {
                        'fl': 'bibcode',
                        'q': input_query,
                        'wt': 'json'
                    }

            if self.kwargs.get('params'): params = self.kwargs.get('params')

            resp = {
                'responseHeader': {
                    'status': 0,
                    'QTime': 152,
                    'params': params
                },
                'response': {
                    'numFound': len(docs),
                    'start': 0,
                    'docs': docs
                }
            }

            if self.kwargs.get('fail', False):
                resp.pop('response')

            resp = json.dumps(resp)

            status = self.kwargs.get('status', 200)
            return status, headers, resp

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

def SolrQueryServiceresp(**kwargs):
    if kwargs.get('canonical_bibcode'):
        docs = []
        canonical_bibcodes = kwargs.get('canonical_bibcode')
        for i in range(len(canonical_bibcodes)):
            docs.append({'bibcode': canonical_bibcodes[i]})
            print(docs)
        input_query ="identifier:("+" OR ".join(canonical_bibcodes)+")"
    else:
        docs = [{'bibcode': 'bibcode'} for i
                in range(kwargs.get('number_of_bibcodes', 1))]
        input_query = ""

    resp = {
        'responseHeader': {
            'status': 0,
            'QTime': 152,
            'params': {
                'fl': 'bibcode',
                'q': input_query,
                'wt': 'json'
            }
        },
        'response': {
            'numFound': len(docs),
            'start': 0,
            'docs': docs
        }
    }

    return resp, 200

def SolrQueryServicerespInvalid(**kwargs):
    if kwargs.get('canonical_bibcode'):
        docs = []
        canonical_bibcodes = kwargs.get('canonical_bibcode')
        for i in range(len(canonical_bibcodes)):
            if i%2-1 == 0:
                docs.append({'bibcode': canonical_bibcodes[i]})
                print(docs)
        input_query ="identifier:("+" OR ".join(canonical_bibcodes)+")"
    else:
        docs = [{'bibcode': 'bibcode'} for i
                in range(kwargs.get('number_of_bibcodes', 1))]
        input_query = ""

    resp = {
        'responseHeader': {
            'status': 0,
            'QTime': 152,
            'params': {
                'fl': 'bibcode',
                'q': input_query,
                'wt': 'json'
            }
        },
        'response': {
            'numFound': len(docs),
            'start': 0,
            'docs': docs
        }
    }

    return resp, 200


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
            'id': stub_user.absolute_uid,
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

    postgresql_url_dict = {
        'port': 1234,
        'host': '127.0.0.1',
        'user': 'postgres',
        'database': 'test'
    }
    postgresql_url = 'postgresql://{user}@{host}:{port}/{database}'\
        .format(
            user=postgresql_url_dict['user'],
            host=postgresql_url_dict['host'],
            port=postgresql_url_dict['port'],
            database=postgresql_url_dict['database']
        )

    def create_app(self):
        """
        Create the wsgi application

        :return: application instance
        """
        app_ = app.create_app(**{
               'SQLALCHEMY_DATABASE_URI': self.postgresql_url,
               'SQLALCHEMY_ECHO': True,
               'TESTING': True,
               'PROPAGATE_EXCEPTIONS': True,
               'TRAP_BAD_REQUEST_ERRORS': True,
               'VAULT_BUMBLEBEE_OPTIONS': {'foo': 'bar'}
            })
        return app_

    @classmethod
    def setUpClass(cls):
        cls.postgresql = \
            testing.postgresql.Postgresql(**cls.postgresql_url_dict)

    @classmethod
    def tearDownClass(cls):
        cls.postgresql.stop()

    def setUp(self):
        """
        Set up the database for use

        :return: no return
        """

        current_app.logger.info('Setting up db on: {0}'
                                .format(current_app.config['SQLALCHEMY_BINDS']))
        Base.metadata.create_all(bind=self.app.db.engine)

    def tearDown(self):
        """
        Remove/delete the database and the relevant connections

        :return: no return
        """
        self.app.db.session.remove()
        Base.metadata.drop_all(bind=self.app.db.engine)

    def assertUnsortedEqual(self, hashable_1, hashable_2):
        """
        Wrapper function to make the tests easier to read. Wraps the utility
        function that compares if two hashables are equal or not.
        :param hashable_1: hashable value 1
        :param hashable_2: hashable value 2
        """

        if not assert_unsorted_equal(hashable_1, hashable_2):
            raise Exception('Not Equal: arg1[{0}], arg2[{1}]'
                            .format(hashable_1, hashable_2))

    def assertUnsortedNotEqual(self, hashable_1, hashable_2):
        """
        Wrapper function to make the tests easier to read. Wraps the utility
        function that compares if two hashables are equal or not.
        :param hashable_1: hashable value 1
        :param hashable_2: hashable value 2
        """

        if assert_unsorted_equal(hashable_1, hashable_2):
            raise Exception('Equal: arg1[{0}], arg2[{1}]'
                            .format(hashable_1, hashable_2))


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
