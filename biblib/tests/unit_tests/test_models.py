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
from models import db, User, Library, Permissions, MutableList
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

        self.assertEqual(set(lib.get_bibcodes()), set(['1', '2', '3']))

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

        self.assertEqual(
            set(lib.get_bibcodes()),
            set(expected_bibcode_output)
        )

    def test_removing_bibcodes_from_library(self):

        # Stub data
        bibcodes_list_1 = {'1': {}, '2': {}, '3': {}}
        expected_list = ['2', '3']

        lib = Library(bibcode=bibcodes_list_1)
        db.session.add(lib)
        db.session.commit()

        lib.remove_bibcodes(['1'])
        db.session.add(lib)
        db.session.commit()

        self.assertEqual(set(lib.get_bibcodes()), set(expected_list))

class TestModelTypes(TestCase):
    """
    Class for testing the behaviour of the custom types created in the models
    of the database
    """

    def create_app(self):
        """
        Create the wsgi application

        :return: application instance
        """
        app_ = app.create_app(config_type='TEST')
        return app_

    def test_append_of_mutable_list(self):
        """
        Checks that the append method of the mutable list behaves as expected

        :return: no return
        """
        expected_list = [1]
        mutable_list = MutableList()
        mutable_list.append(expected_list[0])
        self.assertEqual(expected_list, mutable_list)

    def test_extend_of_mutable_list(self):
        """
        Checks that the extend method of the mutable list behaves as expected

        :return: no return
        """
        expected_list = [1]
        mutable_list = MutableList()
        mutable_list.extend(expected_list)
        self.assertEqual(expected_list, mutable_list)

    def test_remove_when_item_does_not_exist(self):
        """
        Tests that remove behaves like the list remove when an item that
        does not exist, does not raise a KeyError

        :return: no return
        """
        test_list = [1, 2, 3]
        mutable_list = MutableList()
        mutable_list.extend(test_list)

        self.assertEqual(test_list, mutable_list)

        mutable_list.remove(4)

        self.assertEqual(test_list, mutable_list)

    def test_remove_of_mutable_list(self):
        """
        Checks that the remove method of the mutable list behaves as expected

        :return: no return
        """
        expected_list = [1]
        mutable_list = MutableList()
        mutable_list.append(expected_list[0])
        mutable_list.remove(expected_list[0])

        self.assertEqual([], mutable_list)

    def test_shorten_of_mutable_list(self):
        """
        Checks that the remove method of the mutable list behaves as expected

        :return: no return
        """
        expected_list = [1]
        mutable_list = MutableList()
        mutable_list.extend(expected_list)
        mutable_list.shorten(expected_list)

        self.assertEqual([], mutable_list)

    def test_upsert_of_mutable_list(self):
        """
        Checks that the custom upsert command works as expected

        :return: no return
        """

        input_list_1 = [1, 2, 3]
        input_list_2 = [2, 2, 3, 4, 4]
        expected_output = [1, 2, 3, 4]

        mutable_list = MutableList()
        mutable_list.extend(input_list_1)
        mutable_list.upsert(input_list_2)

        self.assertEqual(mutable_list, expected_output)

    def test_coerce(self):
        """
        Checks the coerce for SQLAlchemy works correctly

        :return: no return
        """

        mutable_list = MutableList()

        with self.assertRaises(ValueError):
            mutable_list.coerce('key', 2)

        new_type = mutable_list.coerce('key', [2])
        self.assertIsInstance(new_type, MutableList)

        same_list = mutable_list.coerce('key', mutable_list)
        self.assertEqual(same_list, mutable_list)

if __name__ == '__main__':
    unittest.main(verbosity=2)