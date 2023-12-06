"""
Functional test

Job Epic

Storyboard is defined within the comments of the program itself
"""

import unittest
from flask import url_for
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop
from biblib.views import DocumentView
from biblib.tests.base import MockSolrQueryService, TestCaseDatabase, MockEmailService, \
    MockSolrBigqueryService, MockEndPoint
import json

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
        stub_library = LibraryShop(public=True)

        # Make the library and make it public to be viewed by employers
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_mary.headers
        )
        self.assertEqual(response.status_code, 200, response)
        self.assertTrue('name' in response.json)
        self.assertTrue(response.json['name'] == stub_library.name)

        # Mary searches for an article and then adds it to her private library.
        # First she picks which library to add it to.
        url = url_for('userview')
        with MockEmailService(user_mary, end_type='uid'):
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        library_id = response.json['libraries'][0]['id']

        # Then she submits the document (in this case a bibcode) to add to the
        # library
        url = url_for('documentview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=stub_library.document_view_post_data_json('add'),
                headers=user_mary.headers
            )
        self.assertEqual(response.json['number_added'],
                         len(stub_library.bibcode))
        self.assertEqual(response.status_code, 200, response)

        # Mary realises she added one that is not hers and goes back to her
        # list and deletes it from her library.
        url = url_for('documentview', library=library_id)
        response = self.client.post(
            url,
            data=stub_library.document_view_post_data_json('remove'),
            headers=user_mary.headers
        )
        self.assertEqual(response.json['number_removed'],
                         len(stub_library.bibcode))
        self.assertEqual(response.status_code, 200, response)

        # Checks that there are no documents in the library
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(number_of_bibcodes=0) as BQ, \
                MockEndPoint([user_mary]) as EP:
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        self.assertTrue(len(response.json['documents']) == 0, response.json)

        # Happy with her library, she copies the link to the library and
        # e-mails it to the prospective employer.

        # She then asks a friend to check the link, and it works fine.
        with MockSolrBigqueryService(number_of_bibcodes=0) as BQ, \
                MockEndPoint([user_mary, user_random]) as EP:
            response = self.client.get(
                url,
                headers=user_random.headers
            )
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main(verbosity=2)