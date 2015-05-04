"""
Tests SQLAlchemy models
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
from models import db, User
from flask.ext.testing import TestCase

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

from views import CreateLibrary


class SQLAlchemyFlaskTestCase(TestCase):
    """
    Base class to test the database models for the web service
    """
    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """
        super(TestCase, self).__init__(*args, **kwargs)
        self.create_library = CreateLibrary()

    def create_app(self):
        """
        Create the wsgi application for the flask test extension

        :return: application instance
        """
        return app.create_app()

    def setUp(self):
        """
        Set up the database for use

        :return: no return
        """
        db.create_all()

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

        stub_uid = 1234
        self.create_library.create_user(absolute_uid=stub_uid)
        result = User.query.filter(User.absolute_uid == stub_uid).all()
        self.assertTrue(len(result) == 1)

    def test_user_creation_if_exists(self):
        """
        When adding a user that already exists with the same absolute uid, it
        should handle it gracefully, and give an exit code.

        :return: no return
        """
        #
        # stub_uid = 1234
        # user = User(absolute_uid=stub_uid)
        # db.session.add(user)
        # db.session.commit()
        #
        # self.create_library.create_user(absolute_uid=stub_uid)
        #
        # result = User.query.filter(User.absolute_uid == stub_uid).all()
        # self.assertTrue(len(result) == 1)
