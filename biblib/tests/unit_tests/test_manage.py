"""
Tests the methods within the flask-script file manage.py
"""

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import test_config
import unittest
from manage import CreateDatabase, DestroyDatabase
from models import User, Library, Permissions
from sqlalchemy import create_engine, MetaData

class TestManagePy(unittest.TestCase):
    """
    Class for testing the behaviour of the custom manage scripts
    """

    def test_create_database(self):
        """
        Tests the CreateDatabase action. This should create all the tables
        that should exist in the database.

        :return: no return
        """

        # Setup the tables
        CreateDatabase.run()
        engine = create_engine(test_config.SQLALCHEMY_BINDS['libraries'])
        connection = engine.connect()

        for model in [User, Library, Permissions]:
            exists = engine.dialect.has_table(connection, model.__tablename__)
            self.assertTrue(exists)

        # Clean up the tables
        MetaData().drop_all(bind=engine)

    def test_destroy_database(self):
        """
        Tests the DestroyDatabase action. This should clear all the tables
        that were created in the database.

        :return: no return
        """

        # Setup the tables
        engine = create_engine(test_config.SQLALCHEMY_BINDS['libraries'])
        connection = engine.connect()
        MetaData().create_all(bind=engine)

        DestroyDatabase.run()

        for model in [User, Library, Permissions]:
            exists = engine.dialect.has_table(connection, model.__tablename__)
            self.assertFalse(exists)

if __name__ == '__main__':
    unittest.main(verbosity=2)