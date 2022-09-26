"""
Functional test

Big Share Admin Epic

Storyboard is defined within the comments of the program itself
"""

import unittest
from flask import url_for
from biblib.views.http_errors import NO_PERMISSION_ERROR
from biblib.views import DocumentView
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop, fake_biblist
from biblib.tests.base import MockEmailService, MockSolrBigqueryService, MockSolrQueryService,\
    TestCaseDatabase, MockEndPoint
import json

class TestBigShareAdminEpic(TestCaseDatabase):
    """
    Base class used to test the Big Share Admin Epic
    """

    def test_big_share_admin(self):
        """
        Carries out the epic 'Big Share Admin', where a user creates a library
        and wants one other user to have admin permissions, i.e., add and
        remove users permissions (except the owners) from the library.

        :return: no return
        """

        # Generate some stub data for Dave, Mary and the student
        user_dave = UserShop()
        user_mary = UserShop()
        user_student = UserShop()

        library_dave = LibraryShop()

        # Librarian Dave makes a big library full of bibcodes
        #  1. Lets say 20 bibcodes
        # Dave makes his library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=library_dave.user_view_post_data_json,
            headers=user_dave.headers
        )
        self.assertEqual(response.status_code, 200, response)
        library_id_dave = response.json['id']

        # Dave adds content to his library
        libraries_added = []
        number_of_documents = 20
        for i in range(number_of_documents):

            # Stub data
            stub_library = LibraryShop()
            libraries_added.append(stub_library)

            # Add document
            with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
                url = url_for('documentview', library=library_id_dave)
                response = self.client.post(
                    url,
                    data=stub_library.document_view_post_data_json('add'),
                    headers=user_dave.headers
                )
            self.assertEqual(response.json['number_added'],
                             len(stub_library.bibcode))
            self.assertEqual(response.status_code, 200, response)

        canonical_bibcode = \
            [i.get_bibcodes()[0] for i in libraries_added]
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(
                canonical_bibcode=canonical_bibcode) as BQ, \
                MockEndPoint([user_dave]) as EP:
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertTrue(len(response.json['documents']) == number_of_documents)

        # Dave does not want to manage who can change content. He wants Mary to
        # adminstrate the library. Mary tries, but gets errors. need a
        # permissions endpoint
        # /permissions/<uuid_library>
        url = url_for('permissionview', library=library_id_dave)
        with MockEmailService(user_student):
            response = self.client.post(
                url,
                data=user_student.permission_view_post_data_json(
                    {'read': False, 'write': True, 'admin': False, 'owner': False}
                ),
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
                data=user_mary.permission_view_post_data_json({'read': False, 'write': False, 'admin': True, 'owner': False}),
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)

        # Mary then adds the student as an admin
        url = url_for('permissionview', library=library_id_dave)
        with MockEmailService(user_student):
            response = self.client.post(
                url,
                data=user_student.permission_view_post_data_json(
                    {'read': False, 'write': True, 'admin': False, 'owner': False}
                ),
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, 200)

        # The student removes a few bibcodes and keeps a list of the ones she
        # removed just in case
        url = url_for('documentview', library=library_id_dave)

        libraries_removed = []
        for i in range(number_of_documents // 2):
            # Remove documents
            response = self.client.post(
                url,
                data=libraries_added[i].document_view_post_data_json('remove'),
                headers=user_student.headers
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
                MockEndPoint([user_student, user_dave]) as EP:
            response = self.client.get(
                url,
                headers=user_student.headers
            )
        self.assertTrue(
            len(response.json['documents']) == number_of_documents/2.
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

        # She checks that they got added
        canonical_bibcode = [i.get_bibcodes()[0] for i in libraries_added]
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(
                canonical_bibcode=canonical_bibcode) as BQ, \
                MockEndPoint([user_dave, user_student]) as EP:
            response = self.client.get(
                url,
                headers=user_student.headers
            )
        self.assertTrue(
            len(response.json['documents']) == number_of_documents
        )

        # Sanity check 1
        # --------------
        # Remove the permissions of the student, they should not be able to do
        # what they could before
        # --------------
        # Mary removes the students permissions and the student tries to modify
        #  the library content, but cannot
        url = url_for('permissionview', library=library_id_dave)
        with MockEmailService(user_student):
            response = self.client.post(
                url,
                data=user_student.permission_view_post_data_json(
                    {'read': False, 'write': False, 'admin': False, 'owner': False}
                ),
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, 200)

        # The student tries to add content
        url = url_for('documentview', library=library_id_dave)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=stub_library.document_view_post_data_json('add'),
                headers=user_student.headers
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

        # Sanity check 2
        # --------------
        # Check that you cannot modify owner permissions
        # --------------
        # Mary tries to give the student owner permissions
        url = url_for('permissionview', library=library_id_dave)
        with MockEmailService(user_student):
            response = self.client.post(
                url,
                data=user_student.permission_view_post_data_json(
                    {'read': False, 'write': False, 'admin': False, 'owner': True}
                ),
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code,
                         NO_PERMISSION_ERROR['number'],
                         response.json)
        self.assertEqual(response.json['error'],
                         NO_PERMISSION_ERROR['body'],
                         response.json)

        # Sanity check 3
        # --------------
        # Mary tries to manipulate Daves permissions
        # --------------
        # Mary attempts to change the read, admin, write, owner, permissions
        # of Dave, but should fail
        url = url_for('permissionview', library=library_id_dave)
        for permission_type in ['read', 'write', 'admin', 'owner']:
            with MockEmailService(user_dave):
                response = self.client.post(
                    url,
                    data=user_dave.permission_view_post_data_json(
                        {permission_type: False}
                    ),
                    headers=user_mary.headers
                )
            self.assertEqual(response.status_code,
                             NO_PERMISSION_ERROR['number'])
            self.assertEqual(response.json['error'],
                             NO_PERMISSION_ERROR['body'])

        # Sanity check 4
        # --------------
        # Remove Mary's permissions so she cannot do what she was doing before
        # --------------
        # Dave removes Mary's permissions.
        url = url_for('permissionview', library=library_id_dave)
        with MockEmailService(user_mary):
            response = self.client.post(
                url,
                data=user_mary.permission_view_post_data_json({'read': False, 'write': False, 'admin': False, 'owner': False}),
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)

        # Mary tries to change permissions for the student again but should
        # not be able to
        with MockEmailService(user_student):
            response = self.client.post(
                url,
                data=user_student.permission_view_post_data_json(
                    {'read': False, 'write': True, 'admin': False, 'owner': False}
                ),
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])


if __name__ == '__main__':
    unittest.main(verbosity=2)