"""
Test webservices
"""

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__credit__ = ['V. Sudilovsky']
__license__ = 'MIT'

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import app
import json
import unittest
from httpretty import HTTPretty
from flask.ext.testing import TestCase
from flask import url_for
from models import db
from views import DUPLICATE_LIBRARY_NAME_ERROR, MISSING_LIBRARY_ERROR, \
    MISSING_USERNAME_ERROR, NO_PERMISSION_ERROR
from views import USER_ID_KEYWORD
from tests.stubdata.stub_data import StubDataLibrary, StubDataDocument
from tests.base import MockADSWSAPI


class TestWebservices(TestCase):
    """
    Tests that each route is an http response
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
        self.stub_library, self.stub_user_id = StubDataLibrary().make_stub()
        self.stub_document = StubDataDocument().make_stub()

    def tearDown(self):
        """
        Remove/delete the database and the relevant connections

        :return: no return
        """

        db.session.remove()
        db.drop_all()

    def test_when_no_user_information_passed_to_user_post(self):
        """
        Test the /libraries route
        Tests that a KeyError is raised when the user ID is not passed

        :return: no return
        """

        url = url_for('userview')
        response = self.client.post(url)

        self.assertEqual(response.status_code, MISSING_USERNAME_ERROR['number'])
        self.assertEqual(response.json['error'], MISSING_USERNAME_ERROR['body'])

    def test_when_no_user_information_passed_to_user_get(self):
        """
        Test the /libraries route
        Tests that a KeyError is raised when the user ID is not passed

        :return: no return
        """

        url = url_for('userview')
        response = self.client.get(url)

        self.assertEqual(response.status_code, MISSING_USERNAME_ERROR['number'])
        self.assertEqual(response.json['error'], MISSING_USERNAME_ERROR['body'])

    def test_when_no_user_information_passed_to_library_post(self):
        """
        Test the /libraries/<library_uuid> route
        Tests that a KeyError is raised when the user ID is not passed

        :return: no return
        """

        url = url_for('libraryview', library='test')
        response = self.client.post(url)

        self.assertEqual(response.status_code, MISSING_USERNAME_ERROR['number'])
        self.assertEqual(response.json['error'], MISSING_USERNAME_ERROR['body'])

    def test_when_no_user_information_passed_to_library_get(self):
        """
        Test the /libraries route
        Tests that a KeyError is raised when the user ID is not passed

        :return: no return
        """

        url = url_for('libraryview', library='test')
        response = self.client.get(url)

        self.assertEqual(response.status_code, MISSING_USERNAME_ERROR['number'])
        self.assertEqual(response.json['error'], MISSING_USERNAME_ERROR['body'])

    def test_create_library_resource(self):
        """
        Test the /libraries route
        Creating the user and a library

        :return: no return
        """

        # Make the library
        url = url_for('userview')
        payload = self.stub_library
        headers = {USER_ID_KEYWORD: self.stub_user_id}

        response = self.client.post(
            url,
            data=json.dumps(payload),
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Check the library exists in the database
        url = url_for('userview', user=self.stub_user_id)

        response = self.client.get(
            url,
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        for library in response.json['libraries']:
            self.assertIn(self.stub_library['name'], library['name'])
            self.assertIn(
                self.stub_library['description'],
                library['description']
            )

    def test_add_document_to_library(self):
        """
        Test the /libraries/<> end point with POST to add a document

        :return: no return
        """

        # Make the library
        url = url_for('userview')
        payload = self.stub_library
        headers = {USER_ID_KEYWORD: self.stub_user_id}

        response = self.client.post(
            url,
            data=json.dumps(payload),
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        self.stub_document['action'] = 'add'
        url = url_for('libraryview', library=library_id)

        response = self.client.post(
            url,
            data=json.dumps(self.stub_document),
            headers=headers
        )

        # Check the library was created and documents exist
        response = self.client.get(
            url,
            data=json.dumps(payload),
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.stub_document['bibcode'], response.json['documents'])

    def test_remove_document_from_library(self):
        """
        Test the /libraries/<> end point with POST to remove a document

        :return:
        """
        # Make the library
        url = url_for('userview')
        headers = {USER_ID_KEYWORD: self.stub_user_id}

        response = self.client.post(
            url,
            data=json.dumps(self.stub_library),
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        self.stub_document['action'] = 'add'
        url = url_for('libraryview', library=library_id)

        response = self.client.post(
            url,
            data=json.dumps(self.stub_document),
            headers=headers
        )

        self.assertTrue(response.status, 200)

        # Delete the document
        self.stub_document['action'] = 'remove'
        url = url_for('libraryview', library=library_id)

        response = self.client.post(
            url,
            data=json.dumps(self.stub_document),
            headers=headers
        )

        self.assertTrue(response.status, 200)

        # Check the library is empty
        url = url_for('libraryview', library=library_id)

        response = self.client.get(
            url,
            headers=headers
        )

        self.assertTrue(len(response.json['documents']) == 0)

    def test_cannot_add_library_with_duplicate_names(self):
        """
        Test the /liraries end point with POST to ensure two libraries cannot
        have the same name

        :return: no return
        """

        # Make first library
        url = url_for('userview')
        headers = {USER_ID_KEYWORD: self.stub_user_id}

        response = self.client.post(
            url,
            data=json.dumps(self.stub_library),
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Make another one with the same name
        url = url_for('userview')

        response = self.client.post(
            url,
            data=json.dumps(self.stub_library),
            headers=headers
        )

        self.assertEqual(response.status_code,
                         DUPLICATE_LIBRARY_NAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         DUPLICATE_LIBRARY_NAME_ERROR['body'])

    def test_can_remove_a_library(self):
        """
        Tests the /libraries/<> end point with DELETE to remove a
        library from a user's libraries

        :return: no return
        """

        # Make first library
        url = url_for('userview')
        headers = {USER_ID_KEYWORD: self.stub_user_id}

        response = self.client.post(
            url,
            data=json.dumps(self.stub_library),
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Delete the library
        url = url_for('libraryview', user=self.stub_user_id, library=library_id)
        response = self.client.delete(
            url,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)

        # Check its deleted
        url = url_for('userview')

        response = self.client.get(
            url,
            headers=headers
        )

        self.assertTrue(len(response.json['libraries']) == 0,
                        response.json)

        url = url_for('libraryview', library=library_id)
        response = self.client.get(
            url,
            headers=headers
        )
        self.assertEqual(response.status_code,
                         NO_PERMISSION_ERROR['number'],
                         'Received response error: {0}'
                         .format(response.status_code))
        self.assertEqual(response.json['error'],
                         NO_PERMISSION_ERROR['body'])

        # Try to delete even though it does not exist, this should return
        # some errors from the server
        url = url_for('libraryview', library=library_id)

        response = self.client.delete(
            url,
            headers=headers
        )

        self.assertEqual(response.status_code, MISSING_LIBRARY_ERROR['number'])
        self.assertEqual(response.json['error'],
                         MISSING_LIBRARY_ERROR['body'])

    def test_user_without_permission_cannot_access_private_library(self):
        """
        Tests the /libraries/<> end point to ensure that a user cannot
        access the library unless they have permissions

        :return: no return
        """

        # Make a library for a given user, user 1
        url = url_for('userview')
        headers_1 = {USER_ID_KEYWORD: self.stub_user_id}

        response = self.client.post(
            url,
            data=json.dumps(self.stub_library),
            headers=headers_1
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Request from user 2 to see the library should be refused if user 2
        # does not have the permissions
        # Check the library is empty
        headers_2 = {USER_ID_KEYWORD: self.stub_user_id+1}
        url = url_for('libraryview', library=library_id)

        response = self.client.get(
            url,
            headers=headers_2
        )

        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

    def test_can_add_read_permissions(self):
        """
        Tests that a user can add read permissions to another user for one of
        their libraries.

        :return: no return
        """

        # Initialise HTTPretty for the URL for the API

        # Make a library for a given user, user 1
        url = url_for('userview')
        headers_1 = {USER_ID_KEYWORD: self.stub_user_id}
        headers_2 = {USER_ID_KEYWORD: self.stub_user_id+1}

        response = self.client.post(
            url,
            data=json.dumps(self.stub_library),
            headers=headers_1
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Make a library for user 2 so that we have an account
        response = self.client.post(
            url,
            data=json.dumps(self.stub_library),
            headers=headers_2
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Add the permissions for user 2
        url = url_for('permissionview', library=library_id)
        email = 'user@email.com'

        data_permissions = {
            'email': email,
            'permission': 'read',
            'value': True
        }

        # This requires communication with the API
        test_endpoint = '{api}/{email}'.format(
            api=self.app.config['USER_EMAIL_ADSWS_API_URL'],
            email=data_permissions['email']
        )
        with MockADSWSAPI(test_endpoint, user_uid=self.stub_user_id+1):

            response = self.client.post(
                url,
                data=json.dumps(data_permissions),
                headers=headers_1
            )

        self.assertEqual(response.status_code, 200)

        # The user can now access the content of the library
        url = url_for('libraryview', library=library_id)

        response = self.client.get(
            url,
            headers=headers_2
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue('documents' in response.json)


    def test_cannot_change_permission_without_permission(self):
        """
        Test that a user without permissions cannot alter the permissions
        of a library.
        :return:
        """
        # Make a library for a given user, user 1
        url = url_for('userview')
        headers_1 = {USER_ID_KEYWORD: self.stub_user_id}
        headers_2 = {USER_ID_KEYWORD: self.stub_user_id+1}

        response = self.client.post(
            url,
            data=json.dumps(self.stub_library),
            headers=headers_1
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Make a library for user 2 so that we have an account
        response = self.client.post(
            url,
            data=json.dumps(self.stub_library),
            headers=headers_2
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # User 2 with no permissions tries to modify user 1
        url = url_for('permissionview', library=library_id)
        email = 'user@email.com'

        data_permissions = {
            'email': email,
            'permission': 'read',
            'value': True
        }

        # This requires communication with the API
        # User requesting: user 2 that has no permissions
        # To modify: user 2 is trying to modify user 1, which is the owner of
        # the library
        test_endpoint = '{api}/{email}'.format(
            api=self.app.config['USER_EMAIL_ADSWS_API_URL'],
            email=data_permissions['email']
        )
        # E-mail requested should correspond to the owner of the library,
        # which in this case is user 1
        with MockADSWSAPI(test_endpoint, user_uid=self.stub_user_id):

            response = self.client.post(
                url,
                data=json.dumps(data_permissions),
                headers=headers_2
            )

        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
