"""
Functional test

Returned Solr Data Epic

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
from tests.base import MockSolrBigqueryService, TestCaseDatabase, MockEndPoint


class TestReturnedSolrDataEpic(TestCaseDatabase):
    """
    Base class used to test the Returned Solr Data Epic
    """

    def test_returned_data_solr(self):
        """
        Carries out the epic 'Returned Solr Data', for the LibraryView GET
        end point

        This communicates with the external solr bigquery service. Any calls
        to the service are mocked in this test.

        :return: no return
        """

        # Stub data
        user_dave = UserShop()
        stub_library = LibraryShop(want_bibcode=True)

        # Librarian Dave makes a library with a few bibcodes
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_dave.headers
        )
        self.assertEqual(response.status_code, 200, response)
        library_id_dave = response.json['id']

        # Dave clicks the library to open it and sees that the content is
        # filled with the same information found on the normal search pages.
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService() as BQ, MockEndPoint([user_dave]) as EP:
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('documents', response.json)
        self.assertIn('solr', response.json)

        # The solr microservice goes down, I expect we should not rely on the
        # content to display something semi-nice in the mean time. So even
        # if it fails, we should get a 200 response
        with MockSolrBigqueryService(status=500) as BQ, \
                MockEndPoint([user_dave]) as EP:
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('documents', response.json)
        self.assertIn('solr', response.json)

if __name__ == '__main__':
    unittest.main(verbosity=2)