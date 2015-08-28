"""
Functional test

Deletion Abuse Epic

Storyboard is defined within the comments of the program itself
"""

import unittest
from flask import url_for
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop
from biblib.tests.base import TestCaseDatabase, MockEmailService
from biblib.views.http_errors import NO_PERMISSION_ERROR

class TestDeletionAbuseEpic(TestCaseDatabase):
    """
    Base class used to test the Deletion Abuse Epic
    """

    def test_deletion_abuse_epic(self):
        """
        Carries out the epic 'Deletion Abuse', where each type of permission
        for a library: None, Read, Write, Admin, try to delete a library and
        get permission denied. The owner then deletes the library, and it is
        successful.

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
                        permission, True
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

        # Owner deletes the library, success
        url = url_for('documentview', library=library_id)
        response = self.client.delete(
            url,
            headers=stub_owner.headers
        )
        self.assertEqual(response.status_code, 200)

        # Checks that it is deleted
        url = url_for('userview')
        response = self.client.get(
            url,
            headers=stub_owner.headers
        )
        self.assertTrue(len(response.json['libraries']) == 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)