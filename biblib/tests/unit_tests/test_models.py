"""
Tests the underlying models of the database
"""

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import app
import unittest
from models import db, User, Library, Permissions, MutableDict
from flask.ext.testing import TestCase
from tests.base import TestCaseDatabase

class TestLibraryModel(TestCaseDatabase):
    """
    Class for testing the methods usable by the Library model
    """

    def create_app(self):
        """
        Create the wsgi application

        :return: application instance
        """
        app_ = app.create_app(config_type='TEST')
        return app_

    def test_get_bibcodes_from_model(self):
        """
        Checks that the get_bibcodes method works as expected
        """
        lib = Library(bibcode={'1': {}, '2': {}, '3': {}})
        db.session.add(lib)
        db.session.commit()

        self.assertUnsortedEqual(lib.get_bibcodes(), ['1', '2', '3'])

    def test_adding_bibcodes_to_library(self):
        """
        Checks that the custom add/upsert command works as expected
        """
        # Make fake library
        bibcodes_list_1 = {'1': {}, '2': {}, '3': {}}
        bibcodes_list_2 = ['2', '2', '3', '4', '4']
        expected_bibcode_output = ['1', '2', '3', '4']

        lib = Library(bibcode=bibcodes_list_1)
        db.session.add(lib)
        db.session.commit()

        lib.add_bibcodes(bibcodes_list_2)
        db.session.add(lib)
        db.session.commit()

        self.assertUnsortedEqual(lib.get_bibcodes(), expected_bibcode_output)

    def test_adding_bibcode_if_not_commited_to_library(self):
        """
        Checks that bibcodes are add correctly if the library has not been
        commited to the db yet.
        """
        bibcodes_list = ['1', '2', '3', '4']

        lib = Library()
        lib.add_bibcodes(bibcodes_list)
        db.session.add(lib)
        db.session.commit()

        self.assertEqual(lib.bibcode, {k: {} for k in bibcodes_list})
        self.assertUnsortedEqual(lib.get_bibcodes(), bibcodes_list)

    def test_removing_bibcodes_from_library(self):
        """
        Checks that bibcodes get removed from a library correctly
        """
        # Stub data
        bibcodes_list_1 = {'1': {}, '2': {}, '3': {}}
        expected_list = ['2', '3']

        lib = Library(bibcode=bibcodes_list_1)
        db.session.add(lib)
        db.session.commit()

        lib.remove_bibcodes(['1'])
        db.session.add(lib)
        db.session.commit()

        self.assertUnsortedEqual(lib.get_bibcodes(), expected_list)

    def test_coerce(self):
        """
        Checks the coerce for SQLAlchemy works correctly
        """
        mutable_dict = MutableDict()

        with self.assertRaises(ValueError):
            mutable_dict.coerce('key', 2)

        new_type = mutable_dict.coerce('key', {'key': 'value'})
        self.assertIsInstance(new_type, MutableDict)

        same_list = mutable_dict.coerce('key', mutable_dict)
        self.assertEqual(same_list, mutable_dict)

if __name__ == '__main__':
    unittest.main(verbosity=2)