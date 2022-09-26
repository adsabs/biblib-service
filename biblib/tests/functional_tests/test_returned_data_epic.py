"""
Functional test

Returned Data Epic

Storyboard is defined within the comments of the program itself
"""

import time
import unittest
from datetime import datetime, timedelta
from flask import url_for
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop
from biblib.tests.base import MockEmailService, MockSolrQueryService, TestCaseDatabase, \
    MockSolrBigqueryService, MockEndPoint
import json

class TestReturnedDataEpic(TestCaseDatabase):
    """
    Base class used to test the Big Share Epic
    """

    def test_returned_data_user_view_epic(self):
        """
        Carries out the epic 'Returned Data', for the UserView GET end point

        :return: no return
        """

        # Stub data
        user_dave = UserShop()
        user_mary = UserShop()

        stub_library = LibraryShop()

        # Librarian Dave makes a library (no bibcodes)
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_dave.headers
        )
        self.assertEqual(response.status_code, 200, response)
        library_id_dave = response.json['id']

        # Dave looks at the library from the user view page and checks some
        # of the parameters displayed to him.
        with MockEmailService(user_dave, end_type='uid'):
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertTrue(len(response.json['libraries']) == 1)
        library = response.json['libraries'][0]
        self.assertTrue(library['num_documents'] == 0)
        self.assertTrue(library['num_users'] == 1)
        self.assertTrue(library['permission'] == 'owner')
        self.assertEqual(library['public'], False)
        self.assertEqual(library['owner'], user_dave.email.split('@')[0])
        date_created = datetime.strptime(library['date_created'],
                                         '%Y-%m-%dT%H:%M:%S.%f')
        date_last_modified = datetime.strptime(library['date_last_modified'],
                                               '%Y-%m-%dT%H:%M:%S.%f')
        self.assertAlmostEqual(date_created,
                               date_last_modified,
                               delta=timedelta(seconds=1))

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

        # Dave looks in the library overview and sees that his library size
        # has increased
        url = url_for('userview')
        with MockEmailService(user_dave, end_type='uid'):
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertTrue(len(response.json['libraries'])==1)
        self.assertEqual(response.status_code, 200)
        library = response.json['libraries'][0]
        self.assertTrue(library['num_documents'] == number_of_documents)

        # Dave adds mary so that she can see the library and add content
        url = url_for('permissionview', library=library_id_dave)
        with MockEmailService(user_mary):
            response = self.client.post(
                url,
                data=user_mary.permission_view_post_data_json({'read': False, 'write': False, 'admin': True, 'owner': False}),
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)

        # Mary sees that the number of users of the library has increased by 1
        url = url_for('userview')
        with MockEmailService(user_mary, end_type='uid'):
            with MockEmailService(user_dave, end_type='uid'):
                response = self.client.get(
                    url,
                    headers=user_mary.headers
                )

        library = response.json['libraries'][0]

        self.assertEqual(response.status_code, 200)
        self.assertTrue(library['num_users'] == 2)
        self.assertTrue(library['permission'] == 'admin')

        # Mary adds content to the library
        number_of_documents_second = 1
        for i in range(number_of_documents_second):

            # Stub data
            library = LibraryShop()

            # Add document
            url = url_for('documentview', library=library_id_dave)
            with MockSolrQueryService(canonical_bibcode = json.loads(library.document_view_post_data_json('add')).get('bibcode')) as SQ:
                response = self.client.post(
                    url,
                    data=library.document_view_post_data_json('add'),
                    headers=user_mary.headers
                )
            self.assertEqual(response.json['number_added'],
                             len(library.bibcode))
            self.assertEqual(response.status_code, 200, response)

        # Dave sees that the number of bibcodes has increased and that the
        # last modified date has changed, but the created date has not
        url = url_for('userview')
        with MockEmailService(user_dave, end_type='uid'):
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json['libraries']) == 1)
        self.assertTrue(
            response.json['libraries'][0]['num_documents']
            == (number_of_documents+number_of_documents_second)
        )

        # This is to artificial alter the update time
        time.sleep(1)

        # Dave makes the library public.
        url = url_for('documentview', library=library_id_dave)
        response = self.client.put(
            url,
            data=library.document_view_put_data_json(public=True),
            headers=user_dave.headers
        )
        self.assertEqual(response.status_code, 200)

        # Dave sees that the lock sign from his library page has dissapeared
        url = url_for('userview')
        with MockEmailService(user_dave, end_type='uid'):
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)
        libraries = response.json['libraries']
        self.assertTrue(len(libraries) == 1)
        self.assertTrue(
            libraries[0]['num_documents'] == number_of_documents+1
        )
        self.assertTrue(libraries[0]['public'])
        date_created_2 = datetime.strptime(libraries[0]['date_created'],
                                           '%Y-%m-%dT%H:%M:%S.%f')
        date_last_modified_2 = \
            datetime.strptime(libraries[0]['date_last_modified'],
                              '%Y-%m-%dT%H:%M:%S.%f')
        self.assertEqual(date_created, date_created_2)
        self.assertNotAlmostEqual(date_created_2,
                                  date_last_modified_2,
                                  delta=timedelta(seconds=1))

    def test_returned_data_library_view_epic(self):
        """
        Carries out the epic 'Returned Data', for the LibraryView GET end point
        that should return content similar to the UserView GET end point. This
        ensures the responses are as expected.

        :return: no return
        """

        # Stub data
        user_dave = UserShop()
        user_mary = UserShop()

        stub_library = LibraryShop()

        # Librarian Dave makes a library (no bibcodes)
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library.user_view_post_data_json,
            headers=user_dave.headers
        )
        self.assertEqual(response.status_code, 200, response)
        library_id_dave = response.json['id']

        # Dave looks at the library from the user view page and checks some
        # of the parameters displayed to him.
        with MockSolrBigqueryService(canonical_bibcode=stub_library.bibcode) \
                as BQ, MockEndPoint([user_dave]) as EP:
            url = url_for('libraryview', library=library_id_dave)
            response = self.client.get(
                url,
                headers=user_dave.headers
            )

        for key in ['documents', 'solr', 'metadata']:
            self.assertIn(key, response.json)

        documents = response.json['documents']
        solr = response.json['solr']
        metadata = response.json['metadata']
        self.assertTrue(metadata['num_documents'] == 0)
        self.assertTrue(metadata['num_users'] == 1)
        self.assertTrue(metadata['permission'] == 'owner')
        self.assertEqual(metadata['public'], False)
        self.assertEqual(metadata['owner'], user_dave.email.split('@')[0])
        date_created = datetime.strptime(metadata['date_created'],
                                         '%Y-%m-%dT%H:%M:%S.%f')
        date_last_modified = datetime.strptime(metadata['date_last_modified'],
                                               '%Y-%m-%dT%H:%M:%S.%f')
        self.assertAlmostEqual(date_created,
                               date_last_modified,
                               delta=timedelta(seconds=1))

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

            documents.append(library.get_bibcodes()[0])

        # Dave looks in the library overview and sees that his library size
        # has increased
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(canonical_bibcode=documents) as BQ, \
                MockEndPoint([user_dave]) as EP:
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.json['metadata']['num_documents'] == number_of_documents
        )

        # Dave adds mary so that she can see the library and add content
        url = url_for('permissionview', library=library_id_dave)
        with MockEmailService(user_mary):
            response = self.client.post(
                url,
                data=user_mary.permission_view_post_data_json({'read': False, 'write': False, 'admin': True, 'owner': False}),
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)

        # Mary sees that the number of users of the library has increased by 1
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(canonical_bibcode=documents) as BQ,\
                MockEndPoint([user_mary, user_dave]) as EP:
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, 200)
        library = response.json['metadata']
        self.assertTrue(library['num_users'] == 2)
        self.assertTrue(library['permission'] == 'admin')

        # Mary adds content to the library
        number_of_documents_second = 1
        for i in range(number_of_documents_second):

            # Stub data
            library = LibraryShop()

            # Add document
            url = url_for('documentview', library=library_id_dave)
            with MockSolrQueryService(canonical_bibcode = json.loads(library.document_view_post_data_json('add')).get('bibcode')) as SQ:
                response = self.client.post(
                    url,
                    data=library.document_view_post_data_json('add'),
                    headers=user_mary.headers
                )
            self.assertEqual(response.json['number_added'],
                             len(library.bibcode))
            self.assertEqual(response.status_code, 200, response)
            documents.append(library.get_bibcodes()[0])

        # Dave sees that the number of bibcodes has increased and that the
        # last modified date has changed, but the created date has not
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(canonical_bibcode=documents) as BQ, \
                MockEndPoint([user_dave, user_mary]) as EP:
            response = self.client.get(
                url,
                headers=user_dave.headers
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.json['metadata']['num_documents']
            == (number_of_documents+number_of_documents_second)
        )

        # This is to artificial alter the update time
        time.sleep(1)

        # Dave makes the library public.
        url = url_for('documentview', library=library_id_dave)
        response = self.client.put(
            url,
            data=library.document_view_put_data_json(public=True),
            headers=user_dave.headers
        )
        self.assertEqual(response.status_code, 200)

        # Dave sees that the lock sign from his library page has dissapeared
        url = url_for('libraryview', library=library_id_dave)
        with MockSolrBigqueryService(canonical_bibcode=documents) as BQ,\
                MockEndPoint([user_dave, user_mary]) as EP:
            response = self.client.get(
                url,
                headers=user_dave.headers
            )

        libraries = response.json['metadata']
        self.assertTrue(
            libraries['num_documents'] == number_of_documents+1
        )
        self.assertTrue(libraries['public'])
        date_created_2 = datetime.strptime(libraries['date_created'],
                                           '%Y-%m-%dT%H:%M:%S.%f')
        date_last_modified_2 = \
            datetime.strptime(libraries['date_last_modified'],
                              '%Y-%m-%dT%H:%M:%S.%f')
        self.assertEqual(date_created, date_created_2)
        self.assertNotAlmostEqual(date_created_2,
                                  date_last_modified_2,
                                  delta=timedelta(seconds=1))


if __name__ == '__main__':
    unittest.main(verbosity=2)