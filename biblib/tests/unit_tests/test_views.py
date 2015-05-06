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
from views import UserView
from tests.stubdata.stub_data import StubDataLibrary


class TestUserViews(TestCase):
    """
    Base class to test the Library creation views
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
            self.user_view.create_library(
                service_uid=user.id,
                library_data=self.stub_library
            )

        # Get the library created
        libraries = self.user_view.get_libraries(self.stub_uid)

        self.assertEqual(len(libraries), number_of_libs)