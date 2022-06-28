"""
Functional test

Big Share Editor Epic

Storyboard is defined within the comments of the program itself
"""

import unittest
from flask import url_for
from biblib.views.http_errors import NO_PERMISSION_ERROR
from biblib.views import DocumentView
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop
from biblib.tests.base import MockEmailService, MockSolrBigqueryService, MockSolrQueryService,\
    TestCaseDatabase, MockEndPoint
import json

class TestBigShareEditorEpic(TestCaseDatabase):
    """
    Base class used to test the Big Share Editor Epic
    """

    def test_big_share_editor(self):
        """
        Carries out the epic 'Big Share Editor', where a user creates a library
        and wants one other use to have editing permissions, i.e., add and
        remove bibcodes from the library.

        :return: no return
        """

        # Stub data for users, etc.
        user_dave = UserShop()
        user_mary = UserShop()
        library_dave = LibraryShop()

        # Librarian Dave makes a big library full of content
        url = url_for('userview')
        response = self.client.post(
            url,
            data=library_dave.user_view_post_data_json,
            headers=user_dave.headers
        )
        library_id_dave = response.json['id']
        self.assertEqual(response.status_code, 200, response)

        # Dave adds content to his library
        libraries_added = []
        number_of_documents = 20
        for i in range(number_of_documents):
            # Add document

            library = LibraryShop()
            with MockSolrQueryService(canonical_bibcode = json.loads(library.document_view_post_data_json('add')).get('bibcode')) as SQ:
                url = url_for('documentview', library=library_id_dave)
                response = self.client.post(
                    url,
                    data=library.document_view_post_data_json('add'),
                    headers=user_dave.headers
                )
            self.assertEqual(response.json['number_added'],
                             len(library.bibcode))
            self.assertEqual(response.status_code, 200, response)

            libraries_added.append(library)

        # Checks they are all in the library
        url = url_for('libraryview', library=library_id_dave)
        canonical_bibcode = [i.get_bibcodes()[0] for i in libraries_added]
        with MockSolrBigqueryService(
                canonical_bibcode=canonical_bibcode) as BQ, \
                MockEndPoint([user_dave]) as EP:
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertTrue(len(response.json['documents']) == number_of_documents)

        # Dave is too busy to do any work on the library and so asks his
        # librarian friend Mary to do it. Dave does not realise she cannot
        # add without permissions and Mary gets some error messages
        url = url_for('documentview', library=library_id_dave)
        with MockSolrQueryService(canonical_bibcode = json.loads(library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=library.document_view_post_data_json('add'),
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

        # Dave now adds her account to permissions. She already has an ADS
        # account, and so Dave adds her with her e-mail address with read and
        # write permissions (but not admin).
        url = url_for('permissionview', library=library_id_dave)
        with MockEmailService(user_mary):
            response = self.client.post(
                url,
                data=user_mary.permission_view_post_data_json({'read': False, 'write': True, 'admin': False, 'owner': False}),
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)

        # Mary looks at the library
        canonical_bibcode = [i.get_bibcodes()[0] for i in libraries_added]
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(
                canonical_bibcode=canonical_bibcode) as BQ, \
                MockEndPoint([user_dave, user_dave]) as EP:
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json['documents']) == number_of_documents)

        # Mary removes a few bibcodes and keeps a list of the ones she
        # removed just in case
        url = url_for('documentview', library=library_id_dave)

        libraries_removed = []
        for i in range(number_of_documents // 2):
            # Remove documents
            response = self.client.post(
                url,
                data=libraries_added[i].document_view_post_data_json('remove'),
                headers=user_mary.headers
            )
            self.assertEqual(response.json['number_removed'],
                             len(libraries_added[i].bibcode))
            self.assertEqual(response.status_code, 200, response)

            libraries_removed.append(libraries_added[i])
            libraries_added.remove(libraries_added[i])

        # She checks that they got removed
        canonical_bibcode = [i.get_bibcodes()[0] for i in libraries_added]
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(
                canonical_bibcode=canonical_bibcode) as BQ, \
                MockEndPoint([user_dave, user_mary]) as EP:
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        self.assertTrue(
            len(response.json['documents']) == number_of_documents // 2
        )

        # Dave asks Mary to re-add the ones she removed because they were
        # actually useful
        url = url_for('documentview', library=library_id_dave)
        for library in libraries_removed:
            # Add documents
            with MockSolrQueryService(canonical_bibcode = json.loads(library.document_view_post_data_json('add')).get('bibcode')) as SQ:
                response = self.client.post(
                    url,
                    data=library.document_view_post_data_json('add'),
                    headers=user_mary.headers
                )
            self.assertEqual(response.json['number_added'],
                             len(library.bibcode))
            self.assertEqual(response.status_code, 200, response)

            libraries_added.append(library)
            canonical_bibcode.extend(library.get_bibcodes())

        # She checks that they got added
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(canonical_bibcode=canonical_bibcode) \
                as BQ, MockEndPoint([user_dave, user_mary]) as EP:
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        self.assertTrue(
            len(response.json['documents']) == number_of_documents
        )

        # Sanity check
        # Dave removes her permissions and Mary tries to modify the library
        # content, but cannot
        url = url_for('permissionview', library=library_id_dave)
        with MockEmailService(user_mary):
            response = self.client.post(
                url,
                data=user_mary.permission_view_post_data_json({'read': False, 'write': False, 'admin': False, 'owner': False}),
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)

        # Mary tries to add content
        url = url_for('documentview', library=library_id_dave)            
        with MockSolrQueryService(canonical_bibcode = json.loads(library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=library.document_view_post_data_json('add'),
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
