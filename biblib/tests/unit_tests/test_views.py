"""
Tests Views of the application
"""

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Testing'
__license__ = 'MIT'

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import app
import unittest
from models import db, User, Library, Permissions
from flask.ext.testing import TestCase
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from views import UserView, LibraryView, DocumentView, PermissionView
from tests.stubdata.stub_data import StubDataLibrary, StubDataDocument
from utils import BackendIntegrityError, PermissionDeniedError


class TestUserViews(TestCase):
    """
    Base class to test the User & Library creation views
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """

        super(TestCase, self).__init__(*args, **kwargs)
        self.user_view = UserView()

    def create_app(self):
        """
        Create the wsgi application for the flask test extension

        :return: application instance
        """

        return app.create_app(config_type='TEST')

    def setUp(self):
        """
        Set up the database for use

        :return: no return
        """

        db.create_all()
        self.stub_library, self.stub_uid = StubDataLibrary().make_stub()

    def tearDown(self):
        """
        Remove/delete the database and the relevant connections

        :return: no return
        """

        db.session.remove()
        db.drop_all()

    def test_user_creation(self):
        """
        Creates a user and checks it exists within the database

        :return: no return
        """

        # Create a user using the function
        self.user_view.create_user(absolute_uid=self.stub_uid)
        # Create another use so that we know it returns a single record
        self.user_view.create_user(absolute_uid=self.stub_uid+1)

        # Check if it really exists in the database
        result = User.query.filter(User.absolute_uid == self.stub_uid).all()

        # Should contain one result
        self.assertTrue(len(result) == 1)

    def test_user_creation_raises_exception_if_exists(self):
        """
        Creating a user when the user already exists should raise an exception
        that should be handled gracefully in the main section of the code. The
        end point will handle the return to the user.
        :return:
        """

        # Add the user to the database with the uid we do not want repeated
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Now try to add a user with the same uid from the API, it should raise
        # an error
        with self.assertRaises(IntegrityError):
            self.user_view.create_user(absolute_uid=self.stub_uid)

    def test_user_creation_if_exists(self):
        """
        Check that it knows if a user already exists

        :return: no return
        """

        # Check if the user exists, given we have not added any user in this
        # test, it should return nothing.
        exists = self.user_view.helper_user_exists(absolute_uid=self.stub_uid)
        self.assertFalse(exists)

        # Add the user with the given UID to the database
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Check that the user exists in the database
        exists = self.user_view.helper_user_exists(absolute_uid=self.stub_uid)
        self.assertTrue(exists)

    def test_user_can_create_a_library(self):
        """
        Checks that a library is created and exists in the database

        :return:
        """

        # Make the user we want the library to be associated with
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Create the library for the user we created, with the library stub data
        self.user_view.create_library(
            service_uid=user.id,
            library_data=self.stub_library
        )

        # Check that the library was created with the correct permissions
        result = Permissions.query\
            .filter(User.id == Permissions.user_id)\
            .filter(Library.id == Permissions.library_id)\
            .all()

        self.assertTrue(len(result) == 1)

    def test_user_can_retrieve_library(self):
        """
        Test that we can obtain the libraries that correspond to a given user

        :return: no return
        """

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Make a library that ensures we get one back
        number_of_libs = 2
        for i in range(number_of_libs):

            stub_library, tmp = StubDataLibrary().make_stub()

            self.user_view.create_library(
                service_uid=user.id,
                library_data=stub_library
            )

        # Get the library created
        libraries = self.user_view.get_libraries(self.stub_uid)

        self.assertEqual(len(libraries), number_of_libs)

    def test_user_cannot_add_two_libraries_with_the_same_name(self):
        """
        Test that a user cannot add a new library with the same name

        :return: no return
        """

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Make the first library
        self.user_view.create_library(
            service_uid=user.id,
            library_data=self.stub_library
        )

        # Make the second library
        with self.assertRaises(BackendIntegrityError):
            self.user_view.create_library(
                service_uid=user.id,
                library_data=self.stub_library
            )


