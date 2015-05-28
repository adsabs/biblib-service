"""
Functional test

Big Share Admin Epic

Storyboard is defined within the comments of the program itself
"""

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


class TestDeletionEpic(TestCase):
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

    def test_job_big_share_admin(self):
        """
        Carries out the epic 'Big Share Admin', where a user creates a library
        and wants one other user to have admin permissions, i.e., add and
        remove users permissions (except the owners) from the library.

        :return: no return
        """

        # Generate some stub data for Mary and the student
        uid_mary = StubDataUser().get_user()
        headers_mary = {USER_ID_KEYWORD: uid_mary}
        email_mary = "mary@email.com"

        uid_student = StubDataUser().get_user()
        headers_student = {USER_ID_KEYWORD: uid_student}
        email_student = "student@email.com"

        # Librarian Dave makes a big library full of bibcodes
        #  1. Lets say 20 bibcodes
        # Dave makes his library
        library_dave, uid_dave = StubDataLibrary().make_stub()
        headers_dave = {USER_ID_KEYWORD: uid_dave}
        email_dave = "dave@email.com"
        url = url_for('userview')

        response = self.client.post(
            url,
            data=json.dumps(library_dave),
            headers=headers_dave
        )

        self.assertEqual(response.status_code, 200, response)
        library_id_dave = response.json['id']

        # Dave adds content to his library
        libraries_added = []
        number_of_documents = 20
        for i in range(number_of_documents):
            # Add document
            url = url_for('documentview', library=library_id_dave)
            stub_document = StubDataDocument().make_stub(action='add')

            libraries_added.append(stub_document['bibcode'])

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

        # Dave does not want to manage who can change content. He wants Mary to
        # adminstrate the library. Mary tries, but gets errors.
        data_permissions = {
            'email': email_student,
            'permission': 'write',
            'value': True
        }

        # need a permissions endpoint
        # /permissions/<uuid_library>
        url = url_for('permissionview', library=library_id_dave)

        # This requires communication with the API
        test_endpoint = '{api}/{email}'.format(
            api=self.app.config['USER_EMAIL_ADSWS_API_URL'],
            email=data_permissions['email']
        )
        with MockADSWSAPI(test_endpoint, user_uid=uid_student):
            response = self.client.post(
                url,
                data=data_permissions,
                headers=headers_mary
            )

        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

        # Dave now adds her account to permissions. She already has an ADS
        # account, and so Dave adds her with her e-mail address with read and
        # write permissions (but not admin).
        data_permissions = {
            'email': email_mary,
            'permission': 'admin',
            'value': True
        }

        # need a permissions endpoint
        # /permissions/<uuid_library>
        url = url_for('permissionview', library=library_id_dave)

        # This requires communication with the API
        test_endpoint = '{api}/{email}'.format(
            api=self.app.config['USER_EMAIL_ADSWS_API_URL'],
            email=data_permissions['email']
        )
        with MockADSWSAPI(test_endpoint, user_uid=uid_mary):
            response = self.client.post(
                url,
                data=data_permissions,
                headers=headers_dave
            )
        self.assertEqual(response.status_code, 200)

        # Mary then adds the student as an admin
        data_permissions = {
            'email': email_student,
            'permission': 'write',
            'value': True
        }

        # need a permissions endpoint
        # /permissions/<uuid_library>
        url = url_for('permissionview', library=library_id_dave)

        # This requires communication with the API
        test_endpoint = '{api}/{email}'.format(
            api=self.app.config['USER_EMAIL_ADSWS_API_URL'],
            email=data_permissions['email']
        )
        with MockADSWSAPI(test_endpoint, user_uid=uid_student):
            response = self.client.post(
                url,
                data=data_permissions,
                headers=headers_mary
            )
        self.assertEqual(response.status_code, 200)

        # The student removes a few bibcodes and keeps a list of the ones she
        # removed just in case
        url = url_for('documentview', library=library_id_dave)

        libraries_removed = []
        for i in range(number_of_documents/2):
            # Remove documents

            document = {
                'bibcode': libraries_added[i],
                'action': 'remove'
            }
            libraries_removed.append(libraries_added[i])
            libraries_added.remove(libraries_added[i])

            response = self.client.post(
                url,
                data=json.dumps(document),
                headers=headers_student
            )

            self.assertEqual(response.status_code, 200, response)

        # She checks that they got removed
        url = url_for('libraryview', library=library_id_dave)
        response = self.client.get(
            url,
            headers=headers_student
        )
        self.assertTrue(
            len(response.json['documents']) == number_of_documents/2
        )

        # Dave asks Mary to re-add the ones she removed because they were
        # actually useful
        url = url_for('documentview', library=library_id_dave)
        for bibcode in libraries_removed:
            # Add documents

            document = {
                'bibcode': bibcode,
                'action': 'add'
            }
            libraries_added.append(bibcode)

            response = self.client.post(
                url,
                data=json.dumps(document),
                headers=headers_mary
            )

            self.assertEqual(response.status_code, 200, response)

        # She checks that they got added
        url = url_for('libraryview', library=library_id_dave)
        response = self.client.get(
            url,
            headers=headers_student
        )
        self.assertTrue(
            len(response.json['documents']) == number_of_documents
        )

        # Sanity check 1
        # --------------
        # Remove the permissions of the student, they should not be able to do
        # what they could before
        # --------------
        # Mary removes the students permissions and the student tries to modify
        #  the library content, but cannot

        data_permissions = {
            'email': email_student,
            'permission': 'write',
            'value': False
        }

        # need a permissions endpoint
        # /permissions/<uuid_library>
        url = url_for('permissionview', library=library_id_dave)

        # This requires communication with the API
        test_endpoint = '{api}/{email}'.format(
            api=self.app.config['USER_EMAIL_ADSWS_API_URL'],
            email=data_permissions['email']
        )
        with MockADSWSAPI(test_endpoint, user_uid=uid_student):
            response = self.client.post(
                url,
                data=data_permissions,
                headers=headers_mary
            )
        self.assertEqual(response.status_code, 200)

        # The student tries to add content
        url = url_for('documentview', library=library_id_dave)
        stub_document['bibcode'] = 'failure'
        response = self.client.post(
            url,
            data=json.dumps(stub_document),
            headers=headers_student
        )

        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

        # Sanity check 2
        # --------------
        # Check that you cannot modify owner permissions
        # --------------
        # Mary tries to give the student owner permissions
        url = url_for('permissionview', library=library_id_dave)
        data_permissions = {
            'email': email_student,
            'permission': 'owner',
            'value': True
        }
        # This requires communication with the API
        test_endpoint = '{api}/{email}'.format(
            api=self.app.config['USER_EMAIL_ADSWS_API_URL'],
            email=data_permissions['email']
        )
        with MockADSWSAPI(test_endpoint, user_uid=uid_student):
            response = self.client.post(
                url,
                data=data_permissions,
                headers=headers_mary
            )

        self.assertEqual(response.status_code,
                         NO_PERMISSION_ERROR['number'],
                         response.json)
        self.assertEqual(response.json['error'],
                         NO_PERMISSION_ERROR['body'],
                         response.json)

        # Sanity check 3
        # --------------
        # Mary tries to manipulate Daves permissions
        # --------------
        # Mary attempts to change the read, admin, write, owner, permissions
        # of Dave, but should fail
        url = url_for('permissionview', library=library_id_dave)
        for permission_type in ['read', 'write', 'admin', 'owner']:
            data_permissions = {
                'email': email_dave,
                'permission': permission_type,
                'value': False
            }
            # This requires communication with the API
            test_endpoint = '{api}/{email}'.format(
                api=self.app.config['USER_EMAIL_ADSWS_API_URL'],
                email=data_permissions['email']
            )
            with MockADSWSAPI(test_endpoint, user_uid=uid_dave):
                response = self.client.post(
                    url,
                    data=data_permissions,
                    headers=headers_mary
                )
            self.assertEqual(response.status_code,
                             NO_PERMISSION_ERROR['number'])
            self.assertEqual(response.json['error'],
                             NO_PERMISSION_ERROR['body'])

        # Sanity check 4
        # --------------
        # Remove Mary's permissions so she cannot do what she was doing before
        # --------------
        # Dave removes Mary's permissions.

        data_permissions = {
            'email': email_mary,
            'permission': 'admin',
            'value': False
        }

        # need a permissions endpoint
        # /permissions/<uuid_library>
        url = url_for('permissionview', library=library_id_dave)

        # This requires communication with the API
        test_endpoint = '{api}/{email}'.format(
            api=self.app.config['USER_EMAIL_ADSWS_API_URL'],
            email=data_permissions['email']
        )
        with MockADSWSAPI(test_endpoint, user_uid=uid_mary):
            response = self.client.post(
                url,
                data=data_permissions,
                headers=headers_dave
            )
        self.assertEqual(response.status_code, 200)

        # Mary tries to change permissions for the student again
        data_permissions = {
            'email': email_student,
            'permission': 'write',
            'value': True
        }
        # This requires communication with the API
        test_endpoint = '{api}/{email}'.format(
            api=self.app.config['USER_EMAIL_ADSWS_API_URL'],
            email=data_permissions['email']
        )
        with MockADSWSAPI(test_endpoint, user_uid=uid_mary):
            response = self.client.post(
                url,
                data=data_permissions,
                headers=headers_mary
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])


if __name__ == '__main__':
    unittest.main(verbosity=2)