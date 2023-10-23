"""
Functional test

Clasic User Epic

Storyboard is defined within the comments of the program itself
"""

import unittest

from httmock import HTTMock, urlmatch
from flask import url_for
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop
from biblib.tests.base import TestCaseDatabase, MockEmailService, \
    MockSolrBigqueryService, MockEndPoint, MockClassicService
from biblib.views.http_errors import NO_CLASSIC_ACCOUNT
from config import BIBLIB_CLASSIC_SERVICE_URL


@urlmatch(netloc=r'(.*\.)?{}.*'.format(BIBLIB_CLASSIC_SERVICE_URL))
def classic_service_404(url, request):
    return {
        'status_code': NO_CLASSIC_ACCOUNT['number'],
        'content': NO_CLASSIC_ACCOUNT['body']
    }


class TestClassicUserEpic(TestCaseDatabase):
    """
    Base class used to test the Classic User Epic
    """

    def test_classic_user_epic(self):
        """
        Carries out the epic 'Classic User', where a user that previously used
        ADS Classic has come to the new interface and has decided to import
        contents from ADS Classic. They have not yet made any libraries, and
        have not set up their ADS Classic account in BB yet.
        """
        # Stub data
        user_gpa = UserShop()
        stub_library_1 = LibraryShop(public=True)
        stub_library_2 = LibraryShop(public=True)

        # Gpa navigates to the libraries page and tries to import their libraries
        # from ADS Classic. However, Gpa has not setup any ADS Credentials
        url = url_for('classicview')
        with MockClassicService(status=NO_CLASSIC_ACCOUNT['number'], body={'error': NO_CLASSIC_ACCOUNT['body']}):
            response = self.client.get(url, headers=user_gpa.headers)
        self.assertEqual(response.status_code, NO_CLASSIC_ACCOUNT['number'])
        self.assertEqual(response.json['error'], NO_CLASSIC_ACCOUNT['body'])

        # They visit the relevant page and setup their ADS Classic credentials
        # They then try again to import the libraries from ADS Classic
        with MockClassicService(status=200, libraries=[stub_library_1, stub_library_2]):
            response = self.client.get(url, headers=user_gpa.headers)

        self.assertEqual(response.status_code, 200)

        # Gpa visit the libraries pages to check that it was in fact imported
        url = url_for('userview')
        with MockEmailService(user_gpa, end_type='uid'):
            response = self.client.get(
                url,
                headers=user_gpa.headers
            )
        self.assertEqual(response.json['libraries']['my_libraries'][0]['name'], stub_library_1.name)
        self.assertEqual(response.json['libraries']['my_libraries'][1]['name'], stub_library_2.name)
        library_id_1 = response.json['libraries']['my_libraries'][0]['id']
        library_id_2 = response.json['libraries']['my_libraries'][1]['id']

        # Gpa clicks the library page and checks that the content is as expected
        for library_id, stub_library in [[library_id_1, stub_library_1], [library_id_2, stub_library_2]]:
            url = url_for('libraryview', library=library_id)
            with MockSolrBigqueryService(canonical_bibcode=stub_library.get_bibcodes()) as BQ, \
                    MockEndPoint([user_gpa]) as EP:
                response = self.client.get(
                    url,
                    headers=user_gpa.headers
                )
            self.assertTrue(len(response.json['documents']) == len(stub_library.get_bibcodes()), response.json)
            self.assertEqual(stub_library.get_bibcodes(), response.json['documents'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
