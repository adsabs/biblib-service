"""
Functional test

Deletion Epic

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
from tests.stubdata.stub_data import StubDataLibrary, StubDataDocument


class TestDeletionEpic(TestCase):
    """
    Base class used to test the Big Share Epic
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

    def test_job_big_share(self):
        """
        Carries out the epic 'Big Share', where a user wants to share one of
        their big libraries they have created

        :return: no return
        """

        # Librarian Dave makes a big library full of bibcodes
        #  1. Lets say 20 bibcodes

        # We make a library just to get a user account for mary
        stub_library, uid_mary = StubDataLibrary().make_stub()
        headers_mary = {USER_ID_KEYWORD: uid_mary}

        url = url_for('userview')
        response = self.client.post(
            url,
            data=json.dumps(stub_library),
            headers=headers_mary
        )
        self.assertEqual(response.status_code, 200, response)
        library_id_mary = response.json['id']

        # Dave makes his library
        library_dave, uid_dave = StubDataLibrary().make_stub()
        headers_dave = {USER_ID_KEYWORD: uid_dave}
        url = url_for('userview')

        response = self.client.post(
            url,
            data=json.dumps(stub_library),
            headers=headers_dave
        )

        self.assertEqual(response.status_code, 200, response)
        library_id_dave = response.json['id']

        # Let us just double check that their ids do not match
        self.assertNotEqual(library_id_mary, library_id_dave)

        # Dave adds content to his library
        number_of_documents = 20
        for i in range(number_of_documents):
            # Add document
            url = url_for('libraryview', library=library_id_dave)
            stub_document = StubDataDocument().make_stub(action='add')

            response = self.client.post(
                url,
                data=json.dumps(stub_document),
                headers=headers_dave
            )

            self.assertEqual(response.status_code, 200, response)

        url = url_for('libraryview', library=library_id_dave)
        response = self.client.get(
            url,
            headers=headers_dave
        )
        self.assertTrue(len(response.json['documents']) == number_of_documents)

        # Dave has made his library private, and his library friend Mary says
        # she cannot access the library.
        # Dave selects her e-mail address
        url = url_for('libraryview', library=library_id_dave)
        response = self.client.get(
            url,
            headers=headers_mary
        )

        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertNotIn('documents', response.json.keys())
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

        # Ask API for the user_id, if it does not exist, we send an e-mail?

        # Dave then gives Mary the permissions to read his library
        headers = {'user': uid_dave}
        email_mary = 'mary@email.com'
        permission_data = {
            'user': email_mary,
            'permission': ['viewer'],
            'action': 'add'
        }

        # need a permissions endpoint
        # /permissions/<uuid_library>
        url = url_for('permissionview', library=library_id_dave, method='post')
        headers = {'user': uid_dave}
        response = self.client.post(
            url,
            data=permission_data,
            headers=headers
        )

        self.assertEqual(response.status_code, 200)

        # Mary writes back to say she can see his libraries and is happy but
        # wants to add content herself
        url = url_for('libraryview', library=library_id_dave)
        response = self.client.get(
            url,
            headers=headers_mary
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json['documents']) == number_of_documents)

        # Mary accidentally tries to delete the permissions of Dave, but nothing
        # happens

        # Dave is unhappy with Mary's changes, so he removes her permissions
        # to write

        # Mary realises she can no longer add content

        # Dave then removes her ability to read anything

        # Mary realises she can no longer read content

if __name__ == '__main__':
    unittest.main(verbosity=2)