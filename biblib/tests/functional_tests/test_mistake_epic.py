"""
Functional test

Mistake Epic

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
from views import DEFAULT_LIBRARY_NAME_PREFIX, DEFAULT_LIBRARY_DESCRIPTION

class TestMistakeEpic(TestCaseDatabase):
    """
    Base class used to test the Mistake Epic
    """

    def test_mistake_epic(self):
        """
        Carries out the epic 'Mistake', where a user wants to update the meta
        data of their library, once they have created the library. They see
        that the library already has a pre-filled title that they did not
        change, and want to update it afterwards.

        :return: no return
        """

        # Stub data
        user_mary = UserShop()
        stub_library = LibraryShop(name='', description='')

        # Mary creates a private library and
        # Does not fill any of the details requested, and then looks at the
        # newly created library.
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_mary.headers
        )
        library_id = response.json['id']
        library_name = response.json['name']
        library_description = response.json['description']
        self.assertEqual(response.status_code, 200, response)
        self.assertTrue('name' in response.json, response.json)
        self.assertTrue(response.json['name'] != '')

        # Mary updates the name and description of the library, but leaves the
        # details blank. This should not update the names as we do not want
        # them as blank.
        for meta_data, update in [['name', ''], ['description', '']]:

            # Make the change
            url = url_for('documentview', library=library_id)
            response = self.client.put(
                url,
                data=stub_library.document_view_put_data_json(
                    meta_data, update
                ),
                headers=user_mary.headers
            )
            self.assertEqual(response.status_code, 200)

            # Check the change did not work
            url = url_for('userview', library=library_id)
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
            self.assertEqual(library_name,
                             '{0} 1'.format(DEFAULT_LIBRARY_NAME_PREFIX))
            self.assertEqual(library_description,
                             DEFAULT_LIBRARY_DESCRIPTION)

        # Mary updates the name and description of the library to something
        # sensible
        for meta_data, update in [['name', 'test'], ['description', 'test2']]:

            # Make the change
            url = url_for('documentview', library=library_id)
            response = self.client.put(
                url,
                data=stub_library.document_view_put_data_json(
                    meta_data, update
                ),
                headers=user_mary.headers
            )
            self.assertEqual(response.status_code, 200)

            # Check the change worked
            url = url_for('userview', library=library_id)
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
            self.assertEqual(update,
                             response.json['libraries'][0][meta_data])

if __name__ == '__main__':
    unittest.main(verbosity=2)