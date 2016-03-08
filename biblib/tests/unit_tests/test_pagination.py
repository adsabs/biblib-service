"""
Tests Views of the application
"""

import unittest
import uuid
from flask import url_for
from biblib.models import db, User, Library, Permissions, MutableDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from biblib.views import UserView, LibraryView, DocumentView, PermissionView, \
    BaseView, TransferView, ClassicView
from biblib.views import DEFAULT_LIBRARY_DESCRIPTION
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop
from biblib.utils import get_item
from biblib.biblib_exceptions import BackendIntegrityError, PermissionDeniedError
from biblib.tests.base import TestCaseDatabase, MockEmailService, \
    MockSolrBigqueryService




class TestLibraryViews(TestCaseDatabase):
    """
    Base class to test the Library view for GET
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """

        super(TestLibraryViews, self).__init__(*args, **kwargs)
        self.user_view = UserView
        self.library_view = LibraryView

        self.stub_user = self.stub_user_1 = UserShop()
        self.stub_user_2 = UserShop()

        self.stub_library = LibraryShop()

    def test_library_pagination_default(self):
        """
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        # Give the user and library permissions
        permission = Permissions(owner=True,
                                 read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        #test default pagination

        lib_id=LibraryView.helper_uuid_to_slug(library.id)

        url = url_for('libraryview', library=lib_id)

        r = self.client.get(url, headers={'X-Adsws-Uid': self.stub_user.absolute_uid})

        print r



    def test_library_pagination_user_supplied(self):
        """
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        # Give the user and library permissions
        permission = Permissions(owner=True,
                                 read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        lib_id = LibraryView.helper_uuid_to_slug(library.id)

        #test with user supplied start, rows, sort, and fields
        url = url_for('libraryview', library=lib_id, params={
            'start' : 100,
            'rows' : 100,
            'sort' : 'citation_count desc',
            'fl' : 'bibcode,title,abstract'
        })


        r = self.client.get(url, headers={'X-Adsws-Uid': self.stub_user.absolute_uid})


if __name__ == '__main__':
    unittest.main(verbosity=2)
