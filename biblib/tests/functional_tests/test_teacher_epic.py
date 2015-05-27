"""
Functional test

Teacher Epic

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
from tests.stubdata.stub_data import StubDataLibrary, StubDataDocument,\
    StubDataUser
from tests.base import MockADSWSAPI


class TestDeletionEpic(TestCase):
    """
    Base class used to test the Teacher Epic
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

    def test_teacher(self):
        """
        Carries out the epic 'Teacher', where a user wants to remove the
        privileges of one person, but not affect anyone else

        :return: no return
        """

        # The teacher makes a library
        student_1 = StubDataUser().get_user()
        student_2 = StubDataUser().get_user()

        stub_library, uid_teacher = StubDataLibrary().make_stub()
        headers_teacher = {USER_ID_KEYWORD: uid_teacher}

        url = url_for('userview')
        response = self.client.post(
            url,
            data=json.dumps(stub_library),
            headers=headers_teacher
        )
        self.assertEqual(response.status_code, 200, response)
        library_id_teacher = response.json['id']

        # Some students complain that they cannot see the library that is
        # linked by the University web page
        # need a permissions endpoint
        # /permissions/<uuid_library>
        for uid in [student_1, student_2]:
            headers = {USER_ID_KEYWORD: uid}
            # The students check they can see the content
            url = url_for('libraryview', library=library_id_teacher)
            response = self.client.get(
                url,
                headers=headers
            )
            self.assertEqual(
                response.status_code,
                NO_PERMISSION_ERROR['number']
            )
            self.assertEqual(
                response.json['error'],
                NO_PERMISSION_ERROR['body']
            )

        # The teacher adds two users with read permissions
        email_student_1 = 'student_1@email.com'
        email_student_2 = 'student_2@email.com'
        data_permissions_student_1 = {
            'email': email_student_1,
            'permission': 'read',
            'value': True
        }
        data_permissions_student_2 = {
            'email': email_student_2,
            'permission': 'read',
            'value': True
        }

        # need a permissions endpoint
        # /permissions/<uuid_library>
        for data_permissions, uid in [[data_permissions_student_1, student_1],
                                      [data_permissions_student_2, student_2]]:

            # Permissions url
            url = url_for('permissionview', library=library_id_teacher)

            # This requires communication with the API
            test_endpoint = '{api}/{email}'.format(
                api=self.app.config['USER_EMAIL_ADSWS_API_URL'],
                email=data_permissions['email']
            )
            with MockADSWSAPI(test_endpoint, user_uid=uid):
                response = self.client.post(
                    url,
                    data=data_permissions,
                    headers=headers_teacher
                )
            self.assertEqual(response.status_code, 200)

            headers = {USER_ID_KEYWORD: uid}
            # The students check they can see the content
            url = url_for('libraryview', library=library_id_teacher)
            response = self.client.get(
                url,
                headers=headers
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn('documents', response.json)

        # The teacher realises student 2 is not in the class, and removes
        # the permissions, and makes sure student 1 can still see the content

        data_permissions = {
            'email': email_student_2,
            'permission': 'read',
            'value': False
        }
        url = url_for('permissionview', library=library_id_teacher)

        # Fake response from API
        test_endpoint = '{api}/{email}'.format(
            api=self.app.config['USER_EMAIL_ADSWS_API_URL'],
            email=data_permissions['email']
        )
        with MockADSWSAPI(test_endpoint, user_uid=student_2):
            response = self.client.post(
                url,
                data=data_permissions,
                headers=headers_teacher
            )

        self.assertEqual(response.status_code, 200)

        # Student 2 cannot see the content
        headers = {USER_ID_KEYWORD: student_2}
        url = url_for('libraryview', library=library_id_teacher)
        response = self.client.get(
            url,
            headers=headers
        )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

        # Student 1 can see the content still
        headers = {USER_ID_KEYWORD: student_1}
        url = url_for('libraryview', library=library_id_teacher)
        response = self.client.get(
            url,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('documents', response.json)

if __name__ == '__main__':
    unittest.main(verbosity=2)