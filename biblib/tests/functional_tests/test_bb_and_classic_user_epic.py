"""
Functional test

Bumblebee and Clasic User Epic

Storyboard is defined within the comments of the program itself
"""

import unittest

from httmock import HTTMock, urlmatch
from flask import url_for
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop
from biblib.tests.base import TestCaseDatabase, MockEmailService, \
    MockSolrBigqueryService, MockEndPoint, MockClassicService
from biblib.views.http_errors import NO_CLASSIC_ACCOUNT
from biblib.config import BIBLIB_CLASSIC_SERVICE_URL


class TestBBClassicUserEpic(TestCaseDatabase):
    """
    Base class used to test the Bumblebee and Classic User Epic
    """

    def test_bb_classic_user_epic(self):
        """
        Carries out the epic 'Bumblebee and Classic User', where a user that
        comes to the new interface makes some libraries, and has some permission
        to access other libraries from other users.
        The user then imports some libraries from ADS Classic, where some have
        similar names with that of the ones they previously made. It is assumed
        they have already setup their ADS credentials
        """
        # Stub data
        user_gpa = UserShop()
        user_mary = UserShop()
        stub_library_1 = LibraryShop(want_bibcode=True, public=True)
        stub_library_2 = LibraryShop(want_bibcode=True, public=True)

        # Gpa navigates the search pages and adds some bibcodes to some a few
        # libraries.
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library_1.user_view_post_data_json,
            headers=user_gpa.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['bibcode'], stub_library_1.get_bibcodes())

        # A friend adds them to one of their libraries with a similar name
        # # Make library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=stub_library_1.user_view_post_data_json,
            headers=user_mary.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['bibcode'], stub_library_1.get_bibcodes())
        library_id_mary = response.json['id']

        # # Permission to read
        url = url_for('permissionview', library=library_id_mary)
        with MockEmailService(user_gpa):
            response = self.client.post(
                url,
                data=user_gpa.permission_view_post_data_json('read', True),
                headers=user_mary.headers
            )
        self.assertEqual(response.status_code, 200)

        # Gpa imports all libraries from ADS Classic
        stub_library_2.bibcode = stub_library_1.bibcode.copy()
        stub_library_2.bibcode['new bibcode'] = {}

        url = url_for('classicview')
        with MockClassicService(status=200, libraries=[stub_library_2]):
            response = self.client.get(url, headers=user_gpa.headers)
        self.assertEqual(response.status_code, 200)

        # Gpa checks that the libraries were imported, and didn't affect the
        # friends libraries
        library_id_gpa = response.json[0]['library_id']

        url = url_for('libraryview', library=library_id_gpa)
        with MockSolrBigqueryService(
                canonical_bibcode=stub_library_2.get_bibcodes()) as BQ, \
                MockEndPoint([user_gpa]) as EP:
            response = self.client.get(
                url,
                headers=user_gpa.headers
            )
        self.assertIn('new bibcode', response.json['documents'])

        # Check Mary's library
        url = url_for('userview')
        with MockEmailService(user_mary, end_type='uid'):
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        self.assertTrue(len(response.json['libraries']), 1)
        self.assertEqual(response.json['libraries'][0]['name'], stub_library_1.name)

        url = url_for('libraryview', library=library_id_mary)
        with MockSolrBigqueryService(
                canonical_bibcode=stub_library_1.get_bibcodes()) as BQ, \
                MockEndPoint([user_mary]) as EP:
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        self.assertNotIn('new bibcode', response.json['documents'])

        # Gpa then re-imports again by accident, but this is fine as this should
        # be an indempotent process
        url = url_for('classicview')
        with MockClassicService(status=200, libraries=[stub_library_2]):
            response = self.client.get(url, headers=user_gpa.headers)
        self.assertEqual(response.status_code, 200)
        library_id_gpa = response.json[0]['library_id']

        url = url_for('libraryview', library=library_id_gpa)
        with MockSolrBigqueryService(
                canonical_bibcode=stub_library_2.get_bibcodes()) as BQ, \
                MockEndPoint([user_gpa]) as EP:
            response = self.client.get(
                url,
                headers=user_gpa.headers
            )
        self.assertIn('new bibcode', response.json['documents'])

        # Check Mary's library
        url = url_for('userview')
        with MockEmailService(user_mary, end_type='uid'):
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        self.assertTrue(len(response.json['libraries']), 1)
        self.assertEqual(response.json['libraries'][0]['name'], stub_library_1.name)

        url = url_for('libraryview', library=library_id_mary)
        with MockSolrBigqueryService(
                canonical_bibcode=stub_library_1.get_bibcodes()) as BQ, \
                MockEndPoint([user_mary]) as EP:
            response = self.client.get(
                url,
                headers=user_mary.headers
            )
        self.assertNotIn('new bibcode', response.json['documents'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
