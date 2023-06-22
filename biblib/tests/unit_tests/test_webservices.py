"""
Test webservices
"""

import json
import unittest
from flask import url_for
from biblib.views import DEFAULT_LIBRARY_DESCRIPTION, DEFAULT_LIBRARY_NAME_PREFIX
from biblib.views.http_errors import DUPLICATE_LIBRARY_NAME_ERROR, \
    MISSING_LIBRARY_ERROR, MISSING_USERNAME_ERROR, \
    NO_PERMISSION_ERROR, WRONG_TYPE_ERROR, \
    API_MISSING_USER_EMAIL, SOLR_RESPONSE_MISMATCH_ERROR, NO_CLASSIC_ACCOUNT, \
    NO_LIBRARY_SPECIFIED_ERROR, TOO_MANY_LIBRARIES_SPECIFIED_ERROR
from biblib.tests.stubdata.stub_data import LibraryShop, UserShop, fake_biblist
from biblib.tests.base import MockEmailService, MockSolrBigqueryService,\
    TestCaseDatabase, MockEndPoint, MockClassicService, MockSolrQueryService
from biblib.utils import get_item


class TestWebservices(TestCaseDatabase):
    """
    Tests that each route is an http response
    """

    def test_when_no_user_information_passed_to_user_post(self):
        """
        Test the /libraries route
        Tests that a KeyError is raised when the user ID is not passed

        :return: no return
        """

        url = url_for('userview')
        response = self.client.post(url)

        self.assertEqual(response.status_code,
                         MISSING_USERNAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         MISSING_USERNAME_ERROR['body'])

    def test_when_no_user_information_passed_to_user_get(self):
        """
        Test the /libraries route
        Tests that a KeyError is raised when the user ID is not passed

        :return: no return
        """

        url = url_for('userview')
        response = self.client.get(url)

        self.assertEqual(response.status_code,
                         MISSING_USERNAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         MISSING_USERNAME_ERROR['body'])

    def test_when_no_user_information_passed_to_library_post(self):
        """
        Test the /libraries/<library_uuid> route
        Tests that a KeyError is raised when the user ID is not passed

        :return: no return
        """

        url = url_for('documentview', library='test')
        response = self.client.post(url)

        self.assertEqual(response.status_code,
                         MISSING_USERNAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         MISSING_USERNAME_ERROR['body'])

    def test_when_no_user_information_passed_to_library_get(self):
        """
        Test the /libraries route
        Tests that a KeyError is raised when the user ID is not passed

        :return: no return
        """

        url = url_for('libraryview', library='test')
        with MockSolrBigqueryService():
            response = self.client.get(url)

        self.assertEqual(response.status_code,
                         MISSING_USERNAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         MISSING_USERNAME_ERROR['body'])

    def test_create_library_resource(self):
        """
        Test the /libraries route
        Creating the user and a library

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')

        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        self.assertNotIn('bibcode', response.json)

        # Check the library exists in the database
        url = url_for('userview')

        with MockEmailService(stub_user, end_type='uid'):
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)

        for library in response.json['libraries']:
            self.assertEqual(stub_library.name, library['name'])
            self.assertEqual(stub_library.description,
                             library['description'])

    def test_create_library_resource_response_content(self):
        """
        Test the /libraries GET end point
        Ensuring the response contains the data we expect. For now, this is
        defined within the stub data.

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)

        # Check the library exists in the database
        url = url_for('userview')
        with MockEmailService(stub_user, end_type='uid'):
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)

        for library in response.json['libraries']:
            for expected_type in stub_library.user_view_get_response():
                self.assertIn(expected_type, library.keys())

    def test_create_library_resource_and_add_bibcodes(self):
        """
        Test the /libraries route
        Creating the user and a library

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop(want_bibcode=True)

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)
        library_id = response.json['id']
        for key in ['name', 'id', 'bibcode', 'description']:
            self.assertIn(key, response.json)

        # Check the library exists in the database
        url = url_for('libraryview', library=library_id)

        with MockSolrBigqueryService(
                canonical_bibcode=stub_library.bibcode) as BQ, \
                MockEmailService(stub_user, end_type='uid') as ES:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)

        for document in response.json['documents']:
            self.assertIn(document, stub_library.bibcode)

    def test_get_solr_data_for_documents(self):
        """
        Test the /libraries/<> route to check that solr data is returned by
        the service

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop(want_bibcode=True)

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)
        library_id = response.json['id']
        for key in ['name', 'id', 'bibcode', 'description']:
            self.assertIn(key, response.json)

        # Check the library exists in the database
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService() as BQ, \
                MockEmailService(stub_user, end_type='uid') as ES:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('documents', response.json)
        self.assertIn('solr', response.json)

    def test_pagination_when_someone_passes_strings(self):
        """
        Ensure that even if someone passes strings as start/rows, that it does
        not crash the end point
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop(want_bibcode=True)

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)
        library_id = response.json['id']
        for key in ['name', 'id', 'bibcode', 'description']:
            self.assertIn(key, response.json)

        # Check the library exists in the database
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService() as BQ, \
                MockEmailService(stub_user, end_type='uid') as ES:
            response = self.client.get(
                url,
                headers=stub_user.headers,
                query_string=dict(start='not a number', rows='not a number')
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('documents', response.json)
        self.assertIn('solr', response.json)

    def test_update_library_with_solr_data(self):
        """
        Test the /libraries/<> such that the library bibcodes are updated if
        the solr data returns a new canonical bibcode.

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop(want_bibcode=True)

        # Make the library
        post_data = stub_library.user_view_post_data

        # Hard coding the biblist as otherwise it can be confusing to read
        original_bibcodes = ['1981.....AAX......A',
                             '2007.....WAS......W',
                             '1997.....SPC......S',
                             'arXiv1976.....LWW......L',
                             'arXiv2010.....KPK......K',
                             '1987.....ZMM......Z',
                             '2004.....FJE......F',
                             '2005.....VQU......V',
                             'arXiv2014.....KTC......K',
                             '1980.....TBR......T']
        canonical_biblist = ['1981.....AAX......A',
                             '2007.....WAS......W',
                             '1997.....SPC......S',
                             '1976.....LWW......L',
                             '2010.....KPK......K',
                             '1987.....ZMM......Z',
                             '2004.....FJE......F',
                             '2005.....VQU......V',
                             '1980.....TBR......T']

        solr_docs = [
            {'bibcode': '1981.....AAX......A'},
            {'bibcode': '2007.....WAS......W'},
            {'bibcode': '1997.....SPC......S'},
            {'bibcode': '1976.....LWW......L',
             'alternate_bibcode': ['arXiv1976.....LWW......L']},
            {'bibcode': '2010.....KPK......K',
             'alternate_bibcode': ['arXiv2010.....KPK......K',
                                   'arXiv2014.....KTC......K']},
            {'bibcode': '1987.....ZMM......Z'},
            {'bibcode': '2004.....FJE......F'},
            {'bibcode': '2005.....VQU......V'},
            {'bibcode': '1980.....TBR......T'}
        ]

        # Make the library
        post_data['bibcode'] = original_bibcodes

        url = url_for('userview')
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)
        library_id = response.json['id']

        # Check the library exists in the database
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(solr_docs=solr_docs) as BQ, \
                MockEndPoint([stub_user]) as EP:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('documents', response.json)
        self.assertIn('solr', response.json)
        self.assertIn('metadata', response.json)
        self.assertIn('updates', response.json)

        # Check that the solr docs updated the library docs
        lib_docs = response.json['documents']

        self.assertUnsortedEqual(canonical_biblist, lib_docs)
        self.assertUnsortedNotEqual(original_bibcodes, lib_docs)

        # Check the data returned is correct on what files were updated and why
        updates = response.json['updates']
        self.assertEqual(updates['num_updated'], 3)
        self.assertEqual(updates['duplicates_removed'], 1)
        update_list = updates['update_list']

        self.assertEqual(
            get_item(update_list, 'arXiv1976.....LWW......L'),
            '1976.....LWW......L'
        )
        self.assertEqual(
            get_item(update_list, 'arXiv2010.....KPK......K'),
            '2010.....KPK......K'
        )
        self.assertEqual(
            get_item(update_list, 'arXiv2014.....KTC......K'),
            '2010.....KPK......K'
        )

    def test_solr_does_not_update_if_weird_response(self):
        """
        Test the /libraries/<> such that the library bibcodes are not updated if
        the solr data returns a differently sized bibcode

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop(want_bibcode=True)

        # Make the library
        post_data = stub_library.user_view_post_data
        canonical_biblist = fake_biblist(10)
        non_canonical_biblist = canonical_biblist[:]

        non_canonical_biblist[1] = 'arXiv' + non_canonical_biblist[1]
        non_canonical_biblist[5] = 'arXiv' + non_canonical_biblist[5]

        post_data['bibcode'] = non_canonical_biblist

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)
        library_id = response.json['id']

        # Check the library exists in the database
        canonical_biblist.pop()
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(fail=True) as BQ, \
                MockEndPoint([stub_user]) as EP:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('documents', response.json)
        self.assertIn('solr', response.json)
        self.assertEqual(SOLR_RESPONSE_MISMATCH_ERROR['body'],
                         response.json['solr'])

        # Check that the solr docs did not change the docs
        lib_docs = response.json['documents']
        self.assertUnsortedEqual(lib_docs, non_canonical_biblist)
        self.assertUnsortedNotEqual(lib_docs, canonical_biblist)

    def test_create_library_resource_and_add_bibcodes_of_wrong_type(self):
        """
        Test the /libraries route
        Creating the user and a library

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        library_data = stub_library.user_view_post_data
        for bib_type in ['string', int(3), float(3.0), dict(test='test')]:

            library_data['bibcode'] = bib_type

            # Make the library
            url = url_for('userview')
            response = self.client.post(
                url,
                data=json.dumps(library_data),
                headers=stub_user.headers
            )
            self.assertEqual(response.status_code,
                             WRONG_TYPE_ERROR['number'])
            self.assertEqual(response.json['error'],
                             WRONG_TYPE_ERROR['body'])

    def test_document_view_post_types(self):
        """
        Tests that types raise errors if they are wrong

        :return: no return
        """
        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200)

        # Pass an action that is not a string
        post_data = stub_library.document_view_post_data('add')
        post_data['action'] = 1

        # Action type check
        url = url_for('documentview', library=library_id)
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])

        # bibcode list check
        post_data['action'] = 'add'
        post_data['bibcode'] = 2
        url = url_for('documentview', library=library_id)
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])

    def test_permission_view_post_type(self):
        """
        Tests that the content passed to the PermissionView POST end point
        has all the types checked.
        :return:
        """
        # Stub data
        stub_user = UserShop()
        stub_user_permission = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200)

        post_data = stub_user_permission.permission_view_post_data(
            permission={'read': True, 'write': False, 'admin': False, 'owner': False}
        )
        post_data['permission'] = 2

        url = url_for('permissionview', library=library_id)
        with MockEmailService(stub_user_permission):
            response = self.client.post(
                url,
                data=json.dumps(post_data),
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])

        post_data['permission'] = ['read', -1]

        url = url_for('permissionview', library=library_id)
        with MockEmailService(stub_user_permission):
            response = self.client.post(
                url,
                data=json.dumps(post_data),
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])

    def test_user_view_post_types(self):
        """
        Tests that the content passed to the UserView POST end point
        has all the types checked.
        :return:
        """
        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        post_data = stub_library.user_view_post_data
        post_data['name'] = 2

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])
        post_data['name'] = 'test'
        post_data['description'] = 2

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])
        post_data['description'] = 'test'
        post_data['public'] = -1

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])
        post_data['public'] = True
        post_data['bibcode'] = 111

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])

    def test_operations_view_post_types(self):
        """
        Tests that the content passed to the OperationsView POST endpoint has all types checked
        :return:
        """
        # Stub data
        stub_user = UserShop()
        stub_library_1 = LibraryShop()
        stub_library_2 = LibraryShop()

        # Make the libraries
        url = url_for('userview')
        response_1 = self.client.post(
            url,
            data=stub_library_1.user_view_post_data_json,
            headers=stub_user.headers
        )
        library_id_1 = response_1.json['id']

        response_2 = self.client.post(
            url,
            data=stub_library_2.user_view_post_data_json,
            headers=stub_user.headers
        )
        library_id_2 = response_2.json['id']

        # Pass an action that is not a string
        post_data = stub_library_1.operations_view_post_data()
        post_data['action'] = 1

        # Action type check
        url = url_for('operationsview', library=library_id_1)
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])

        post_data['action'] = 'bad-action'
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 400)

        # bibcode list check
        post_data['action'] = 'union'
        post_data['libraries'] = library_id_2
        url = url_for('operationsview', library=library_id_1)
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])

        # secondary libraries check
        post_data = stub_library_1.operations_view_post_data(action='union')
        url = url_for('operationsview', library=library_id_1)
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, NO_LIBRARY_SPECIFIED_ERROR['number'])
        self.assertEqual(response.json['error'], NO_LIBRARY_SPECIFIED_ERROR['body'])

        post_data['action'] = 'copy'
        post_data['libraries'] = ['lib1', 'lib2']
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, TOO_MANY_LIBRARIES_SPECIFIED_ERROR['number'])
        self.assertEqual(response.json['error'], TOO_MANY_LIBRARIES_SPECIFIED_ERROR['body'])

    def test_document_view_put_types(self):
        """
        Tests that the content passed to the UserView POST end point
        has all the types checked.

        :return: no return
        """
        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200)

        put_data = stub_library.document_view_put_data()
        put_data['name'] = 1

        url = url_for('documentview', library=library_id)
        response = self.client.put(
            url,
            data=json.dumps(put_data),
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])

        put_data = stub_library.document_view_put_data()
        put_data['description'] = 1

        url = url_for('documentview', library=library_id)
        response = self.client.put(
            url,
            data=put_data,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])

        put_data = stub_library.document_view_put_data()
        put_data['public'] = -1

        url = url_for('documentview', library=library_id)
        response = self.client.put(
            url,
            data=put_data,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])

    def test_transfer_view_post_types(self):
        """
        Tests that the content passed to the UserView POST end point
        has all the types checked.

        :return: no return
        """
        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200)

        post_data = stub_user.transfer_view_post_data()
        post_data['email'] = 1

        # Transfer it to a non-existent user
        with MockEmailService(stub_user):
            url = url_for('transferview', library=library_id)
            response = self.client.post(
                url,
                data=json.dumps(post_data),
                headers=stub_user.headers
            )

        self.assertEqual(response.status_code, WRONG_TYPE_ERROR['number'])
        self.assertEqual(response.json['error'], WRONG_TYPE_ERROR['body'])

    def test_add_document_to_library(self):
        """
        Test the /documents/<> end point with POST to add a document

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        url = url_for('documentview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=stub_library.document_view_post_data_json('add'),
                headers=stub_user.headers
            )
        self.assertEqual(response.json['number_added'],
                         len(stub_library.bibcode))
        self.assertEqual(response.status_code, 200)

        # Check the library was created and documents exist
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(
                canonical_bibcode=stub_library.bibcode) as BQ, \
                MockEmailService(stub_user, end_type='uid') as ES:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )

        self.assertEqual(response.status_code, 200, response)
        self.assertEqual(stub_library.get_bibcodes(),
                         response.json['documents'])

    def test_add_invalid_document_to_library(self):
        """
        Test the /documents/<> end point with POST to reject an invalid document

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode'), invalid=True) as SQ:
            url = url_for('documentview', library=library_id)
            response = self.client.post(
                url,
                data=stub_library.document_view_post_data_json('add'),
                headers=stub_user.headers
            )

        self.assertEqual(response.status_code, 400)

        # Check the library was created and documents exist
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(
                canonical_bibcode=stub_library.bibcode) as BQ, \
                MockEmailService(stub_user, end_type='uid') as ES:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )

        self.assertEqual(response.status_code, 200, response)
        self.assertNotEqual(stub_library.get_bibcodes(),
                         response.json['documents'])

    def test_add_some_invalid_documents_to_library(self):
        """
        Test the /documents/<> end point with POST to reject invalid documents while adding others

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop(nb_codes=2)

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        url = url_for('documentview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode'), invalid = True) as SQ:
            response = self.client.post(
                url,
                data=stub_library.document_view_post_data_json('add'),
                headers=stub_user.headers
            )
            print(response.json)
        #Check that the response is as expected.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json.get('invalid_identifiers'),
                        json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')[:1])
        self.assertEqual(response.json.get("number_added"), 1)
        
        # Check the library was created and documents exist
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(
                canonical_bibcode=stub_library.bibcode) as BQ, \
                MockEmailService(stub_user, end_type='uid') as ES:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        #Check that the expected bibcode and only the expected bibcode is in the libary.
        self.assertIn(json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')[1], response.json['documents'])
        self.assertNotIn(json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')[0], response.json['documents'])

        #Check that the library makes sense.
        self.assertEqual(response.status_code, 200, response)
        self.assertEqual(1, len(response.json.get('documents')))

    def test_cannot_add_duplicate_documents_to_library(self):
        """
        Test the /documents/<> end point with POST to add a document. Should
        not be able to add the same document more than once.

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            url = url_for('documentview', library=library_id)
            response = self.client.post(
                url,
                data=stub_library.document_view_post_data_json('add'),
                headers=stub_user.headers
            )
        print(response.json)
        self.assertEqual(response.json['number_added'],
                         len(stub_library.bibcode))
        self.assertEqual(response.status_code, 200)

        # Should not be able to add the same document
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            url = url_for('documentview', library=library_id)
            response = self.client.post(
                url,
                data=stub_library.document_view_post_data_json('add'),
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['number_added'], 0)

    def test_remove_document_from_library(self):
        """
        Test the /libraries/<> end point with POST to remove a document

        :return:
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        url = url_for('documentview', library=library_id)
        with MockSolrQueryService(canonical_bibcode=json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=stub_library.document_view_post_data_json('add'),
                headers=stub_user.headers
            )
            self.assertEqual(response.json['number_added'],
                            len(stub_library.bibcode))
            self.assertEqual(response.status_code, 200)

        # Delete the document
        url = url_for('documentview', library=library_id)
        response = self.client.post(
            url,
            data=stub_library.document_view_post_data_json('remove'),
            headers=stub_user.headers
        )
        self.assertEqual(response.json['number_removed'],
                         len(stub_library.bibcode))
        self.assertEqual(response.status_code, 200)

        # Check the library is empty
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(number_of_bibcodes=0) as BQ, \
                MockEmailService(stub_user, end_type='uid') as ES:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertTrue(len(response.json['documents']) == 0,
                        response.json['documents'])

    def test_add_query_to_library(self):
        """
        Test the /query/<> end point with POST to add a document

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        url = url_for('queryview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=stub_library.query_view_post_data_json('add'),
                headers=stub_user.headers
            )
        self.assertEqual(response.json['number_added'],
                         len(stub_library.bibcode))
        self.assertEqual(response.status_code, 200)

        # Check the library was created and documents exist
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(
                canonical_bibcode=stub_library.bibcode) as BQ, \
                MockEmailService(stub_user, end_type='uid') as ES:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )

        self.assertEqual(response.status_code, 200, response)
        self.assertEqual(stub_library.get_bibcodes(),
                         response.json['documents'])

    def test_cannot_add_duplicate_documents_to_library_from_query(self):
        """
        Test the /query/<> end point with POST to add a document. Should
        not be able to add the same document more than once.

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        url = url_for('queryview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=stub_library.query_view_post_data_json(),
                headers=stub_user.headers
            )
        self.assertEqual(response.json['number_added'],
                         len(stub_library.bibcode))
        self.assertEqual(response.status_code, 200)

        # Should not be able to add the same document
        url = url_for('queryview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=stub_library.query_view_post_data_json(),
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['number_added'], 0)

    def test_remove_document_from_library(self):
        """
        Test the /libraries/<> end point with POST to remove a document

        :return:
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        url = url_for('queryview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=stub_library.query_view_post_data_json('add'),
                headers=stub_user.headers
            )
        self.assertEqual(response.json['number_added'],
                         len(stub_library.bibcode))
        self.assertEqual(response.status_code, 200)

        # Delete the document
        url = url_for('queryview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('remove')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=stub_library.query_view_post_data_json('remove'),
                headers=stub_user.headers
            )
        self.assertEqual(response.json['number_removed'],
                         len(stub_library.bibcode))
        self.assertEqual(response.status_code, 200)

        # Check the library is empty
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(number_of_bibcodes=0) as BQ, \
                MockEmailService(stub_user, end_type='uid') as ES:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertTrue(len(response.json['documents']) == 0,
                        response.json['documents'])

    def test_add_query_to_library_get(self):
        """
        Test the /query/<> end point with POST to add a document

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        url = url_for('queryview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode'), params = stub_library.query_view_post_data('add').get('params')) as SQ:
            response = self.client.get(
                url+'/?q=author%3A"Author, N."',
                headers=stub_user.headers
            )
        self.assertEqual(response.json['number_added'],
                         len(stub_library.bibcode))
        self.assertEqual(response.status_code, 200)

        # Check the library was created and documents exist
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(
                canonical_bibcode=stub_library.bibcode) as BQ, \
                MockEmailService(stub_user, end_type='uid') as ES:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )

        self.assertEqual(response.status_code, 200, response)
        self.assertEqual(stub_library.get_bibcodes(),
                         response.json['documents'])
    
    def test_query_cannot_add_library_without_q_get(self):
        """
        Test the /query/<> end point with POST to add a document

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        url = url_for('queryview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode'), params = stub_library.query_view_post_data('add').get('params')) as SQ:
            response = self.client.get(
                url+'/?g=usesless_junk_not_real_query"',
                headers=stub_user.headers
            )

        self.assertEqual(response.status_code, 400, response)


    def test_cannot_add_duplicate_documents_to_library_from_query_get(self):
        """
        Test the /query/<> end point with POST to add a document. Should
        not be able to add the same document more than once.

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Get the library ID
        library_id = response.json['id']

        # Add to the library
        url = url_for('queryview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode'), params = stub_library.query_view_post_data('add').get('params')) as SQ:
            response = self.client.get(
                url+'/?q=author%3A"Author, N."',
                headers=stub_user.headers
            )
        self.assertEqual(response.json['number_added'],
                         len(stub_library.bibcode))
        self.assertEqual(response.status_code, 200)

        # Should not be able to add the same document
        url = url_for('queryview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode'), params = stub_library.query_view_post_data('add').get('params')) as SQ:
            response = self.client.post(
                url,
                data=stub_library.query_view_post_data_json(),
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['number_added'], 0)

    def _create_libraries(self, n=2, lib_data=None):
        """
        Create testing libraries
        :param n: <int> number of libraries to create
        :param data: <list> bibcode data to insert in libraries
        :return lib_ids: list of library ids
                libraries: list of stub_libraries
                stub_user: stub_user who owns libraries
        """
        # Stub data
        stub_user = UserShop()

        lib_ids = []
        libraries = []
        for nl in range(n):
            stub_library = LibraryShop()

            # Make the libraries
            url = url_for('userview')
            response_1 = self.client.post(
                url,
                data=stub_library.user_view_post_data_json,
                headers=stub_user.headers
            )
            self.assertEqual(response_1.status_code, 200)

            if not lib_data:
                data = stub_library.document_view_post_data_json('add')
            else:
                data = lib_data[nl]

            library_id = response_1.json['id']
            with MockSolrQueryService(canonical_bibcode=json.loads(data).get('bibcode')) as SQ:
                response_2 = self.client.post(
                    url_for('documentview', library=library_id),
                    data=data,
                    headers=stub_user.headers
                )
            self.assertEqual(response_2.status_code, 200)

            lib_ids.append(library_id)
            libraries.append(stub_library)

        return lib_ids, libraries, stub_user

    def test_library_union(self):
        """
        Test the /libraries/operations/<> endpoint with POST to take the union of libraries
        :return:
        """
        library_ids, stub_libraries, stub_user = self._create_libraries(n=2)

        # take the union
        url = url_for('operationsview', library=library_ids[0])
        post_data = stub_libraries[0].operations_view_post_data(action='union',libraries=[library_ids[1]])
        # check the default name
        post_data.pop('name')
        # check the default description
        post_data.pop('description')
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Untitled',response.json['name'])
        self.assertIn('Union',response.json['description'])
        self.assertIn('bibcode', response.json)

    def test_library_union_many(self):
        """
        Test the union with many libraries
        :return:
        """
        library_ids, stub_libraries, stub_user = self._create_libraries(n=10)
        post_data = stub_libraries[0].operations_view_post_data(action='union', libraries=library_ids[1:])
        # make sure the default description isn't too long
        post_data.pop('description')

        url = url_for('operationsview', library=library_ids[0])
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Union', response.json['description'])
        self.assertIn('9 other libraries', response.json['description'])

    def test_library_intersection(self):
        """
        Test the /libraries/operations/<> endpoint with POST to take the intersection of libraries
        :return:
        """
        library_ids, stub_libraries, stub_user = self._create_libraries(n=2,
                                                                        lib_data=[json.dumps({'bibcode': ['test1', 'test2'], 'action':'add'}),
                                                                                  json.dumps({'bibcode': ['test1', 'test3'], 'action':'add'})])
        # take the intersection
        url = url_for('operationsview', library=library_ids[0])
        post_data = stub_libraries[0].operations_view_post_data(name='Library3', action='intersection', libraries=[library_ids[1]])
        # check the default description
        post_data.pop('description')
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], 'Library3')
        self.assertIn('Intersection', response.json['description'])
        self.assertIn('test1', response.json['bibcode'])

    def test_library_intersection_many(self):
        """
        Test the intersection of many libraries
        :return:
        """

        library_ids, \
        stub_libraries, \
        stub_user = self._create_libraries(n=10, lib_data=[json.dumps({'bibcode': ['test1', 'test2'], 'action': 'add'}),
                                                           json.dumps({'bibcode': ['test1', 'test3'], 'action': 'add'}),
                                                           json.dumps({'bibcode': ['test1', 'test4'], 'action': 'add'}),
                                                           json.dumps({'bibcode': ['test1', 'test5'], 'action': 'add'}),
                                                           json.dumps({'bibcode': ['test1', 'test6'], 'action': 'add'}),
                                                           json.dumps({'bibcode': ['test1', 'test7'], 'action': 'add'}),
                                                           json.dumps({'bibcode': ['test1', 'test8'], 'action': 'add'}),
                                                           json.dumps({'bibcode': ['test1', 'test9'], 'action': 'add'}),
                                                           json.dumps({'bibcode': ['test1', 'test10'], 'action': 'add'}),
                                                           json.dumps({'bibcode': ['test1', 'test11'], 'action': 'add'}),])

        # take the intersection
        url = url_for('operationsview', library=library_ids[0])
        post_data = stub_libraries[0].operations_view_post_data(name='Library Many', action='intersection',
                                                                libraries=library_ids[1:])
        # check the default description
        post_data.pop('description')
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Intersection', response.json['description'])
        self.assertIn('9 other libraries', response.json['description'])

    def test_library_difference(self):
        """
        Test the /libraries/operations/<> endpoint with POST to take the difference of libraries
        :return:
        """
        library_ids, stub_libraries, stub_user = self._create_libraries(n=2,
                                                                        lib_data=[json.dumps({'bibcode': ['test1', 'test2'],'action': 'add'}),
                                                                                  json.dumps({'bibcode': ['test1', 'test3'],'action': 'add'})])
        # take the difference
        url = url_for('operationsview', library=library_ids[0])
        post_data = stub_libraries[0].operations_view_post_data(name='Library3', action='difference', libraries=[library_ids[1]])
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], 'Library3')
        self.assertIn('test2', response.json['bibcode'])

    def test_library_copy(self):
        """
        Test the /libraries/operations/<> endpoint with POST to copy one library to another
        :return:
        """
        library_ids, stub_libraries, stub_user = self._create_libraries(n=2,
                                                                        lib_data=[json.dumps({'bibcode': ['test1', 'test2'],'action': 'add'}),
                                                                                  json.dumps({'bibcode': ['test1', 'test3'],'action': 'add'})])
        # copy one to the other
        url = url_for('operationsview', library=library_ids[0])
        post_data = stub_libraries[0].operations_view_post_data(action='copy', libraries=[library_ids[1]])
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['name'], stub_libraries[1].name)
        self.assertIn('test2', response.json['bibcode'])

    def test_library_empty(self):
        """
        Test the /libraries/operations/<> endpoint with POST to copy one library to another
        :return:
        """
        library_ids, stub_libraries, stub_user = self._create_libraries(n=1,
                                                                        lib_data=[json.dumps({'bibcode': ['test1', 'test2'],'action': 'add'})])
        # empty the library
        url = url_for('operationsview', library=library_ids[0])
        post_data = stub_libraries[0].operations_view_post_data(action='empty')
        response = self.client.post(
            url,
            data=json.dumps(post_data),
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['bibcode'], [])

    def test_cannot_add_library_with_duplicate_names(self):
        """
        Test the /liraries end point with POST to ensure two libraries cannot
        have the same name

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make first library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)

        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Make another one with the same name
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code,
                         DUPLICATE_LIBRARY_NAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         DUPLICATE_LIBRARY_NAME_ERROR['body'])

    def test_can_remove_a_library(self):
        """
        Tests the /documents/<> end point with DELETE to remove a
        library from a user's libraries

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make first library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Delete the library
        url = url_for('documentview',
                      user=stub_user.absolute_uid,
                      library=library_id)
        response = self.client.delete(
            url,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)

        # Check its deleted
        url = url_for('userview')
        with MockEmailService(stub_user, end_type='uid'):
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertTrue(len(response.json['libraries']) == 0,
                        response.json)

        # Check there is no document content
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService() as BQ, \
                MockEmailService(stub_user, end_type='uid') as ES:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(response.status_code,
                         MISSING_LIBRARY_ERROR['number'],
                         'Received response error: {0}'
                         .format(response.status_code))
        self.assertEqual(response.json['error'],
                         MISSING_LIBRARY_ERROR['body'])

        # Try to delete even though it does not exist, this should return
        # some errors from the server
        url = url_for('documentview', library=library_id)

        response = self.client.delete(
            url,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, MISSING_LIBRARY_ERROR['number'])
        self.assertEqual(response.json['error'],
                         MISSING_LIBRARY_ERROR['body'])

    def test_user_without_permission_cannot_access_private_library(self):
        """
        Tests the /libraries/<> end point to ensure that a user cannot
        access the library unless they have permissions

        :return: no return
        """

        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_library = LibraryShop()

        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers,
        )
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Request from user 2 to see the library should be refused if user 2
        # does not have the permissions
        # Check the library is empty
        url = url_for('libraryview', library=library_id)

        with MockSolrBigqueryService(number_of_bibcodes=0) as BQ, \
                MockEmailService(stub_user_1, end_type='uid') as ES:
            response = self.client.get(
                url,
                headers=stub_user_2.headers
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

    def test_can_add_read_permissions(self):
        """
        Tests that a user can add read permissions to another user for one of
        their libraries.

        :return: no return
        """

        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_library = LibraryShop()

        # Initialise HTTPretty for the URL for the API
        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers
        )
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Make a library for user 2 so that we have an account
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_2.headers
        )
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # Add the permissions for user 2
        url = url_for('permissionview', library=library_id)

        # This requires communication with the API
        with MockEmailService(stub_user_2):
            response = self.client.post(
                url,
                data=stub_user_2.permission_view_post_data_json({'read': True, 'write': False, 'admin': False, 'owner': False}),
                headers=stub_user_1.headers
            )
        self.assertEqual(response.status_code, 200)

        # The user can now access the content of the library
        url = url_for('libraryview', library=library_id)
        with MockSolrBigqueryService(number_of_bibcodes=0) as BQ, \
                MockEndPoint([stub_user_1, stub_user_2]) as ES:
            response = self.client.get(
                url,
                headers=stub_user_2.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue('documents' in response.json)

    def test_cannot_change_permission_without_permission(self):
        """
        Test that a user without permissions cannot alter the permissions
        of a library.
        :return:
        """

        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_library = LibraryShop()

        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers
        )
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Make a library for user 2 so that we have an account
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_2.headers
        )
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)

        # User 2 with no permissions tries to modify user 1
        url = url_for('permissionview', library=library_id)
        # This requires communication with the API
        # User requesting: user 2 that has no permissions
        # To modify: user 2 is trying to modify user 1, which is the owner of
        # the library
        # E-mail requested should correspond to the owner of the library,
        # which in this case is user 1
        with MockEmailService(stub_user_1):
            response = self.client.post(
                url,
                data=stub_user_1.permission_view_post_data_json({'read': True, 'write': False, 'admin': False, 'owner': False}),
                headers=stub_user_2.headers
            )

        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

    def test_owner_cannot_edit_owner(self):
        """
        Test that the owner of a library cannot modify their own permissions,
        such as read, write, etc., otherwise it would allow orphan libraries

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_library = LibraryShop()

        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Owner tries to modify owner permissions
        url = url_for('permissionview', library=library_id)
        for permission_type in ['read', 'write', 'admin', 'owner']:
            # E-mail requested should correspond to user
            with MockEmailService(stub_user):
                response = self.client.post(
                    url,
                    data=stub_user.permission_view_post_data_json(
                        {permission_type: False}
                    ),
                    headers=stub_user.headers
                )

            self.assertEqual(response.status_code,
                             NO_PERMISSION_ERROR['number'])
            self.assertEqual(response.json['error'],
                             NO_PERMISSION_ERROR['body'])

    def test_admin_cannot_edit_any_owner_permission(self):
        """
        Test that an admin cannot edit the owner value of a library.

        :return: no return
        """

        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_user_3 = UserShop()
        stub_library = LibraryShop()

        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Give user 2 admin permissions
        # This requires communication with the API
        # User requesting: user 1 owner of the library
        # To modify: user 1 is trying to modify user 2
        # E-mail requested should correspond to user 2
        url = url_for('permissionview', library=library_id)
        with MockEmailService(stub_user_2):
            response = self.client.post(
                url,
                data=stub_user_2.permission_view_post_data_json({'read': False, 'write': False, 'admin': True, 'owner': False}),
                headers=stub_user_1.headers
            )
        self.assertEqual(response.status_code, 200)

        # Now user 2 tries to give user 3 owner permissions. Even though user 2
        # has admin permissions, they should not be able to modify the owner.
        # E-mail requested should correspond to user 3
        url = url_for('permissionview', library=library_id)
        with MockEmailService(stub_user_3):
            response = self.client.post(
                url,
                data=stub_user_3.permission_view_post_data_json({'read': False, 'write': False, 'admin': False, 'owner': True}),
                headers=stub_user_2.headers
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

    def test_give_permissions_to_a_user_not_in_the_service_database(self):
        """
        This tests that a user that exists in the API but not the service
        database, can have permissions changed.

        :return: no return
        """

        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_library = LibraryShop()

        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers
        )

        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Add the permissions for user 2
        url = url_for('permissionview', library=library_id)
        for permission_type in ['read', 'write', 'admin']:
            with MockEmailService(stub_user_2):
                response = self.client.post(
                    url,
                    data=stub_user_2.permission_view_post_data_json(
                        {permission_type: True}
                    ),
                    headers=stub_user_1.headers
                )
            self.assertEqual(response.status_code, 200)

    def test_user_cannot_edit_library_without_permission(self):
        """
        Tests that only a user with correct edit permissions can edit the
        content of a library.

        :return:
        """

        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_library = LibraryShop()

        # Make a library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers
        )
        self.assertEqual(response.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # See if a random user can edit content of the library
        # Add to the library
        url = url_for('documentview', library=library_id)
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add'))) as SQ:
            response = self.client.post(
                url,
                data=stub_library.document_view_post_data_json('add'),
                headers=stub_user_2.headers
            )
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])

        # Check the owner can add/remove content
        with MockSolrQueryService(canonical_bibcode = json.loads(stub_library.document_view_post_data_json('add')).get('bibcode')) as SQ:
            response = self.client.post(
                url,
                data=stub_library.document_view_post_data_json('add'),
                headers=stub_user_1.headers
            )
        print(response.json)
        self.assertEqual(response.json['number_added'],
                                       len(stub_library.bibcode))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_users_can_access_public_libraries(self):
        """
        Tests that a user with no ties to the ADS can view libraries that
        are public

        :return: no return
        """
        # Stub data
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()
        stub_library = LibraryShop(public=True)

        # Make a library for a given user, user 1
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user_1.headers
        )
        self.assertEqual(response.status_code, 200)

        for key in ['name', 'id']:
            self.assertIn(key, response.json)
        # Get the library ID
        library_id = response.json['id']

        # Request from user 2
        # Given it is public, should be able to view it
        url = url_for('libraryview', library=library_id)
        with MockEndPoint([stub_user_1, stub_user_2]) as ES,\
                MockSolrBigqueryService(number_of_bibcodes=0) as BQ:
            response = self.client.get(
                url,
                headers=stub_user_2.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('documents', response.json)

    def test_cannot_delete_a_library_if_not_owner(self):
        """
        Tests the /documents/<> end point with DELETE to remove a
        library from a user's libraries

        :return: no return
        """

        # Load stub data
        stub_owner = UserShop(name='owner')
        stub_none = UserShop(name='none')
        stub_reader = UserShop(name='reader')
        stub_editor = UserShop(name='editor')
        stub_admin = UserShop(name='admin')
        stub_library = LibraryShop(public=False)

        # Makes the library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_owner.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200, response)
        self.assertTrue('name' in response.json)
        self.assertTrue(response.json['name'] == stub_library.name)

        # Give the correct permissions to each user
        url = url_for('permissionview', library=library_id)
        for stub_user, permission in [[stub_reader, 'read'],
                                      [stub_editor, 'write'],
                                      [stub_admin, 'admin']]:
            with MockEmailService(stub_user):
                response = self.client.post(
                    url,
                    data=stub_user.permission_view_post_data_json(
                        {permission: True}
                    ),
                    headers=stub_owner.headers
                )
            self.assertEqual(response.status_code, 200)

        # The following users try to the delete the library, and fail:
        # reader, editor, admin
        url = url_for('documentview', library=library_id)
        for stub_user in [stub_none, stub_reader, stub_editor, stub_admin]:
            response = self.client.delete(
                url,
                headers=stub_user.headers
            )
            self.assertEqual(response.status_code,
                             NO_PERMISSION_ERROR['number'],
                             'User: {0}'.format(stub_user.name))
            self.assertEqual(response.json['error'],
                             NO_PERMISSION_ERROR['body'])

    def test_when_no_post_content_or_empty_when_creating_library(self):
        """
        Tests that when a user posts no content or empty name and description
        for creating a library, that the wanted behaviour happens.

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
        self.assertEqual(response.status_code, 200)
        self.assertEqual('{0} 1'.format(DEFAULT_LIBRARY_NAME_PREFIX),
                         response.json['name'])
        self.assertEqual(DEFAULT_LIBRARY_DESCRIPTION,
                         response.json['description'])

        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_mary.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual('{0} 2'.format(DEFAULT_LIBRARY_NAME_PREFIX),
                         response.json['name'])
        self.assertEqual(DEFAULT_LIBRARY_DESCRIPTION,
                         response.json['description'])

    def test_can_update_name_and_description_with_permissions(self):
        """
        Tests that when a user posts no content or empty name and description
        for creating a library, that the wanted behaviour happens.

        :return: no return
        """

        # Stub data
        user_mary = UserShop()
        stub_library = LibraryShop(name='', description='', public=False)

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
        self.assertEqual(response.status_code, 200)
        self.assertEqual('{0} 1'.format(DEFAULT_LIBRARY_NAME_PREFIX),
                         response.json['name'])
        self.assertEqual(DEFAULT_LIBRARY_DESCRIPTION,
                         response.json['description'])

        # Change the library name
        new_name = 'New name'
        new_description = 'New description'
        new_publicity = True

        library_data = \
            stub_library.document_view_put_data(name=new_name)
        library_data.pop('description')
        library_data.pop('public')
        library_data = json.dumps(library_data)

        url = url_for('documentview', library=library_id)
        response = self.client.put(
            url,
            data=library_data,
            headers=user_mary.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name,
                         response.json['name'],
                         response.json)

        # Change the library description
        library_data = \
            stub_library.document_view_put_data(description=new_description)
        library_data.pop('name')
        library_data.pop('public')
        library_data = json.dumps(library_data)

        response = self.client.put(
            url,
            data=library_data,
            headers=user_mary.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_description,
                         response.json['description'])

        # Change the publicity
        library_data = \
            stub_library.document_view_put_data(public=new_publicity)
        library_data.pop('name')
        library_data.pop('description')
        library_data = json.dumps(library_data)

        url = url_for('documentview', library=library_id)
        response = self.client.put(
            url,
            data=library_data,
            headers=user_mary.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_publicity,
                         response.json['public'])

        # Update both at the same time
        new_name += ' new'
        new_description += ' description'
        new_publicity = False
        response = self.client.put(
            url,
            data=stub_library.document_view_put_data_json(
                name=new_name,
                description=new_description,
                public=new_publicity
            ),
            headers=user_mary.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name,
                         response.json['name'])
        self.assertEqual(new_description,
                         response.json['description'])
        self.assertEqual(new_publicity,
                         response.json['public'])

    def test_can_update_library_with_permissions_admin(self):
        """
        Tests that when a user updates the name it is possible when the user
        has admin permissions.

        :return: no return
        """

        # Stub data
        user_mary = UserShop()
        user_admin = UserShop()
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
        self.assertEqual(response.status_code, 200)
        self.assertEqual('{0} 1'.format(DEFAULT_LIBRARY_NAME_PREFIX),
                         response.json['name'])
        self.assertEqual(DEFAULT_LIBRARY_DESCRIPTION,
                         response.json['description'])

        # Allocate admin permissions
        url = url_for('permissionview', library=library_id)
        with MockEmailService(user_admin):
            response = self.client.post(
                url,
                data=user_admin.permission_view_post_data_json({'read': False, 'write': False, 'admin': True, 'owner': False}),
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, 200)

        # Change the library name
        new_name = 'New name'
        new_description = 'New description'
        new_publicity = True

        url = url_for('documentview', library=library_id)
        response = self.client.put(
            url,
            data=stub_library.document_view_put_data_json(
                name=new_name,
                description=new_description
            ),
            headers=user_admin.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name,
                         response.json['name'])
        self.assertEqual(new_description,
                         response.json['description'])

    def test_cannot_update_name_with_name_that_exists(self):
        """
        Should not be able to update the library with a name that already
        exists for one of the users own libraries.

        :return: no return
        """

        # Stub data
        same_name = 'Same name'
        user_mary = UserShop()
        stub_library = LibraryShop(name=same_name, description='')

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
        self.assertEqual(response.status_code, 200)
        self.assertEqual(same_name,
                         response.json['name'])
        self.assertEqual(DEFAULT_LIBRARY_DESCRIPTION,
                         response.json['description'])

        # Try to update the name with the same name
        url = url_for('documentview', library=library_id)
        response = self.client.put(
            url,
            data=stub_library.document_view_put_data_json(name=same_name),
            headers=user_mary.headers
        )

        self.assertEqual(response.status_code,
                         DUPLICATE_LIBRARY_NAME_ERROR['number'])
        self.assertEqual(response.json['error'],
                         DUPLICATE_LIBRARY_NAME_ERROR['body'])

    def test_return_error_when_user_email_not_exist_api(self):
        """
        When the user does not exist the API database, the web service should
        pass on the message

        :return: no return
        """

        # Stub data
        stub_user = UserShop()
        stub_random = UserShop(name='fail')
        stub_library = LibraryShop(name='', description='')

        # Fake library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200)

        # Allocate permissions
        url = url_for('permissionview', library=library_id)
        with MockEmailService(stub_random):
            response = self.client.post(
                url,
                data=stub_random.permission_view_post_data_json({'read': True, 'write': False, 'admin': False, 'owner': False}),
                headers=stub_user.headers
            )

        self.assertEqual(response.status_code,
                         API_MISSING_USER_EMAIL['number'])
        self.assertEqual(response.json['error'],
                         API_MISSING_USER_EMAIL['body'])

    def test_return_error_when_user_uid_not_exist_api(self):
        """
        When the user does not exist in the API database, the web service
        should pass on the message.

        :return: no return
        """

        # Stub data
        stub_user = UserShop(name='fail')
        stub_library = LibraryShop()

        # Make the library
        url = url_for('userview')

        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=stub_user.headers
        )
        self.assertEqual(response.status_code, 200)

        # Check the library exists in the database
        url = url_for('userview')

        with MockEmailService(stub_user, end_type='uid'):
            response = self.client.get(
                url,
                headers=stub_user.headers
            )

        self.assertTrue(
            response.json['libraries'][0]['owner'] == 'Not available'
        )

    def test_cannot_update_name_and_description_without_permissions(self):
        """
        Tests that users who have read, write, or no permissions, can not
        update a library they can see.

        :return: no return
        """

        # Stub data
        user_mary = UserShop()
        user_random = UserShop()
        user_reader = UserShop()
        user_write = UserShop()
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
        self.assertEqual(response.status_code, 200)
        self.assertEqual('{0} 1'.format(DEFAULT_LIBRARY_NAME_PREFIX),
                         response.json['name'])
        self.assertEqual(DEFAULT_LIBRARY_DESCRIPTION,
                         response.json['description'])

        # Allocate permissions
        url = url_for('permissionview', library=library_id)
        for user, permission in [[user_reader, 'read'], [user_write, 'write']]:
            with MockEmailService(user):
                response = self.client.post(
                    url,
                    data=user.permission_view_post_data_json({permission: True}),
                    headers=user_mary.headers
                )
            self.assertEqual(response.status_code, 200)

        # Change the library name
        for user in [user_random, user_reader, user_write]:
            url = url_for('documentview', library=library_id)
            new_name = 'New name'
            response = self.client.put(
                url,
                data=stub_library.document_view_put_data_json('name',
                                                              new_name),
                headers=user.headers
            )
            self.assertEqual(response.status_code,
                             NO_PERMISSION_ERROR['number'])
            self.assertEqual(response.json['error'],
                             NO_PERMISSION_ERROR['body'])

    def test_can_find_out_permissions_of_a_library_if_owner_or_admin(self):
        """
        Tests the permissions/<> GET end point to make sure the permissions
        are returned. This should return if the permissions are of the user are
        owner or admin.

        :return: no return
        """
        # Stub data
        user_owner = UserShop()
        user_admin = UserShop()
        stub_library = LibraryShop()

        # Make a library with the owner user
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_owner.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200)

        # Give the user_admin 'admin' permissions
        with MockEmailService(user_admin):
            url = url_for('permissionview', library=library_id)
            response = self.client.post(
                url,
                data=user_admin.permission_view_post_data_json({'read': False, 'write': False, 'admin': True, 'owner': False}),
                headers=user_owner.headers
            )
        self.assertEqual(response.status_code, 200)

        # Try and get the permissions with both of the users
        with MockEndPoint([user_owner, user_admin]):
            for stub_user in [user_owner, user_admin]:
                response = self.client.get(
                    url,
                    headers=stub_user.headers
                )

                self.assertEqual(response.status_code, 200)
                self.assertIn(user_owner.email, response.json[0].keys())
                self.assertIn(user_admin.email, response.json[1].keys())
                self.assertEqual(['owner'], response.json[0][user_owner.email])
                self.assertEqual(['admin'], response.json[1][user_admin.email])

    def test_cannot_find_permissions_of_a_library_if_not_owner_or_admin(self):
        """
        Tests the permissions/<> GET end point to make sure the permissions
        are not returned if the permissions of the user are not owner or admin.

        :return: no return
        """
        # Stub data
        user_read = UserShop()
        user_write = UserShop()
        user_owner = UserShop()
        stub_library = LibraryShop()

        # Make a library with the owner user
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_owner.headers
        )
        library_id = response.json['id']
        self.assertEqual(response.status_code, 200)

        # Give the user_read and user_write 'read' and 'write' permissions
        with MockEmailService(user_read):
            url = url_for('permissionview', library=library_id)
            response = self.client.post(
                url,
                data=user_read.permission_view_post_data_json({'read': True, 'write': False, 'admin': False, 'owner': False}),
                headers=user_owner.headers
            )
        self.assertEqual(response.status_code, 200)

        with MockEmailService(user_write):
            url = url_for('permissionview', library=library_id)
            response = self.client.post(
                url,
                data=user_write.permission_view_post_data_json({'read': False, 'write': True, 'admin': False, 'owner': False}),
                headers=user_owner.headers
            )
        self.assertEqual(response.status_code, 200)

        # Try and get the permissions with both of the users
        user_list = [user_read, user_write]
        with MockEndPoint([user_list[0], user_list[1], user_owner]):
            for stub_user in user_list:
                response = self.client.get(
                    url,
                    headers=stub_user.headers
                )
                self.assertEqual(response.status_code,
                                 NO_PERMISSION_ERROR['number'])
                self.assertEqual(response.json['error'],
                                 NO_PERMISSION_ERROR['body'])

    def test_missing_user_id_raises_error(self):
        """
        Tests that a KeyError is raised if the header does not contain the
        user id of the requesting user

        :return: no return
        """

        get_end_points = ['userview', 'libraryview', 'permissionview']
        post_end_points = ['userview', 'documentview', 'permissionview',
                           'transferview', 'operationsview']
        put_end_points = ['documentview']
        delete_end_points = ['documentview']

        # GETs
        for end_points in get_end_points:
            url = url_for(end_points, library='1')
            response = self.client.get(
                url
            )
            self.assertEqual(response.status_code,
                             MISSING_USERNAME_ERROR['number'])

        # POSTs
        for end_points in post_end_points:
            url = url_for(end_points, library='1')
            response = self.client.post(
                url,
                data="{}"
            )
            self.assertEqual(response.status_code,
                             MISSING_USERNAME_ERROR['number'])

        # PUTs
        for end_points in put_end_points:
            url = url_for(end_points, library='1')
            response = self.client.post(
                url,
                data="{}"
            )
            self.assertEqual(response.status_code,
                             MISSING_USERNAME_ERROR['number'])

        # DELETEs
        for end_points in delete_end_points:
            url = url_for(end_points, library='1')
            response = self.client.delete(
                url
            )
            self.assertEqual(response.status_code,
                             MISSING_USERNAME_ERROR['number'])

    def test_can_transfer_a_library(self):
        """
        Tests that a user can transfer a library to another user.

        :return: no return
        """
        user_owner = UserShop()
        user_new_owner = UserShop()
        stub_library = LibraryShop()

        # Dave has a big library that he has maintained for many years
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_owner.headers
        )
        self.assertEqual(response.status_code, 200, response)
        library_id_dave = response.json['id']

        # Transfer it to a non-existent user
        with MockEmailService(user_new_owner):
            url = url_for('transferview', library=library_id_dave)
            response = self.client.post(
                url,
                data=user_new_owner.transfer_view_post_data_json(),
                headers=user_owner.headers
            )
        self.assertEqual(response.status_code, 200)

        # Check the permissions
        with MockEndPoint([user_owner, user_new_owner]):
            url = url_for('permissionview', library=library_id_dave)
            response = self.client.get(
                url,
                headers=user_new_owner.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json) == 1)
        self.assertEqual(['owner'], response.json[0][user_new_owner.email])

    def test_cannot_transfer_a_library_if_user_non_existent(self):
        """
        Tests that you cannot transfer a library if the other user does not
        exist.

        :return: no return
        """
        user_dave = UserShop()
        user_random = UserShop(name='fail')
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

        # Transfer it to a non-existent user
        with MockEmailService(user_random):
            url = url_for('transferview', library=library_id_dave)
            response = self.client.post(
                url,
                data=user_random.transfer_view_post_data_json(),
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code,
                         API_MISSING_USER_EMAIL['number'])
        self.assertEqual(response.json['error'],
                         API_MISSING_USER_EMAIL['body'])

    def test_cannot_transfer_a_library_if_not_owner(self):
        """
        Tests that you cannot transfer a library if the other user does not
        exist.

        :return: no return
        """
        user_owner = UserShop()
        user_random = UserShop()
        stub_library = LibraryShop()

        # Dave has a big library that he has maintained for many years
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_owner.headers
        )
        self.assertEqual(response.status_code, 200, response)
        library_id_dave = response.json['id']

        # Transfer it to a non-existent user
        with MockEmailService(user_random):
            url = url_for('transferview', library=library_id_dave)
            response = self.client.post(
                url,
                data=user_random.transfer_view_post_data_json(),
                headers=user_random.headers
            )
        self.assertEqual(response.status_code,
                         NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'],
                         NO_PERMISSION_ERROR['body'])

    def test_when_user_has_no_ads_classic_credentials(self):
        """
        Test the scenario where the user accessing classic view has no ADS
        credentials associated to their account
        """
        user = UserShop()
        url = url_for('classicview')

        with MockClassicService(status=NO_CLASSIC_ACCOUNT['number'],
                                body={'error': NO_CLASSIC_ACCOUNT['body']}):
            response = self.client.get(url, headers=user.headers)

        self.assertEqual(response.status_code, NO_CLASSIC_ACCOUNT['number'])
        self.assertEqual(response.json['error'], NO_CLASSIC_ACCOUNT['body'])

    def test_when_user_has_classic_credentials_and_library_returns(self):
        """
        Tests that when you have ADS Credentials, it stores the libraries from
        your ADS Classic account
        """
        stub_user = UserShop()
        stub_library = LibraryShop()
        url = url_for('classicview')

        with MockClassicService(status=200, libraries=[stub_library]):
            response = self.client.get(url, headers=stub_user.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json[0]['action'], 'created')
        self.assertEqual(response.json[0]['num_added'], len(stub_library.get_bibcodes()))

        # Check they were stored
        url = url_for('userview')
        with MockEmailService(stub_user, end_type='uid'):
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertTrue(len(response.json['libraries']) > 0,
                        msg='No libraries returned: {}'.format(response.json))
        self.assertEqual(response.json['libraries'][0]['name'], stub_library.name)
        self.assertEqual(response.json['libraries'][0]['description'],
                         stub_library.description)
        library_id = response.json['libraries'][0]['id']

        url = url_for('libraryview', library=library_id)
        with MockEmailService(stub_user, end_type='uid') as ES, \
                MockSolrBigqueryService(canonical_bibcode=stub_library.bibcode) as BQ:
            response = self.client.get(
                url,
                headers=stub_user.headers
            )
        self.assertEqual(
            sorted(stub_library.get_bibcodes()),
            response.json['documents'],
            msg='Bibcodes received do not match: {} != {}'
                .format(stub_library.bibcode, response.json['documents'])
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
