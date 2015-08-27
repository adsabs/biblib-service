"""
Functional test

Anonymous Epic

Storyboard is defined within the comments of the program itself
"""

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import unittest
from views.http_errors import NO_PERMISSION_ERROR
from flask import url_for
from tests.stubdata.stub_data import UserShop, LibraryShop
from tests.base import TestCaseDatabase, MockSolrBigqueryService, MockEndPoint

class TestAnonymousEpic(TestCaseDatabase):
    """
    Base class used to test the Big Share Admin Epic
    """

    def test_anonymous_epic(self):
        """
        Carries out the epic 'Anonymous', where a user tries to access a
        private library and also a public library. The user also (artificial)
        tries to access any other endpoints that do not have any scopes set

        :return: no return
        """

        # Define two sets of stub data
        # user: who makes a library (e.g., Dave the librarian)
        # anon: someone using the BBB client
        user_anonymous = UserShop()
        user_dave = UserShop()
        library_dave_private = LibraryShop(public=False)
        library_dave_public = LibraryShop(public=True)

        # Dave makes two libraries
        # One private library
        # One public library
        url = url_for('userview')
        response = self.client.post(
            url,
            data=library_dave_private.user_view_post_data_json,
            headers=user_dave.headers
        )
        library_id_private = response.json['id']
        self.assertEqual(response.status_code, 200, response)

        response = self.client.post(
            url,
            data=library_dave_public.user_view_post_data_json,
            headers=user_dave.headers
        )
        library_id_public = response.json['id']
        self.assertEqual(response.status_code, 200, response)

        # Anonymous user tries to access the private library. But cannot.
        url = url_for('libraryview', library=library_id_private)
        with MockSolrBigqueryService(number_of_bibcodes=0) as BQ, \
                MockEndPoint([user_dave, user_anonymous]) as EP:
            response = self.client.get(
                url,
                headers=user_anonymous.headers
            )
        self.assertEqual(response.status_code, NO_PERMISSION_ERROR['number'])
        self.assertEqual(response.json['error'], NO_PERMISSION_ERROR['body'])

        # Anonymous user tries to access the public library. And can.
        url = url_for('libraryview', library=library_id_public)
        with MockSolrBigqueryService(number_of_bibcodes=0) as BQ, \
                MockEndPoint([user_dave, user_anonymous]) as EP:
            response = self.client.get(
                url,
                headers=user_anonymous.headers
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn('documents', response.json)

    def test_scopes(self):
        """
        Separately test the number of scopes that are scopeless. This will only
        fail during staging when the scopes are all set to be open. In the
        production system, there is only once end point that will be scopelss.

        :return: no return
        """
        response = self.client.get('/resources')
        end_points = []
        for end_point in response.json.keys():

            if len(response.json[end_point]['scopes']) == 0:
                end_points.append(end_point)

        self.assertEqual(1, len(end_points))
        self.assertEqual('/libraries/<string:library>', end_points[0])

if __name__ == '__main__':
    unittest.main(verbosity=2)
