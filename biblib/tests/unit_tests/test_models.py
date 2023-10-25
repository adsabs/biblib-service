"""
Tests the underlying models of the database
"""

import unittest
from biblib.models import User, Library, Permissions, MutableDict
from biblib.tests.base import TestCaseDatabase

class TestLibraryModel(TestCaseDatabase):
    """
    Class for testing the methods usable by the Library model
    """
    def test_get_bibcodes_from_model(self):
        """
        Checks that the get_bibcodes method works as expected
        """
        lib = Library(bibcode={'1': {}, '2': {}, '3': {}})
        with self.app.session_scope() as session:
            session.add(lib)
            session.commit()

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
        with self.app.session_scope() as session:
            session.add(lib)
            session.commit()

            lib.add_bibcodes(bibcodes_list_2)
            session.add(lib)
            session.commit()

            self.assertUnsortedEqual(lib.get_bibcodes(), expected_bibcode_output)

    def test_adding_bibcode_if_not_commited_to_library(self):
        """
        Checks that bibcodes are add correctly if the library has not been
        commited to the db yet.
        """
        bibcodes_list = ['1', '2', '3', '4']

        lib = Library()
        lib.add_bibcodes(bibcodes_list)
        with self.app.session_scope() as session:
            session.add(lib)
            session.commit()

            self.assertEqual(lib.bibcode, {k: {"timestamp":lib.bibcode[k]["timestamp"]} for k in bibcodes_list})
            self.assertUnsortedEqual(lib.get_bibcodes(), bibcodes_list)

    def test_removing_bibcodes_from_library(self):
        """
        Checks that bibcodes get removed from a library correctly
        """
        # Stub data
        bibcodes_list_1 = {'1': {}, '2': {}, '3': {}}
        expected_list = ['2', '3']

        lib = Library(bibcode=bibcodes_list_1)
        with self.app.session_scope() as session:
            session.add(lib)
            session.commit()

            lib.remove_bibcodes(['1'])
            session.add(lib)
            session.commit()

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
