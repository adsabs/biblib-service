"""
Functional test

Deletion Epic

Storyboard is defined within the comments of the program itself
"""

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import unittest
from flask import url_for
from tests.stubdata.stub_data import UserShop, LibraryShop
from tests.base import TestCaseDatabase


class TestDeletionEpic(TestCaseDatabase):
    """
    Base class used to test the Deletion Epic
    """

    def test_job_epic(self):
        """
        Carries out the epic 'Deletion', where a user wants to delete their
        libraries that they have created

        :return: no return
        """

        # The librarian makes
        #  1. two different libraries on her account
        #  2. decides she wants to delete one
        #  3. decides she wants to delete the next one too
        # She then checks that they were deleted

        # Load stub data 1
        stub_user = UserShop()
        stub_library_1 = LibraryShop()
        stub_library_2 = LibraryShop()

        # Makes the two libraries
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library_1.user_view_post_data_json,
            headers=stub_user.headers
        )
        library_name_1 = response.json['name']

        self.assertEqual(response.status_code, 200, response)
        self.assertTrue('name' in response.json)
        self.assertTrue(library_name_1 == stub_library_1.name)

        # Second stub data
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library_2.user_view_post_data_json,
            headers=stub_user.headers
        )
        library_name_2 = response.json['name']

        self.assertEqual(response.status_code, 200, response)
        self.assertTrue('name' in response.json)
        self.assertTrue(library_name_2 == stub_library_2.name)

        # Check the two libraries are not the same
        self.assertNotEqual(library_name_1,
                            library_name_2,
                            'Name should be unique: {0} == {1}'
                            .format(library_name_1, library_name_2))

        # Deletes the first library
        url = url_for('userview')
        response = self.client.get(
            url,
            headers=stub_user.headers
        )
        library_id_1 = response.json['libraries'][0]['id']
        library_id_2 = response.json['libraries'][1]['id']

        # Deletes the second library
        url = url_for('documentview', library=library_id_2)
        response = self.client.delete(
            url,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)

        # Looks to check there are is only one libraries
        url = url_for('userview')
        response = self.client.get(
            url,
            headers=stub_user.headers
        )
        self.assertTrue(len(response.json['libraries']) == 1)

        # Deletes the first library
        url = url_for('documentview', library=library_id_1)
        response = self.client.delete(
            url,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)

        # Looks to check there are is only one libraries
        url = url_for('userview')
        response = self.client.get(
            url,
            headers=stub_user.headers
        )
        self.assertTrue(len(response.json['libraries']) == 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)