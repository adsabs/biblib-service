"""
Functional test

Retiring Librarian Epic

Storyboard is defined within the comments of the program itself
"""

import unittest
from flask import url_for
from biblib.views.http_errors import NO_PERMISSION_ERROR, API_MISSING_USER_EMAIL
from biblib.views import DocumentView
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop
from biblib.tests.base import MockEmailService, MockSolrBigqueryService, MockSolrQueryService,\
    TestCaseDatabase, MockEndPoint
import json
class TestRetiringLibrarianEpic(TestCaseDatabase):
    """
    Base class used to test the Retiring Librarian Epic
    """

    def test_retiring_librarian_epic(self):
        """
        Carries out the epic 'Retiring Librarian', where a user that owns and
        maintains a library wants to pass on the responsibility to someone else

        :return: no return
        """

        # Stub data
        user_dave = UserShop()
        user_mary = UserShop()

        stub_library = LibraryShop()

        # Dave has a big library that he has maintained for many years
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_dave.headers
        )
        self.assertEqual(response.status_code, 200, response)
        library_id_dave = response.json['id']

        # Dave adds content to his library
        number_of_documents = 20
        for i in range(number_of_documents):

            # Stub data
            library = LibraryShop()

            # Add document
            url = url_for('documentview', library=library_id_dave)
            with MockSolrQueryService(canonical_bibcode = json.loads(library.document_view_post_data_json('add')).get('bibcode')) as SQ:
                response = self.client.post(
                    url,
                    data=library.document_view_post_data_json('add'),
                    headers=user_dave.headers
                )
            self.assertEqual(response.json['number_added'],
                             len(library.bibcode))
            self.assertEqual(response.status_code, 200, response)

        # Check they all got added
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(
                number_of_bibcodes=number_of_documents) as BQ, \
                MockEndPoint([user_dave]) as EP:
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertTrue(len(response.json['documents']) == number_of_documents)

        # Dave is soon retiring and wants to give the permissions to the
        # person who takes over his job.
        # Unfortunately, the first time he tries, he realises she has not made
        # an ADS account
        url = url_for('transferview', library=library_id_dave)
        user_mary.name = 'fail'
        with MockEmailService(user_mary):
            response = self.client.post(
                url,
                headers=user_dave.headers,
                data=user_mary.transfer_view_post_data_json()
            )
        self.assertEqual(response.status_code,
                         API_MISSING_USER_EMAIL['number'])
        self.assertEqual(response.json['error'],
                         API_MISSING_USER_EMAIL['body'])

        # Mary makes an account and tries to transfer Dave's library herself
        # because Dave is busy
        url = url_for('transferview', library=library_id_dave)
        user_mary.name = 'Mary'
        with MockEmailService(user_mary):
            response = self.client.post(
                url,
                headers=user_mary.headers,
                data=user_mary.transfer_view_post_data_json()
            )
        self.assertEqual(response.status_code,
                         NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'],
                         NO_PERMISSION_ERROR['body'])

        # Dave finds out she has an account and then tells her he will transfer
        # the library because she does not have permissions
        url = url_for('transferview', library=library_id_dave)
        with MockEmailService(user_mary):
            response = self.client.post(
                url,
                headers=user_dave.headers,
                data=user_mary.transfer_view_post_data_json()
            )
        self.assertEqual(response.status_code, 200)

        # Dave checks he does not have access anymore
        with MockEndPoint([user_mary, user_dave]):
            url = url_for('permissionview', library=library_id_dave)
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

        # Mary sees she does infact now have ownership
        with MockEndPoint([user_mary, user_dave]):
            url = url_for('permissionview', library=library_id_dave)
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json) == 1)
        self.assertEqual(['owner'], response.json[0][user_mary.email])

if __name__ == '__main__':
    unittest.main(verbosity=2)