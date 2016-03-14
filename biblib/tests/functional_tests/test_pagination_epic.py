# encoding: utf-8
"""
Functional test

Pagination Epic

Storyboard is defined within the comments of the program itself
"""

import unittest
from flask import url_for
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop
from biblib.tests.base import TestCaseDatabase, \
    MockSolrBigqueryService, MockEndPoint


class TestPaginationEpic(TestCaseDatabase):
    """
    Base class used to test the Pagination Epic
    """

    def test_pagination_epic(self):
        """
        Carries out the epic 'Pagination', where a user is paginating through
        pages of 20 documents on their user interface.
        """

        # Mary creates a private library and
        #   1. Gives it a name.
        #   2. Gives it a description.

        # Create stub data for:
        # 1. the user, named Mary
        # 2. a library, prefilled with name, description, and bibcodes
        user_mary = UserShop()
        stub_bibcodes = {
            '2010MNRAS': {},
            '2012MNRAS': {},
            '2012MNRAS': {},
            '2014MNRAS': {},
        }
        solr_docs_page_1 = [{'bibcode': '2010MNRAS'}, {'bibcode': '2011MNRAS'}]
        solr_docs_page_2 = [{'bibcode': '2012MNRAS'}, {'bibcode': '2014MNRAS'}]

        docs_page_1 = ['2010MNRAS', '2011MNRAS']
        docs_page_2 = ['2012MNRAS', '2014MNRAS']

        stub_library = LibraryShop(want_bibcode=True, bibcode=stub_bibcodes)

        # Make the library by using the /library POST end point
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_mary.headers
        )
        self.assertStatus(response, 200)

        # Library ID is returned from this POST request
        library_id = response.json['id']

        # Now we check that we can retrieve the first 20 paginated documents
        # First set up the parameters for pagination
        params = {
            'start': 0,
            'rows': 2,
        }
        # Then send the GET request
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(solr_docs=solr_docs_page_1) as BQ, \
                MockEndPoint([user_mary]) as EP:
            response = self.client.get(
                url,
                headers=user_mary.headers,
                query_string=params
            )
        self.assertStatus(response, 200)
        self.assertEqual(docs_page_1, response.json['documents'])

        # Then ask for the second page
        params = {
            'start': 2,
            'rows': 2
        }
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(solr_docs=solr_docs_page_2) as BQ, \
                MockEndPoint([user_mary]) as EP:
            response = self.client.get(
                url,
                headers=user_mary.headers,
                query_string=params
            )
        self.assertStatus(response, 200)
        self.assertEqual(docs_page_2, response.json['documents'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
