"""
Functional test

Fast Job Epic

Storyboard is defined within the comments of the program itself
"""

import unittest
from flask import url_for
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop
from biblib.tests.base import MockSolrQueryService, TestCaseDatabase, MockSolrBigqueryService, MockEndPoint
import json

class TestJobFastEpic(TestCaseDatabase):
    """
    Base class used to test the Job Fast Epic
    """

    def test_job_fast_epic(self):
        """
        Carries out the epic 'Fast Job', where a user wants to add their articles to
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

        self.assertIs(list, type(stub_library.get_bibcodes()))
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
        with MockSolrBigqueryService(
                canonical_bibcode=stub_library.bibcode) as BQ, \
                MockEndPoint([user_mary]) as EP:
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
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=stub_library.document_view_post_data_json('add'),
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['number_added'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
