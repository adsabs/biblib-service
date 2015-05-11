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
from models import db, User, Library, Permissions
from flask.ext.testing import TestCase
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from views import UserView, LibraryView
from tests.stubdata.stub_data import StubDataLibrary, StubDataDocument


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
        exists = self.user_view.user_exists(absolute_uid=self.stub_uid)
        self.assertFalse(exists)

        # Add the user with the given UID to the database
        user = User(absolute_uid=self.stub_uid)
        db.session.add(user)
        db.session.commit()

        # Check that the user exists in the database
        exists = self.user_view.user_exists(absolute_uid=self.stub_uid)
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
        with self.assertRaises(IntegrityError):
            self.user_view.create_library(
                service_uid=user.id,
                library_data=self.stub_library
            )


class TestLibraryViews(TestCase):
    """
    Base class to test the Library view for GET/POST/DELETE (PUT for tags?)
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
        self.library_view.add_document_to_library(
            library_id=library_id,
            document_data=self.stub_document
        )

        # Check that the document is in the library
        library = Library.query.filter(Library.id == library_id).all()
        for _lib in library:
            self.assertIn(self.stub_document['bibcode'], _lib.bibcode)

        self.stub_document['bibcode'] = self.stub_document['bibcode'] + 'NEW'
        # Add a different document to the library
        self.library_view.add_document_to_library(
            library_id=library_id,
            document_data=self.stub_document
        )

        # Check that the document is in the library
        library = Library.query.filter(Library.id == library_id).all()
        for _lib in library:
            self.assertIn(self.stub_document['bibcode'], _lib.bibcode)

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
        self.library_view.remove_documents_from_library(
            library_id=library.id,
            document_data=self.stub_document
        )

        # Check it worked
        library = Library.query.filter(Library.id == library.id).one()

        self.assertTrue(
            len(library.bibcode) == 0,
            'There should be no bibcodes: {0}'.format(library.bibcode)
        )

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

        self.library_view.delete_library(library_id=library.id)

        with self.assertRaises(NoResultFound):
            library = Library.query.filter(Library.id == library.id).one()