class TestLibraryViews(TestCase):
    """
    Base class to test the Library view for GET
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """

        super(TestCase, self).__init__(*args, **kwargs)
        self.user_view = UserView()
        self.library_view = LibraryView()

    def create_app(self):
        """
        Create the wsgi application for the flask test extension

        :return: application instance
        """

        return app.create_app(config_type='TEST')

    def setUp(self):
        """
        Set up the database for use

        :return: no return
        """

        db.create_all()
        self.stub_library, self.stub_uid = StubDataLibrary().make_stub()
        self.stub_document = StubDataDocument().make_stub()

    def tearDown(self):
        """
        Remove/delete the database and the relevant connections

        :return: no return
        """

        db.session.remove()
        db.drop_all()

    def test_user_can_get_documents_from_library(self):
        """
        Test that can retrieve all the bibcodes from a library

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=[self.stub_document['bibcode']])

        # Give the user and library permissions
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        # Retrieve the bibcodes using the web services
        bibcodes = self.library_view.get_documents_from_library(
            library_id=library.id
        )

    def test_user_without_permission_cannot_access_private_library(self):
        """
        Tests that the user requesting to see the contents of a library has
        the correct permissions. In this case, they do not, and are refused to
        see the library content.

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=[self.stub_document['bibcode']])

        # Give the user and library permissions
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        # Make sure the second user is denied access
        # add 1 to the UID to represent a random user
        access = self.library_view.read_access(service_uid=user.id+1,
                                               library_id=library.id)
        self.assertIsNotNone(access)
        self.assertFalse(access)


