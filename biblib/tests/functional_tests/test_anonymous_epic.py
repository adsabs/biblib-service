"""
Functional test

Anonymous Epic

Storyboard is defined within the comments of the program itself
"""

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__license__ = 'MIT'

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import app
import json
import unittest
from views import USER_ID_KEYWORD, NO_PERMISSION_ERROR
from models import db
from flask.ext.testing import TestCase
from flask import url_for
from tests.stubdata.stub_data import StubDataLibrary, StubDataDocument, \
    StubDataUser
from tests.base import MockADSWSAPI


class TestAnonymousEpic(TestCase):
    """
    Base class used to test the Big Share Admin Epic
    """
    def create_app(self):
        """
        Create the wsgi application for flask

        :return: application instance
        """
        return app.create_app(config_type='TEST')

    def setUp(self):
        """
        Set up the database for use

        :return: no return
        """
        db.create_all()

    def tearDown(self):
        """
        Remove/delete the database and the relevant connections
!
        :return: no return
        """
        db.session.remove()
        db.drop_all()

    def test_anonymous_epic(self):
        """
        Carries out the epic 'Anonymous', where a user tries to access a
        private library and also a public library. The user also (artificial)
        tries to access any other endpoints that do not have any scopes set

        :return: no return
        """

        # Define two sets of stub data
        # user: who makes a library (e.g., Dave the librarian)
        # anon: someone using the BBB client
        uid_anonymous = StubDataUser().get_user()
        headers_anonymous = {USER_ID_KEYWORD: uid_anonymous}
        email_anonymous = "mary@email.com"

        library_dave, uid_dave = StubDataLibrary().make_stub()
        headers_dave = {USER_ID_KEYWORD: uid_dave}
        email_dave = "dave@email.com"

        # Dave makes two libraries
        # One private library
        # One public library
        url = url_for('userview')

        library_dave['public'] = False
        library_dave['name'] = 'Private'
        response = self.client.post(
            url,
            data=json.dumps(library_dave),
            headers=headers_dave
        )
        library_id_private = response.json['id']
        self.assertEqual(response.status_code, 200, response)

        library_dave['public'] = True
        library_dave['name'] = 'Public'
        response = self.client.post(
            url,
            data=json.dumps(library_dave),
            headers=headers_dave
        )
        library_id_public = response.json['id']

        # Anonymous user tries to access the private library. But cannot.
        url = url_for('libraryview', library=library_id_private)
        response = self.client.get(
            url,
            headers=headers_anonymous
        )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

        # Anonymous user tries to access the public library. And can.
        url = url_for('libraryview', library=library_id_public)
        response = self.client.get(
            url,
            headers=headers_anonymous
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('documents', response.json)

        number_of_scopeless = 0
        response = self.client.get('/resources')
        for end_point in response.json.keys():

            if len(response.json[end_point]['scopes']) == 0:
                number_of_scopeless += 1
                endpoint = end_point

        self.assertEqual(1, number_of_scopeless)
        self.assertEqual('/libraries/<string:library>', endpoint)

if __name__ == '__main__':
    unittest.main(verbosity=2)