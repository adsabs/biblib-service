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
import unittest
import json
from flask.ext.testing import TestCase
from flask import url_for
from models import db
from views import DUPLICATE_LIBRARY_NAME_ERROR, MISSING_LIBRARY_ERROR
from tests.stubdata.stub_data import StubDataLibrary, StubDataDocument


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

    def test_create_library_resource(self):
        """
        Test the /users/<> route

        :return: no return
        """

        # Make the library
        url = url_for('userview', user=self.stub_user_id)
        response = self.client.post(url, data=json.dumps(self.stub_library))
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Check the library exists in the database
        url = url_for('userview', user=self.stub_user_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        for library in response.json['libraries']:
            self.assertIn(self.stub_library['name'], library['name'])
            self.assertIn(
                self.stub_library['description'],
                library['description']
            )

    def test_add_document_to_library(self):
        """
        Test the /users/<>/libraries/<> end point with POST to add a document

        :return: no return
        """

        # Make the library
        url = url_for('userview', user=self.stub_user_id)
        response = self.client.post(url, data=json.dumps(self.stub_library))
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        self.stub_document['action'] = 'add'
        url = url_for('libraryview', user=self.stub_user_id, library=library_id)
        response = self.client.post(url, data=json.dumps(self.stub_document))

        # Check the library was created and documents exist
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.stub_document['bibcode'], response.json['documents'])

    def test_remove_document_from_library(self):
        """
        Test the /users/<>/libraries/<> end point with POST to remove a document

        :return:
        """
        # Make the library
        url = url_for('userview', user=self.stub_user_id)
        response = self.client.post(url, data=json.dumps(self.stub_library))
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        self.stub_document['action'] = 'add'
        url = url_for('libraryview', user=self.stub_user_id, library=library_id)
        response = self.client.post(url, data=json.dumps(self.stub_document))
        self.assertTrue(response.status, 200)

        # Delete the document
        self.stub_document['action'] = 'remove'
        url = url_for('libraryview', user=self.stub_user_id, library=library_id)
        response = self.client.post(url, data=json.dumps(self.stub_document))
        self.assertTrue(response.status, 200)

        # Check the library is empty
        url = url_for('libraryview', user=self.stub_user_id, library=library_id)
        response = self.client.get(url)
        self.assertTrue(len(response.json['documents']) == 0)

    def test_cannot_add_library_with_duplicate_names(self):
        """
        Test the /users/<> end point with POST to ensure two libraries cannot
        have the same name

        :return: no return
        """

        # Make first library
        url = url_for('userview', user=self.stub_user_id)
        response = self.client.post(url, data=json.dumps(self.stub_library))
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Make another one with the same name
        url = url_for('userview', user=self.stub_user_id)
        response = self.client.post(url, data=json.dumps(self.stub_library))
        self.assertEqual(response.status_code,
                         DUPLICATE_LIBRARY_NAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         DUPLICATE_LIBRARY_NAME_ERROR['body'])

    def test_can_remove_a_library(self):
        """
        Tests the /users/<>/library/<> end point with DELETE to remove a
        library from a user's libraries

        :return: no return
        """

        # Make first library
        url = url_for('userview', user=self.stub_user_id)
        response = self.client.post(url, data=json.dumps(self.stub_library))
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Delete the library
        url = url_for('libraryview', user=self.stub_user_id, library=library_id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)

        # Check its deleted
        url = url_for('userview', user=self.stub_user_id)
        response = self.client.get(url)
        self.assertTrue(len(response.json['libraries']) == 0,
                        response.json)

        url = url_for('libraryview', user=self.stub_user_id, library=library_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code,
                         MISSING_LIBRARY_ERROR['number'],
                         'Received response error: {0}'
                         .format(response.status_code))
        self.assertEqual(response.json['error'],
                         MISSING_LIBRARY_ERROR['body'])

        # Try to delete even though it does not exist, this should return
        # some errors from the server
        url = url_for('libraryview', user=self.stub_user_id, library=library_id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, MISSING_LIBRARY_ERROR['number'])
        self.assertEqual(response.json['error'],
                         MISSING_LIBRARY_ERROR['body'])

    def test_user_without_permission_cannot_access_library(self):
        """
        Tests the /users/<>/library/<> end point to ensure that a user cannot
        access the library unless they have permissions

        :return: no return
        """

if __name__ == '__main__':
    unittest.main(verbosity=2)
