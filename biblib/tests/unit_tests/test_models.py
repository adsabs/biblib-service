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

    def test_coerce(self):

        mutable_list = MutableList()

        with self.assertRaises(ValueError):
            mutable_list.coerce('key', 2)

        new_type = mutable_list.coerce('key', [2])
        self.assertIsInstance(new_type, MutableList)

        same_list = mutable_list.coerce('key', mutable_list)
        self.assertEqual(same_list, mutable_list)

if __name__ == '__main__':
    unittest.main(verbosity=2)