class TestDocumentViews(TestCase):
    """
    Base class to test the Document view for POST/DELETE (PUT for tags?)
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """

        super(TestCase, self).__init__(*args, **kwargs)
        self.document_view = DocumentView()

    def create_app(self):
        """
        Create the wsgi application for the flask test extension

        :return: application instance
        """

        return app.create_app(config_type='TEST')

    def setUp(self):
        """
        Set up the database for use

        :return: no return
        """

        db.create_all()
        self.stub_library, self.stub_uid = StubDataLibrary().make_stub()
        self.stub_document = StubDataDocument().make_stub()

    def tearDown(self):
        """
        Remove/delete the database and the relevant connections

        :return: no return
        """

        db.session.remove()
        db.drop_all()

    def test_user_can_delete_a_library(self):
        """
        Tests that the user can correctly remove a library from its account

        :return: no return
        """

        # Step 1. Make the user, library, and permissions

        # Ensure a user exists
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=[self.stub_document['bibcode']])

        # Give the user and library permissions
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        library = Library.query.filter(Library.id == library.id).one()
        self.assertIsInstance(library, Library)

        self.document_view.delete_library(library_id=library.id)

        with self.assertRaises(NoResultFound):
            Library.query.filter(Library.id == library.id).one()

    def test_user_can_add_to_library(self):
        """
        Tests that adding a bibcode to a library works correctly

        :return:
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True)

        # Give the user and library permissions
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        library_id = library.id
        user_id = user.id

        # Get stub data for the document

        # Add a document to the library
        self.document_view.add_document_to_library(
            library_id=library_id,
            document_data=self.stub_document
        )

        # Check that the document is in the library
        library = Library.query.filter(Library.id == library_id).all()
        for _lib in library:
            self.assertIn(self.stub_document['bibcode'], _lib.bibcode)

        self.stub_document['bibcode'] = self.stub_document['bibcode'] + 'NEW'
        # Add a different document to the library
        self.document_view.add_document_to_library(
            library_id=library_id,
            document_data=self.stub_document
        )

        # Check that the document is in the library
        library = Library.query.filter(Library.id == library_id).all()
        for _lib in library:
            self.assertIn(self.stub_document['bibcode'], _lib.bibcode)

    def test_user_can_remove_document_from_library(self):
        """
        Test that can remove a document from the library

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=[self.stub_document['bibcode']])

        # Give the user and library permissions
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        # Remove the bibcode from the library
        self.document_view.remove_documents_from_library(
            library_id=library.id,
            document_data=self.stub_document
        )

        # Check it worked
        library = Library.query.filter(Library.id == library.id).one()

        self.assertTrue(
            len(library.bibcode) == 0,
            'There should be no bibcodes: {0}'.format(library.bibcode)
        )

    def test_user_without_permission_cannot_edit_private_library(self):
        """
        Tests that the user requesting to edit the contents of a library has
        the correct permissions. In this case, they do not, and are refused to
        see the library content.

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=[self.stub_document['bibcode']])

        # Give the user and library permissions
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        # add 1 to the UID to represent a random user
        access = self.document_view.write_access(service_uid=user.id+1,
                                                 library_id=library.id)
        self.assertIsNotNone(access)
        self.assertFalse(access)


class TestPermissionViews(TestCase):
    """
    Base class to test the creation, modification, deletion of user
    permissions via the Permissions view.
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """

        super(TestCase, self).__init__(*args, **kwargs)
        self.permission_view = PermissionView()
        self.user_view = UserView()

    def create_app(self):
        """
        Create the wsgi application for the flask test extension

        :return: application instance
        """

        return app.create_app(config_type='TEST')

    def setUp(self):
        """
        Set up the database for use

        :return: no return
        """

        db.create_all()
        self.stub_library, self.stub_uid = StubDataLibrary().make_stub()
        self.stub_document = StubDataDocument().make_stub()

    def tearDown(self):
        """
        Remove/delete the database and the relevant connections

        :return: no return
        """

        db.session.remove()
        db.drop_all()

    def test_can_add_read_permission_to_user(self):
        """
        Tests the backend logic for adding read permissions to a user

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=[self.stub_document['bibcode']])

        db.session.add_all([user, library])
        db.session.commit()

        self.permission_view.add_permission(service_uid=user.id,
                                            library_id=library.id,
                                            permission='read',
                                            value=True)

        try:
            permission = Permissions.query.filter(
                Permissions.user_id == user.id,
                Permissions.library_id == library.id
            ).one()
        except Exception as error:
            self.fail('No permissions were created, most likely the code has '
                      'not been implemented. [{0}]'.format(error))

        self.assertTrue(permission.read)
        self.assertFalse(permission.write)
        self.assertFalse(permission.owner)

    def test_a_user_without_permissions_cannot_modify_permissions(self):
        """
        Tests that a user that does not have admin permissions, cannot modify
        the permissions of another user.

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user_1 = User(absolute_uid=self.stub_uid)
        user_2 = User(absolute_uid=self.stub_uid+1)

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=[self.stub_document['bibcode']])

        permission = Permissions()
        user_1.permissions.append(permission)
        library.permissions.append(permission)

        db.session.add_all([user_1, user_2, library])
        db.session.commit()

        result = self.permission_view.has_permission(
            service_uid_editor=user_2.id,
            service_uid_modify=user_1.id,
            library_id=library.id
        )

        self.assertFalse(result)

    def test_a_user_with_owner_permissions_can_edit_permissions(self):
        """
        Tests that the owner has the ability to edit permissions of users
        within their library.

        :return: no return
        """
        # Make a fake user and library
        # Ensure a user exists
        user_1 = User(absolute_uid=self.stub_uid)
        user_2 = User(absolute_uid=self.stub_uid+1)

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=[self.stub_document['bibcode']])

        permission = Permissions()
        permission.owner = True
        user_2.permissions.append(permission)
        library.permissions.append(permission)

        db.session.add_all([user_1, user_2, library])
        db.session.commit()

        result = self.permission_view.has_permission(
            service_uid_editor=user_2.id,
            service_uid_modify=user_1.id,
            library_id=library.id
        )

        self.assertTrue(result)

    def test_a_user_with_editing_permissions_can_edit_permissions(self):
        """
        Tests that a user that has been given admin privileges can edit other
        users in the library.

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user_1 = User(absolute_uid=self.stub_uid)
        user_2 = User(absolute_uid=self.stub_uid+1)

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=[self.stub_document['bibcode']])

        permission_1 = Permissions()
        permission_1.admin = True
        permission_2 = Permissions()
        permission_2.admin = True

        user_1.permissions.append(permission_1)
        library.permissions.append(permission_1)

        user_2.permissions.append(permission_2)
        library.permissions.append(permission_2)

        db.session.add_all([user_1, user_2, library])
        db.session.commit()

        result = self.permission_view.has_permission(
            service_uid_editor=user_2.id,
            service_uid_modify=user_1.id,
            library_id=library.id
        )

        self.assertTrue(result)

    def test_a_user_with_editing_permissions_cannot_edit_owner(self):
        """
        Tests that a user with admin permissions cannot manipulate any of the
        settings of the owners permissions.

        :return: no return
        """
        # Make a fake user and library
        # Ensure a user exists
        user_1 = User(absolute_uid=self.stub_uid)
        user_2 = User(absolute_uid=self.stub_uid+1)

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=[self.stub_document['bibcode']])

        permission_1 = Permissions()
        permission_1.owner = True
        permission_2 = Permissions()
        permission_2.admin = True

        user_1.permissions.append(permission_1)
        library.permissions.append(permission_1)

        user_2.permissions.append(permission_2)
        library.permissions.append(permission_2)

        db.session.add_all([user_1, user_2, library])
        db.session.commit()

        result = self.permission_view.has_permission(
            service_uid_editor=user_2.id,
            service_uid_modify=user_1.id,
            library_id=library.id
        )

        self.assertFalse(result)

    def test_a_user_with_permissions_cannot_edit_anyone(self):
        """
        Tests that a user with read permissions cannot do any permission
        changes to other users.

        :return: no return
        """
        # Make a fake user and library
        # Ensure a user exists
        user_admin = User(absolute_uid=self.stub_uid)
        user_read_only = User(absolute_uid=self.stub_uid+1)

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=[self.stub_document['bibcode']])

        permission_admin = Permissions()
        permission_admin.admin = True
        permission_read_only = Permissions()
        permission_read_only.read = True

        user_admin.permissions.append(permission_admin)
        library.permissions.append(permission_admin)

        user_read_only.permissions.append(permission_read_only)
        library.permissions.append(permission_read_only)

        db.session.add_all([user_admin, user_read_only, library])
        db.session.commit()

        result = self.permission_view.has_permission(
            service_uid_editor=user_read_only.id,
            service_uid_modify=user_admin.id,
            library_id=library.id
        )

        self.assertFalse(result)

    def test_owner_does_not_modify_owner(self):
        # Make a fake user and library
        # Ensure a user exists
        user_owner = User(absolute_uid=self.stub_uid)
        db.session.add(user_owner)
        db.session.commit()

        # Ensure a library exists
        library_data = dict(name='MyLibrary',
                            description='My library',
                            public=True,
                            read=False,
                            write=False,
                            bibcode=[self.stub_document['bibcode']])

        library = self.user_view.create_library(service_uid=user_owner.id,
                                                library_data=library_data)

        # Check our user has owner permissions
        permission = Permissions.query.filter(
            Permissions.library_id == library.id,
            Permissions.user_id == user_owner.id
        ).one()
        self.assertTrue(permission.owner)

        # Check that the owner cannot mess with the owner's permissions
        result = self.permission_view.has_permission(
            service_uid_editor=user_owner.id,
            service_uid_modify=user_owner.id,
            library_id=library.id
        )
        self.assertFalse(result)

    def test_admin_cannot_modify_owner_value(self):
        """
        Test to ensure that the user with owner privileges cannot modify the
        owner value of a library

        :return: no return
        """
        # Make a fake user and library
        # Ensure a user exists
        user_owner = User(absolute_uid=self.stub_uid)
        user_admin = User(absolute_uid=self.stub_uid+1)
        user_random = User(absolute_uid=self.stub_uid+2)

        db.session.add_all([user_owner, user_admin, user_random])
        db.session.commit()

        # Ensure a library exists
        library_data = dict(name='MyLibrary',
                            description='My library',
                            public=True,
                            read=False,
                            write=False,
                            bibcode=[self.stub_document['bibcode']])

        library = self.user_view.create_library(service_uid=user_owner.id,
                                                library_data=library_data)

        # Check our user has owner permissions
        permission = Permissions.query.filter(
            Permissions.library_id == library.id,
            Permissions.user_id == user_owner.id
        ).one()
        self.assertTrue(permission.owner)

        # Give the second user, admin permissions
        self.permission_view.add_permission(service_uid=user_admin.id,
                                            library_id=library.id,
                                            permission='admin',
                                            value=True)

        # Check our user has owner permissions
        permission = Permissions.query.filter(
            Permissions.library_id == library.id,
            Permissions.user_id == user_admin.id
        ).one()
        self.assertTrue(permission.admin)
        self.assertFalse(permission.owner)

        # Check that the admin cannot modify the owner status of random user
        with self.assertRaises(PermissionDeniedError):
            self.permission_view.add_permission(service_uid=user_random.id,
                                                library_id=library.id,
                                                permission='owner',
                                                value=True)

        # Check our user has owner permissions
        with self.assertRaises(NoResultFound):
            Permissions.query.filter(
                Permissions.library_id == library.id,
                Permissions.user_id == user_random.id
            ).one()

if __name__ == '__main__':
    unittest.main(verbosity=2)
