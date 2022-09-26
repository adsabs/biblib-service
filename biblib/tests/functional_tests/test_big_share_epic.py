"""
Functional test

Big Share Epic

Storyboard is defined within the comments of the program itself
"""

import unittest
from flask import url_for
from biblib.views.http_errors import NO_PERMISSION_ERROR
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop
from biblib.views import DocumentView
from biblib.tests.base import MockEmailService, MockSolrBigqueryService, MockSolrQueryService,\
    TestCaseDatabase, MockEndPoint
import json
class TestBigShareEpic(TestCaseDatabase):
    """
    Base class used to test the Big Share Epic
    """

    def test_big_share(self):
        """
        Carries out the epic 'Big Share', where a user wants to share one of
        their big libraries they have created

        :return: no return
        """

        # Librarian Dave makes a big library full of bibcodes
        #  1. Lets say 20 bibcodes

        # Stub data
        user_dave = UserShop()
        user_mary = UserShop()

        stub_library = LibraryShop()

        # Make a library for Mary
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_mary.headers
        )
        self.assertEqual(response.status_code, 200, response)
        library_id_mary = response.json['id']

        # Dave makes his library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_dave.headers
        )
        self.assertEqual(response.status_code, 200, response)
        library_id_dave = response.json['id']

        # Let us just double check that their ids do not match
        self.assertNotEqual(library_id_mary, library_id_dave)

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

        # Dave has made his library private, and his library friend Mary says
        # she cannot access the library.
        # Dave selects her e-mail address
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(
                number_of_bibcodes=number_of_documents) as BQ, \
                MockEndPoint([user_dave, user_mary]) as EP:
            response = self.client.get(
                url,
                headers=user_mary.headers
            )

        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertNotIn('documents', response.json.keys())
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

        # Ask API for the user_id, if it does not exist, we send an e-mail?
        # Dave then gives Mary the permissions to read his library
        url = url_for('permissionview', library=library_id_dave)
        with MockEmailService(user_mary):
            response = self.client.post(
                url,
                data=user_mary.permission_view_post_data_json({'read': True, 'write': False, 'admin': False, 'owner': False}),
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)

        # Mary says she cannot see the libraries. Dave checks that Mary is in
        # the list of permissions
        with MockEndPoint([user_dave, user_mary]):
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertIn(user_dave.email, response.json[0].keys())
        self.assertIn(user_mary.email, response.json[1].keys())
        self.assertEqual(['owner'], response.json[0][user_dave.email])
        self.assertEqual(['read'], response.json[1][user_mary.email])

        # Mary tries to check who has permissions too, but does not have
        # permission given she only has 'read' rights.
        with MockEndPoint([user_dave, user_mary]):
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
            self.assertEqual(response.status_code,
                             NO_PERMISSION_ERROR['number'])
            self.assertEqual(response.json['error'],
                             NO_PERMISSION_ERROR['body'])

        # Mary finally realises she has not logged in, and then writes back to
        # say she can see his libraries and is happy but wants to add content
        # herself
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(
                number_of_bibcodes=number_of_documents) as BQ, \
                MockEndPoint([user_dave, user_mary]) as EP:
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json['documents']) == number_of_documents)

        # Mary tries to modify the permissions of Dave, but
        # nothing happens
        url = url_for('permissionview', library=library_id_dave)
        with MockEmailService(user_dave):
            response = self.client.post(
                url,
                data=user_dave.permission_view_post_data_json({'read': False, 'write': False, 'admin': False, 'owner': False}),
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

        # Dave is unhappy with Mary's attempt, so he removes her permissions
        # to read
        url = url_for('permissionview', library=library_id_dave)
        with MockEmailService(user_mary):
            response = self.client.post(
                url,
                data=user_mary.permission_view_post_data_json({'read': False, 'write': False, 'admin': False, 'owner': False}),
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)

        # Mary realises she can no longer read content
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(
                number_of_bibcodes=number_of_documents) as BQ, \
                MockEndPoint([user_dave, user_mary]) as EP:
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertNotIn('documents', response.json.keys())
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

if __name__ == '__main__':
    unittest.main(verbosity=2)