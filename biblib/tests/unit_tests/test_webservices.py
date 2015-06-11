"""
Test webservices
"""

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import json
import unittest
from flask import url_for
from views import DUPLICATE_LIBRARY_NAME_ERROR, MISSING_LIBRARY_ERROR, \
    MISSING_USERNAME_ERROR, NO_PERMISSION_ERROR, DEFAULT_LIBRARY_NAME_PREFIX, \
    DEFAULT_LIBRARY_DESCRIPTION, WRONG_TYPE_LIST_ERROR, \
    DUPLICATE_DOCUMENT_NAME_ERROR, API_MISSING_USER_EMAIL
from tests.stubdata.stub_data import LibraryShop, UserShop
from tests.base import MockEmailService, MockSolrBigqueryService,\
    TestCaseDatabase

class TestWebservices(TestCaseDatabase):
    """
    Tests that each route is an http response
    """

    def test_when_no_user_information_passed_to_user_post(self):
        """
        Test the /libraries route
        Tests that a KeyError is raised when the user ID is not passed

        :return: no return
        """

        url = url_for('userview')
        response = self.client.post(url)

        self.assertEqual(response.status_code,
                         MISSING_USERNAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         MISSING_USERNAME_ERROR['body'])

    def test_when_no_user_information_passed_to_user_get(self):
        """
        Test the /libraries route
        Tests that a KeyError is raised when the user ID is not passed

        :return: no return
        """

        url = url_for('userview')
        response = self.client.get(url)

        self.assertEqual(response.status_code,
                         MISSING_USERNAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         MISSING_USERNAME_ERROR['body'])

    def test_when_no_user_information_passed_to_library_post(self):
        """
        Test the /libraries/<library_uuid> route
        Tests that a KeyError is raised when the user ID is not passed

        :return: no return
        """

        url = url_for('documentview', library='test')
        response = self.client.post(url)

        self.assertEqual(response.status_code,
                         MISSING_USERNAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         MISSING_USERNAME_ERROR['body'])

    def test_when_no_user_information_passed_to_library_get(self):
        """
        Test the /libraries route
        Tests that a KeyError is raised when the user ID is not passed

        :return: no return
        """

        url = url_for('libraryview', library='test')
        with MockSolrBigqueryService():
            response = self.client.get(url)

        self.assertEqual(response.status_code,
                         MISSING_USERNAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         MISSING_USERNAME_ERROR['body'])

    def test_create_library_resource(self):
        """
        Test the /libraries route
        Creating the user and a library

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')

        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        self.assertNotIn('bibcode', response.json)

        # Check the library exists in the database
        url = url_for('userview')

        with MockEmailService(stub_user, end_type='uid'):
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)

        for library in response.json['libraries']:
            self.assertEqual(stub_library.name, library['name'])
            self.assertEqual(stub_library.description,
                             library['description'])

    def test_create_library_resource_response_content(self):
        """
        Test the /libraries GET end point
        Ensuring the response contains the data we expect. For now, this is
        defined within the stub data.

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)

        # Check the library exists in the database
        url = url_for('userview')
        with MockEmailService(stub_user, end_type='uid'):
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)

        for library in response.json['libraries']:
            for expected_type in stub_library.user_view_get_response():
                self.assertIn(expected_type, library.keys())

    def test_create_library_resource_and_add_bibcodes(self):
        """
        Test the /libraries route
        Creating the user and a library

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop(want_bibcode=True)

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)
        library_id = response.json['id']
        for key in ['name', 'id', 'bibcode', 'description']:
            self.assertIn(key, response.json)

        # Check the library exists in the database
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService():
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)

        for document in response.json['documents']:
            self.assertIn(document, stub_library.bibcode)

    def test_get_solr_data_for_documents(self):
        """
        Test the /libraries/<> route to check that solr data is returned by
        the service

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop(want_bibcode=True)

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)
        library_id = response.json['id']
        for key in ['name', 'id', 'bibcode', 'description']:
            self.assertIn(key, response.json)

        # Check the library exists in the database
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService():
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('documents', response.json)
        self.assertIn('solr', response.json)

    def test_create_library_resource_and_add_bibcodes_of_wrong_type(self):
        """
        Test the /libraries route
        Creating the user and a library

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        library_data = stub_library.user_view_post_data
        for bib_type in ['string', int(3), float(3.0), dict(test='test')]:

            library_data['bibcode'] = bib_type

            # Make the library
            url = url_for('userview')
            response = self.client.post(
                url,
                data=json.dumps(library_data),
                headers=stub_user.headers
            )
            self.assertEqual(response.status_code,
                             WRONG_TYPE_LIST_ERROR['number'])
            self.assertEqual(response.json['error'],
                             WRONG_TYPE_LIST_ERROR['body'])

    def test_add_document_to_library(self):
        """
        Test the /documents/<> end point with POST to add a document

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        url = url_for('documentview', library=library_id)
        self.client.post(
            url,
            data=stub_library.document_view_post_data_json('add'),
            headers=stub_user.headers
        )

        # Check the library was created and documents exist
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService():
            response = self.client.get(
                url,
                headers=stub_user.headers
            )

        self.assertEqual(response.status_code, 200, response)
        self.assertEqual(stub_library.bibcode, response.json['documents'])

    def test_cannot_add_duplicate_documents_to_library(self):
        """
        Test the /documents/<> end point with POST to add a document. Should
        not be able to add the same document more than once.

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        url = url_for('documentview', library=library_id)
        response = self.client.post(
            url,
            data=stub_library.document_view_post_data_json('add'),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)

        # Should not be able to add the same document
        url = url_for('documentview', library=library_id)
        response = self.client.post(
            url,
            data=stub_library.document_view_post_data_json('add'),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code,
                         DUPLICATE_DOCUMENT_NAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         DUPLICATE_DOCUMENT_NAME_ERROR['body'])

    def test_remove_document_from_library(self):
        """
        Test the /libraries/<> end point with POST to remove a document

        :return:
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        url = url_for('documentview', library=library_id)
        response = self.client.post(
            url,
            data=stub_library.document_view_post_data_json('add'),
            headers=stub_user.headers
        )
        self.assertTrue(response.status, 200)

        # Delete the document
        url = url_for('documentview', library=library_id)
        response = self.client.post(
            url,
            data=stub_library.document_view_post_data_json('remove'),
            headers=stub_user.headers
        )
        self.assertTrue(response.status, 200)

        # Check the library is empty
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService():
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertTrue(len(response.json['documents']) == 0,
                        response.json['documents'])

    def test_cannot_add_library_with_duplicate_names(self):
        """
        Test the /liraries end point with POST to ensure two libraries cannot
        have the same name

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make first library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)

        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Make another one with the same name
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code,
                         DUPLICATE_LIBRARY_NAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         DUPLICATE_LIBRARY_NAME_ERROR['body'])

    def test_can_remove_a_library(self):
        """
        Tests the /documents/<> end point with DELETE to remove a
        library from a user's libraries

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make first library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Delete the library
        url = url_for('documentview',
                      user=stub_user.absolute_uid,
                      library=library_id)
        response = self.client.delete(
            url,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)

        # Check its deleted
        url = url_for('userview')
        with MockEmailService(stub_user, end_type='uid'):
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertTrue(len(response.json['libraries']) == 0,
                        response.json)

        # Check there is no document content
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService():
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code,
                         MISSING_LIBRARY_ERROR['number'],
                         'Received response error: {0}'
                         .format(response.status_code))
        self.assertEqual(response.json['error'],
                         MISSING_LIBRARY_ERROR['body'])

        # Try to delete even though it does not exist, this should return
        # some errors from the server
        url = url_for('documentview', library=library_id)

        response = self.client.delete(
            url,
            headers=stub_user.headers
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

        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_library = LibraryShop()

        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers,
        )
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Request from user 2 to see the library should be refused if user 2
        # does not have the permissions
        # Check the library is empty
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService():
            response = self.client.get(
                url,
                headers=stub_user_2.headers
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

    def test_can_add_read_permissions(self):
        """
        Tests that a user can add read permissions to another user for one of
        their libraries.

        :return: no return
        """

        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_library = LibraryShop()

        # Initialise HTTPretty for the URL for the API
        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers
        )
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Make a library for user 2 so that we have an account
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_2.headers
        )
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Add the permissions for user 2
        url = url_for('permissionview', library=library_id)

        # This requires communication with the API
        with MockEmailService(stub_user_2):
            response = self.client.post(
                url,
                data=stub_user_2.permission_view_post_data_json('read', True),
                headers=stub_user_1.headers
            )
        self.assertEqual(response.status_code, 200)

        # The user can now access the content of the library
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService():
            response = self.client.get(
                url,
                headers=stub_user_2.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue('documents' in response.json)

    def test_cannot_change_permission_without_permission(self):
        """
        Test that a user without permissions cannot alter the permissions
        of a library.
        :return:
        """

        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_library = LibraryShop()

        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers
        )
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Make a library for user 2 so that we have an account
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_2.headers
        )
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # User 2 with no permissions tries to modify user 1
        url = url_for('permissionview', library=library_id)
        # This requires communication with the API
        # User requesting: user 2 that has no permissions
        # To modify: user 2 is trying to modify user 1, which is the owner of
        # the library
        # E-mail requested should correspond to the owner of the library,
        # which in this case is user 1
        with MockEmailService(stub_user_1):
            response = self.client.post(
                url,
                data=stub_user_1.permission_view_post_data_json('read', True),
                headers=stub_user_2.headers
            )

        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

    def test_owner_cannot_edit_owner(self):
        """
        Test that the owner of a library cannot modify their own permissions,
        such as read, write, etc., otherwise it would allow orphan libraries

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Owner tries to modify owner permissions
        url = url_for('permissionview', library=library_id)
        for permission_type in ['read', 'write', 'admin', 'owner']:
            # E-mail requested should correspond to user
            with MockEmailService(stub_user):
                response = self.client.post(
                    url,
                    data=stub_user.permission_view_post_data_json(
                        permission_type, False
                    ),
                    headers=stub_user.headers
                )

            self.assertEqual(response.status_code,
                             NO_PERMISSION_ERROR['number'])
            self.assertEqual(response.json['error'],
                             NO_PERMISSION_ERROR['body'])

    def test_admin_cannot_edit_any_owner_permission(self):
        """
        Test that an admin cannot edit the owner value of a library.

        :return: no return
        """

        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_user_3 = UserShop()
        stub_library = LibraryShop()

        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Give user 2 admin permissions
        # This requires communication with the API
        # User requesting: user 1 owner of the library
        # To modify: user 1 is trying to modify user 2
        # E-mail requested should correspond to user 2
        url = url_for('permissionview', library=library_id)
        with MockEmailService(stub_user_2):
            response = self.client.post(
                url,
                data=stub_user_2.permission_view_post_data_json('admin', True),
                headers=stub_user_1.headers
            )
        self.assertEqual(response.status_code, 200)

        # Now user 2 tries to give user 3 owner permissions. Even though user 2
        # has admin permissions, they should not be able to modify the owner.
        # E-mail requested should correspond to user 3
        url = url_for('permissionview', library=library_id)
        with MockEmailService(stub_user_3):
            response = self.client.post(
                url,
                data=stub_user_3.permission_view_post_data_json('owner', True),
                headers=stub_user_2.headers
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

    def test_give_permissions_to_a_user_not_in_the_service_database(self):
        """
        This tests that a user that exists in the API but not the service
        database, can have permissions changed.

        :return: no return
        """

        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_library = LibraryShop()

        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Add the permissions for user 2
        url = url_for('permissionview', library=library_id)
        for permission_type in ['read', 'write', 'admin']:
            with MockEmailService(stub_user_2):
                response = self.client.post(
                    url,
                    data=stub_user_2.permission_view_post_data_json(
                        permission_type,
                        True
                    ),
                    headers=stub_user_1.headers
                )
            self.assertEqual(response.status_code, 200)

    def test_user_cannot_edit_library_without_permission(self):
        """
        Tests that only a user with correct edit permissions can edit the
        content of a library.

        :return:
        """

        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_library = LibraryShop()

        # Make a library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers
        )
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # See if a random user can edit content of the library
        # Add to the library
        url = url_for('documentview', library=library_id)
        response = self.client.post(
            url,
            data=stub_library.document_view_post_data_json('add'),
            headers=stub_user_2.headers
        )
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])

        # Check the owner can add/remove content
        response = self.client.post(
            url,
            data=stub_library.document_view_post_data_json('add'),
            headers=stub_user_1.headers
        )
        self.assertEqual(response.status_code, 200)

    def test_anonymous_users_can_access_public_libraries(self):
        """
        Tests that a user with no ties to the ADS can view libraries that
        are public

        :return: no return
        """
        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_library = LibraryShop(public=True)

        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers
        )
        self.assertEqual(response.status_code, 200)

        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Request from user 2
        # Given it is public, should be able to view it
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService():
            response = self.client.get(
                url,
                headers=stub_user_2.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('documents', response.json)

    def test_cannot_delete_a_library_if_not_owner(self):
        """
        Tests the /documents/<> end point with DELETE to remove a
        library from a user's libraries

        :return: no return
        """

        # Load stub data
        stub_owner = UserShop(name='owner')
        stub_none = UserShop(name='none')
        stub_reader = UserShop(name='reader')
        stub_editor = UserShop(name='editor')
        stub_admin = UserShop(name='admin')
        stub_library = LibraryShop(public=False)

        # Makes the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_owner.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200, response)
        self.assertTrue('name' in response.json)
        self.assertTrue(response.json['name'] == stub_library.name)

        # Give the correct permissions to each user
        url = url_for('permissionview', library=library_id)
        for stub_user, permission in [[stub_reader, 'read'],
                                      [stub_editor, 'write'],
                                      [stub_admin, 'admin']]:
            with MockEmailService(stub_user):
                response = self.client.post(
                    url,
                    data=stub_user.permission_view_post_data_json(
                        permission, True
                    ),
                    headers=stub_owner.headers
                )
            self.assertEqual(response.status_code, 200)

        # The following users try to the delete the library, and fail:
        # reader, editor, admin
        url = url_for('documentview', library=library_id)
        for stub_user in [stub_none, stub_reader, stub_editor, stub_admin]:
            response = self.client.delete(
                url,
                headers=stub_user.headers
            )
            self.assertEqual(response.status_code,
                             NO_PERMISSION_ERROR['number'],
                             'User: {0}'.format(stub_user.name))
            self.assertEqual(response.json['error'],
                             NO_PERMISSION_ERROR['body'])

    def test_when_no_post_content_or_empty_when_creating_library(self):
        """
        Tests that when a user posts no content or empty name and description
        for creating a library, that the wanted behaviour happens.

        :return: no return
        """

        # Stub data
        user_mary = UserShop()
        stub_library = LibraryShop(name='', description='')

        # Mary creates a private library and
        # Does not fill any of the details requested, and then looks at the
        # newly created library.
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_mary.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual('{0} 1'.format(DEFAULT_LIBRARY_NAME_PREFIX),
                         response.json['name'])
        self.assertEqual(DEFAULT_LIBRARY_DESCRIPTION,
                         response.json['description'])

        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_mary.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual('{0} 2'.format(DEFAULT_LIBRARY_NAME_PREFIX),
                         response.json['name'])
        self.assertEqual(DEFAULT_LIBRARY_DESCRIPTION,
                         response.json['description'])

    def test_can_update_name_and_description_with_permissions(self):
        """
        Tests that when a user posts no content or empty name and description
        for creating a library, that the wanted behaviour happens.

        :return: no return
        """

        # Stub data
        user_mary = UserShop()
        stub_library = LibraryShop(name='', description='', public=False)

        # Mary creates a private library and
        # Does not fill any of the details requested, and then looks at the
        # newly created library.
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_mary.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200)
        self.assertEqual('{0} 1'.format(DEFAULT_LIBRARY_NAME_PREFIX),
                         response.json['name'])
        self.assertEqual(DEFAULT_LIBRARY_DESCRIPTION,
                         response.json['description'])

        # Change the library name
        new_name = 'New name'
        new_description = 'New description'
        new_publicity = True

        library_data = \
            stub_library.document_view_put_data(name=new_name)
        library_data.pop('description')
        library_data.pop('public')
        library_data = json.dumps(library_data)

        url = url_for('documentview', library=library_id)
        response = self.client.put(
            url,
            data=library_data,
            headers=user_mary.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name,
                         response.json['name'],
                         response.json)

        # Change the library description
        library_data = \
            stub_library.document_view_put_data(description=new_description)
        library_data.pop('name')
        library_data.pop('public')
        library_data = json.dumps(library_data)

        response = self.client.put(
            url,
            data=library_data,
            headers=user_mary.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_description,
                         response.json['description'])

        # Change the publicity
        library_data = \
            stub_library.document_view_put_data(public=new_publicity)
        library_data.pop('name')
        library_data.pop('description')
        library_data = json.dumps(library_data)

        url = url_for('documentview', library=library_id)
        response = self.client.put(
            url,
            data=library_data,
            headers=user_mary.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_publicity,
                         response.json['public'])

        # Update both at the same time
        new_name += ' new'
        new_description += ' description'
        new_publicity = False
        response = self.client.put(
            url,
            data=stub_library.document_view_put_data_json(
                name=new_name,
                description=new_description,
                public=new_publicity
            ),
            headers=user_mary.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name,
                         response.json['name'])
        self.assertEqual(new_description,
                         response.json['description'])
        self.assertEqual(new_publicity,
                         response.json['public'])

    def test_can_update_library_with_permissions_admin(self):
        """
        Tests that when a user updates the name it is possible when the user
        has admin permissions.

        :return: no return
        """

        # Stub data
        user_mary = UserShop()
        user_admin = UserShop()
        stub_library = LibraryShop(name='', description='')

        # Mary creates a private library and
        # Does not fill any of the details requested, and then looks at the
        # newly created library.
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_mary.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200)
        self.assertEqual('{0} 1'.format(DEFAULT_LIBRARY_NAME_PREFIX),
                         response.json['name'])
        self.assertEqual(DEFAULT_LIBRARY_DESCRIPTION,
                         response.json['description'])

        # Allocate admin permissions
        url = url_for('permissionview', library=library_id)
        with MockEmailService(user_admin):
            response = self.client.post(
                url,
                data=user_admin.permission_view_post_data_json('admin', True),
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, 200)

        # Change the library name
        new_name = 'New name'
        new_description = 'New description'
        new_publicity = True

        url = url_for('documentview', library=library_id)
        response = self.client.put(
            url,
            data=stub_library.document_view_put_data_json(
                name=new_name,
                description=new_description
            ),
            headers=user_admin.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name,
                         response.json['name'])
        self.assertEqual(new_description,
                         response.json['description'])

    def test_cannot_update_name_with_name_that_exists(self):
        """
        Should not be able to update the library with a name that already
        exists for one of the users own libraries.

        :return: no return
        """

        # Stub data
        same_name = 'Same name'
        user_mary = UserShop()
        stub_library = LibraryShop(name=same_name, description='')

        # Mary creates a private library and
        # Does not fill any of the details requested, and then looks at the
        # newly created library.
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_mary.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(same_name,
                         response.json['name'])
        self.assertEqual(DEFAULT_LIBRARY_DESCRIPTION,
                         response.json['description'])

        # Try to update the name with the same name
        url = url_for('documentview', library=library_id)
        response = self.client.put(
            url,
            data=stub_library.document_view_put_data_json(name=same_name),
            headers=user_mary.headers
        )

        self.assertEqual(response.status_code,
                         DUPLICATE_LIBRARY_NAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         DUPLICATE_LIBRARY_NAME_ERROR['body'])

    def test_return_error_when_user_email_not_exist_api(self):
        """
        When the user does not exist the API database, the web service should
        pass on the message

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_random = UserShop(name='fail')
        stub_library = LibraryShop(name='', description='')

        # Fake library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200)

        # Allocate permissions
        url = url_for('permissionview', library=library_id)
        with MockEmailService(stub_random):
            response = self.client.post(
                url,
                data=stub_random.permission_view_post_data_json('read',
                                                              True),
                headers=stub_user.headers
            )

        self.assertEqual(response.status_code,
                         API_MISSING_USER_EMAIL['number'])
        self.assertEqual(response.json['error'],
                         API_MISSING_USER_EMAIL['body'])

    def test_return_error_when_user_uid_not_exist_api(self):
        """
        When the user does not exist in the API database, the web service
        should pass on the message.

        :return: no return
        """

        # Stub data
        stub_user = UserShop(name='fail')
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')

        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)

        # Check the library exists in the database
        url = url_for('userview')

        with MockEmailService(stub_user, end_type='uid'):
            response = self.client.get(
                url,
                headers=stub_user.headers
            )

        self.assertTrue(
            response.json['libraries'][0]['owner'] == 'Not available'
        )

    def test_cannot_update_name_and_description_without_permissions(self):
        """
        Tests that users who have read, write, or no permissions, can not
        update a library they can see.

        :return: no return
        """

        # Stub data
        user_mary = UserShop()
        user_random = UserShop()
        user_reader = UserShop()
        user_write = UserShop()
        stub_library = LibraryShop(name='', description='')

        # Mary creates a private library and
        # Does not fill any of the details requested, and then looks at the
        # newly created library.
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_mary.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200)
        self.assertEqual('{0} 1'.format(DEFAULT_LIBRARY_NAME_PREFIX),
                         response.json['name'])
        self.assertEqual(DEFAULT_LIBRARY_DESCRIPTION,
                         response.json['description'])

        # Allocate permissions
        url = url_for('permissionview', library=library_id)
        for user, permission in [[user_reader, 'read'], [user_write, 'write']]:
            with MockEmailService(user):
                response = self.client.post(
                    url,
                    data=user.permission_view_post_data_json(permission, True),
                    headers=user_mary.headers
                )
            self.assertEqual(response.status_code, 200)

        # Change the library name
        for user in [user_random, user_reader, user_write]:
            url = url_for('documentview', library=library_id)
            new_name = 'New name'
            response = self.client.put(
                url,
                data=stub_library.document_view_put_data_json('name',
                                                              new_name),
                headers=user.headers
            )
            self.assertEqual(response.status_code,
                             NO_PERMISSION_ERROR['number'])
            self.assertEqual(response.json['error'],
                             NO_PERMISSION_ERROR['body'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
