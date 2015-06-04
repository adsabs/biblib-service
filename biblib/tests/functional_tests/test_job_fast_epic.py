"""
Functional test

Job Epic

Storyboard is defined within the comments of the program itself
"""

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import unittest
from views import DUPLICATE_DOCUMENT_NAME_ERROR
from flask import url_for
from tests.stubdata.stub_data import UserShop, LibraryShop
from tests.base import TestCaseDatabase

class TestJobEpic(TestCaseDatabase):
    """
    Base class used to test the Job Epic
    """

    def test_job_epic(self):
        """
        Carries out the epic 'Job', where a user wants to add their articles to
        their private libraries so that they can send it on to a prospective
        employer

        :return: no return
        """

        # Mary creates a private library and
        #   1. Gives it a name.
        #   2. Gives it a description.
        #   3. Makes it public to view.

        # Stub data
        user_mary = UserShop()
        user_random = UserShop()
        stub_library = LibraryShop(want_bibcode=True, public=True)

        self.assertIs(list, type(stub_library.bibcode))
        self.assertIs(list, type(stub_library.user_view_post_data['bibcode']))

        # Make the library and make it public to be viewed by employers
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_mary.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200, response)
        self.assertTrue('bibcode' in response.json)
        self.assertTrue(response.json['name'] == stub_library.name)

        # She then asks a friend to check the link, and it works fine.
        url = url_for('libraryview', library=library_id)
        response = self.client.get(
            url,
            headers=user_random.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['documents']),
                         len(stub_library.bibcode))

        # Accidentally tries to add the same bibcodes, but it does not work as
        # expected
        url = url_for('documentview', library=library_id)
        response = self.client.post(
            url,
            data=stub_library.document_view_post_data_json('add'),
            headers=user_mary.headers
        )
        self.assertEqual(response.status_code,
                         DUPLICATE_DOCUMENT_NAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         DUPLICATE_DOCUMENT_NAME_ERROR['body'])


if __name__ == '__main__':
    unittest.main(verbosity=2)