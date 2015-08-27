"""
Tests Views of the application
"""

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import unittest
import uuid
from models import db, User, Library, Permissions, MutableDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from views import UserView, LibraryView, DocumentView, PermissionView, \
    BaseView, TransferView
from views import DEFAULT_LIBRARY_DESCRIPTION
from tests.stubdata.stub_data import UserShop, LibraryShop
from utils import get_item
from biblib_exceptions import BackendIntegrityError, PermissionDeniedError
from tests.base import TestCaseDatabase, MockEmailService, \
    MockSolrBigqueryService



class TestBaseViews(TestCaseDatabase):
    """
    Class for testing helper functions that are not neccessarily related to a
    single View and do not need special behaviour related to a view.
    """

    def test_slug_to_uuid(self):
        """
        Test the conversion of a base64 URL encoded string to a UUID behaves as
        expected

        :return:
        """
        input_slug = '878JECDeTX6hoI77gq1Y2Q'
        expected_uuid = 'f3bf0910-20de-4d7e-a1a0-8efb82ad58d9'

        output_uuid = BaseView.helper_slug_to_uuid(input_slug)

        self.assertEqual(expected_uuid, output_uuid)

    def test_uuid_to_slug(self):
        """
        Test the conversion of UUID to a base64 URL encoded string behaves as
        expected

        :return: no return
        """
        input_uuid = uuid.UUID('f3bf0910-20de-4d7e-a1a0-8efb82ad58d9')
        expected_slug = '878JECDeTX6hoI77gq1Y2Q'

        output_slug = BaseView.helper_uuid_to_slug(input_uuid)

        self.assertEqual(expected_slug, output_slug)

    def test_api_email_does_exist(self):
        """
        Tests that the api email resolver returns 200 if e-mail exists

        :return: no return
        """

        stub_random = UserShop()

        # Allocate permissions
        with MockEmailService(stub_random):
            email = BaseView.helper_email_to_api_uid(
                permission_data=stub_random.permission_view_post_data(
                    'read',
                    True
                )
            )
        self.assertEqual(email, stub_random.absolute_uid)

    def test_api_email_does_not_exist(self):
        """
        Tests that the api email resolver raises an exception if the e-mail
        does not exist

        :return: no return
        """

        stub_random = UserShop(name='fail')

        with self.assertRaises(NoResultFound):
            # Allocate permissions
            with MockEmailService(stub_random):
                BaseView.helper_email_to_api_uid(
                    permission_data=stub_random.permission_view_post_data(
                        'read',
                        True
                    )
                )


class TestUserViews(TestCaseDatabase):
    """
    Base class to test the User & Library creation views
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """

        super(TestUserViews, self).__init__(*args, **kwargs)
        self.user_view = UserView()
        self.document_view = DocumentView
        self.permission_view = PermissionView

        # Stub data
        self.stub_user = self.stub_user_1 = UserShop()
        self.stub_user_2 = UserShop()

        self.stub_library = LibraryShop()

    def test_user_creation(self):
        """
        Creates a user and checks it exists within the database

        :return: no return
        """

        # Create a user using the function
        self.user_view.create_user(absolute_uid=self.stub_user_1.absolute_uid)
        # Create another use so that we know it returns a single record
        self.user_view.create_user(absolute_uid=self.stub_user_2.absolute_uid)

        # Check if it really exists in the database
        result = User.query.filter(
            User.absolute_uid == self.stub_user_1.absolute_uid
        ).all()

        # Should contain one result
        self.assertTrue(len(result) == 1)

    def test_user_creation_raises_exception_if_exists(self):
        """
        Creating a user when the user already exists should raise an exception
        that should be handled gracefully in the main section of the code. The
        end point will handle the return to the user.
        :return:
        """

        # Add the user to the database with the uid we do not want repeated
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Now try to add a user with the same uid from the API, it should raise
        # an error
        with self.assertRaises(IntegrityError):
            self.user_view.create_user(
                absolute_uid=self.stub_user.absolute_uid
            )

    def test_user_creation_if_exists(self):
        """
        Check that it knows if a user already exists

        :return: no return
        """

        # Check if the user exists, given we have not added any user in this
        # test, it should return nothing.
        exists = self.user_view.helper_user_exists(
            absolute_uid=self.stub_user.absolute_uid
        )
        self.assertFalse(exists)

        # Add the user with the given UID to the database
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Check that the user exists in the database
        exists = self.user_view.helper_user_exists(
            absolute_uid=self.stub_user.absolute_uid
        )
        self.assertTrue(exists)

    def test_user_can_create_a_library(self):
        """
        Checks that a library is created and exists in the database

        :return:
        """

        # Make the user we want the library to be associated with
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Create the library for the user we created
        library = self.user_view.create_library(
            service_uid=user.id,
            library_data=self.stub_library.user_view_post_data
        )

        self.assertEqual({}, library.bibcode)

        # Check that the library was created with the correct permissions
        result = Permissions.query\
            .filter(User.id == Permissions.user_id)\
            .filter(library.id == Permissions.library_id)\
            .all()

        with self.assertRaises(AttributeError):
            result.library.bibcode

        self.assertTrue(len(result) == 1)

    def test_user_can_create_a_library_passing_bibcodes(self):
        """
        Checks that a library is created and exists in the database. A set of
        bibcodes is sent with the creation.

        :return: no return
        """

        # Temporary stub data
        stub_library = LibraryShop(want_bibcode=True)
        self.assertIn('bibcode', stub_library.user_view_post_data.keys())

        # Make the user we want the library to be associated with
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Create the library for the user we created
        library = self.user_view.create_library(
            service_uid=user.id,
            library_data=stub_library.user_view_post_data
        )

        # Check that the library was created with the correct permissions
        result = Permissions.query\
            .filter(User.id == Permissions.user_id)\
            .filter(library.id == Permissions.library_id)\
            .all()

        library = result[0].library
        self.assertIs(MutableDict, type(library.bibcode), type(library.bibcode))
        self.assertTrue(
            len(library.bibcode) == len(stub_library.bibcode)
        )
        self.assertTrue(len(result) == 1)

    def test_user_cannot_create_a_library_passing_wrong_bibcode_type(self):
        """
        Tests when the user sends the wrong type for the bibcode

        :return: no return
        """

        # Temporary stub data
        stub_library = LibraryShop()

        # Make the user we want the library to be associated with
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        library_data = stub_library.user_view_post_data

        for bib_type in ['string', int(3), float(3.0), dict(test='test')]:

            with self.assertRaises(TypeError):
                library_data['bibcode'] = bib_type
                # Create the library for the user we created
                lib=self.user_view.create_library(
                    service_uid=user.id,
                    library_data=library_data
                )

    def test_user_can_retrieve_library(self):
        """
        Test that we can obtain the libraries that correspond to a given user

        :return: no return
        """

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Make a library that ensures we get one back
        number_of_libs = 2
        for i in range(number_of_libs):
            stub_library = LibraryShop()
            self.user_view.create_library(
                service_uid=user.id,
                library_data=stub_library.user_view_post_data
            )

        # Get the library created
        with MockEmailService(self.stub_user, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user.id,
                absolute_uid=user.absolute_uid
            )
        self.assertEqual(len(libraries), number_of_libs)

    def test_user_can_retrieve_library_when_uid_does_not_exist(self):
        """
        Test that we can obtain the libraries that correspond to a given user

        :return: no return
        """

        # To make a library we need an actual user
        stub_user = UserShop(name='fail')
        user = User(absolute_uid=stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Make a library that ensures we get one back
        self.user_view.create_library(
            service_uid=user.id,
            library_data=self.stub_library.user_view_post_data
        )

        # Get the library created
        with MockEmailService(stub_user, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user.id,
                absolute_uid=user.absolute_uid
            )
        self.assertEqual(libraries[0]['owner'], 'Not available')

    def test_user_retrieves_correct_library_content(self):
        """
        Test that the contents returned from the user_view contains all the
        information that we want

        :return: no return
        """
        # Stub data
        stub_library_other = LibraryShop()
        stub_user_1 = UserShop()
        stub_user_2 = UserShop()

        # To make a library we need an actual user
        user = User(absolute_uid=stub_user_1.absolute_uid)
        user_other = User(absolute_uid=stub_user_2.absolute_uid)
        db.session.add_all([user, user_other])
        db.session.commit()

        # The random user has a library
        self.user_view.create_library(
            service_uid=user_other.id,
            library_data=stub_library_other.user_view_post_data
        )

        # Make a library that ensures we get one back
        number_of_libs = 3
        libs = []
        for i in range(number_of_libs):
            stub_library = LibraryShop()
            _lib = self.user_view.create_library(
                service_uid=user.id,
                library_data=stub_library.user_view_post_data
            )
            libs.append(stub_library)

        # Give random permission to the random user
        self.permission_view.add_permission(library_id=_lib.id,
                                            service_uid=user_other.id,
                                            permission='read',
                                            value=True)

        # Get the library created
        with MockEmailService(stub_user_1, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user.id,
                absolute_uid=user.absolute_uid
            )

        self.assertTrue(len(libraries) == number_of_libs)
        for library in libraries:
            for key in self.stub_library.user_view_get_response():
                self.assertIn(key, library.keys(), 'Missing key: {0}'
                                                   .format(key))
        for i in range(number_of_libs):
            for key in ['name', 'description', 'public']:
                self.assertEqual(libraries[i][key],
                                 libs[i].user_view_post_data[key])

            self.assertEqual(libraries[i]['num_documents'], 0)

            if libraries[i]['id'] == \
                    self.user_view.helper_uuid_to_slug(_lib.id):
                self.assertEqual(libraries[i]['num_users'], 2)
            else:
                self.assertEqual(libraries[i]['num_users'], 1)

            self.assertEqual(libraries[i]['permission'], 'owner')

        # Get the library created
        with MockEmailService(stub_user_2, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user_other.id,
                absolute_uid=user_other.absolute_uid
            )

        self.assertTrue(len(libraries) == 2)

    def test_dates_of_updates_change_correctly(self):
        """
        Test that dates change when a library is updated

        :return: no return
        """

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Make a library that ensures we get one back
        stub_library = LibraryShop()
        library = self.user_view.create_library(
            service_uid=user.id,
            library_data=stub_library.user_view_post_data
        )

        self.document_view.update_library(
            library_id=library.id,
            library_data=dict(public=True)
        )

        library_2 = Library.query.filter(Library.id == library.id).one()

        self.assertEqual(library.date_created, library_2.date_created)
        self.assertNotEqual(library.date_created,
                            library_2.date_last_modified)

    def test_returned_permissions_are_right(self):
        """
        Test that the correct permissions get returned for a library

        :return: no return
        """

        # Stub data
        stub_user_other = UserShop()

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_user.absolute_uid)
        user_other = User(absolute_uid=stub_user_other.absolute_uid)
        db.session.add_all([user, user_other])
        db.session.commit()

        # Make a library to make sure things work properly
        stub_library = LibraryShop()
        library = self.user_view.create_library(
            service_uid=user.id,
            library_data=stub_library.user_view_post_data
        )

        stub_permissions = [['read', True], ['write', True], ['admin', True]]
        for permission, value in stub_permissions:
            self.permission_view.add_permission(library_id=library.id,
                                                service_uid=user_other.id,
                                                permission=permission,
                                                value=value)
            # Get the library created
            with MockEmailService(stub_user_other, end_type='uid'):
                libraries = self.user_view.get_libraries(
                    service_uid=user_other.id,
                    absolute_uid=user_other.absolute_uid
                )

            self.assertEqual(permission, libraries[0]['permission'])

    def test_can_only_see_number_of_people_with_admin_or_owner(self):
        """
        Test that the owner and admin can see the number of people
        :return: no return
        """

        # To make a library we need an actual user
        user_owner = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_admin = User(absolute_uid=self.stub_user_2.absolute_uid)

        library = Library()
        permission_admin = Permissions(admin=True)
        permission_owner = Permissions(owner=True)
        library.permissions.append(permission_admin)
        library.permissions.append(permission_owner)
        user_admin.permissions.append(permission_admin)
        user_owner.permissions.append(permission_owner)

        db.session.add_all([user_owner, user_admin, library, permission_admin,
                            permission_owner])
        db.session.commit()

        # Get the library created
        # For user admin
        with MockEmailService(self.stub_user_2, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user_admin.id,
                absolute_uid=user_admin.absolute_uid
            )[0]
        self.assertTrue(libraries['num_users'] > 0)

        # For user owner
        with MockEmailService(self.stub_user_1, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user_owner.id,
                absolute_uid=user_owner.absolute_uid
            )[0]
        self.assertTrue(libraries['num_users'] > 0)

    def test_cannot_see_number_of_people_with_lower_than_admin(self):
        """
        Test that the non-owner and non-admin cannot see the number of people
        :return: no return
        """

        # To make a library we need an actual user
        user_read = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_write = User(absolute_uid=self.stub_user_2.absolute_uid)

        library = Library()
        permission_read = Permissions(read=True)
        permission_write = Permissions(write=True)
        library.permissions.append(permission_read)
        library.permissions.append(permission_write)
        user_read.permissions.append(permission_read)
        user_write.permissions.append(permission_write)

        db.session.add_all([user_read, user_write, library, permission_read,
                            permission_write])
        db.session.commit()

        # Get the library created
        # For user read
        with MockEmailService(self.stub_user_1, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user_read.id,
                absolute_uid=user_read.absolute_uid
            )[0]
        self.assertTrue(libraries['num_users'] == 0)

        # For user write
        with MockEmailService(self.stub_user_2, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user_write.id,
                absolute_uid=user_write.absolute_uid
            )[0]
        self.assertTrue(libraries['num_users'] == 0)

    def test_user_cannot_add_two_libraries_with_the_same_name(self):
        """
        Test that a user cannot add a new library with the same name

        :return: no return
        """

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Make the first library
        self.user_view.create_library(
            service_uid=user.id,
            library_data=self.stub_library.user_view_post_data
        )

        # Make the second library
        with self.assertRaises(BackendIntegrityError):
            self.user_view.create_library(
                service_uid=user.id,
                library_data=self.stub_library.user_view_post_data
            )

    def test_default_name_and_description_given_when_empty_string_passed(self):
        """
        Test that a user who provides empty strings for the name and
        description has them generated automatically.

        :return: no return
        """

        # Stub data
        stub_library = LibraryShop()

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Make the first library
        for i in range(2):
            # On each loop the user view post will be modified, so lets just
            # be explicit about what we want
            stub_library.user_view_post_data['name'] = ''
            stub_library.user_view_post_data['description'] = ''

            library = self.user_view.create_library(
                service_uid=user.id,
                library_data=stub_library.user_view_post_data
            )

            lib = Library.query.filter(Library.id == library.id).one()
            self.assertTrue(lib.name == 'Untitled Library {0}'.format(i+1),
                            lib.name)
            self.assertTrue(lib.description == DEFAULT_LIBRARY_DESCRIPTION)

    def test_default_name_and_description_given_when_no_content(self):
        """
        Test that a user who does not specify a title or description has them
        generated automatically.

        :return: no return
        """

        # Stub data
        stub_library = LibraryShop(name=None, description=None)
        del stub_library.name
        del stub_library.description

        with self.assertRaises(AttributeError):
            stub_library.name
            stub_library.description

        stub_library.user_view_post_data.pop('name')
        stub_library.user_view_post_data.pop('description')

        with self.assertRaises(KeyError):
            stub_library.user_view_post_data['name']
            stub_library.user_view_post_data['description']

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Make the first library
        for i in range(2):
            library = self.user_view.create_library(
                service_uid=user.id,
                library_data=stub_library.user_view_post_data
            )

            lib = Library.query.filter(Library.id == library.id).one()
            self.assertTrue(lib.name == 'Untitled Library {0}'.format(i+1),
                            lib.name)
            self.assertTrue(lib.description == DEFAULT_LIBRARY_DESCRIPTION)


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

    def test_user_can_get_documents_from_library(self):
        """
        Test that can retrieve all the bibcodes from a library

        :return: no return
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

        # Retrieve the bibcodes using the web services
        response_library, meta_data = \
            self.library_view.get_documents_from_library(
                library_id=library.id,
                service_uid=user.id
            )
        self.assertEqual(library.bibcode, response_library.bibcode)

    def test_user_retrieves_correct_library_content(self):
        """
        Test that the contents returned from the library_view contains all the
        information that we want

        :return: no return
        """
        # Stub data
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        # Give the user and library permissions
        permission = Permissions(owner=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        with MockEmailService(self.stub_user, end_type='uid'):
            library, metadata = self.library_view.get_documents_from_library(
                library_id=library.id,
                service_uid=user.id
            )

        for key in self.stub_library.library_view_get_response():
            self.assertIn(key, metadata)

    def test_user_retrieves_correct_library_content_if_not_owner(self):
        """
        Test that the contents returned from the library_view contains all the
        information that we want

        :return: no return
        """
        # Stub data
        user = User(absolute_uid=self.stub_user.absolute_uid)
        user_random = User(absolute_uid=self.stub_user_2.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=False,
                          bibcode=self.stub_library.bibcode)

        # Give the user and library permissions
        permission = Permissions(owner=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user, user_random])
        db.session.commit()

        with MockEmailService(self.stub_user, end_type='uid'):
            library, metadata = self.library_view.get_documents_from_library(
                library_id=library.id,
                service_uid=user_random.id
            )

        for key in self.stub_library.library_view_get_response():
            self.assertIn(key, metadata)

        self.assertEqual(0, metadata['num_users'])

    def test_that_solr_data_is_returned(self):
        """
        Test that can retrieve all the bibcodes from a library with the data
        returned from the solr bigquery end point

        :return: no return
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
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        # Retrieve the bibcodes using the web services
        with MockSolrBigqueryService():
            response_library = self.library_view.solr_big_query(
                bibcodes=library.bibcode
            )
        self.assertIn('responseHeader', response_library.json())

    def test_that_solr_updates_canonical_bibcodes(self):
        """
        Tests that a comparison between the solr data and the stored data is
        carried out. Mismatching documents are then updated appropriately.

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        original_bibcodes = ['test1', 'test2', 'arXivtest3', 'test4']
        canonical_bibcodes = ['test1', 'test2', 'test3', 'test4']
        solr_docs = [
            {'bibcode': 'test1'},
            {'bibcode': 'test2'},
            {'bibcode': 'test3', 'alternate_bibcode': ['arXivtest3']},
            {'bibcode': 'test4'}
        ]

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode={k: {} for k in original_bibcodes})

        # Give the user and library permissions
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        # Retrieve the bibcodes using the web services
        with MockSolrBigqueryService(solr_docs=solr_docs):
            response_library = self.library_view.solr_big_query(
                bibcodes=library.bibcode
            ).json()
        self.assertIn('responseHeader', response_library)

        # Now check solr updates the records correctly
        solr_docs = response_library['response']['docs']
        updates = self.library_view.solr_update_library(library=library,
                                                        solr_docs=solr_docs)

        # Check the data returned is correct on what files were updated and why
        self.assertEqual(updates['num_updated'], 1)
        self.assertEqual(updates['duplicates_removed'], 0)
        update_list = updates['update_list']
        self.assertEqual(update_list[0]['arXivtest3'],
                         'test3')

        library = Library.query.filter(Library.id == library.id).one()

        self.assertUnsortedNotEqual(library.get_bibcodes(),
                                    original_bibcodes)
        self.assertUnsortedEqual(library.get_bibcodes(),
                                 canonical_bibcodes)

    def test_that_solr_updates_canonical_bibcodes_with_multi_alternates(self):
        """
        Tests that a comparison between the solr data and the stored data is
        carried out. Mismatching documents are then updated appropriately.
        This specifically considers the case when fewer documents are returned
        as there exists two alternates.

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        original_bibcodes = ['test1', 'test2', 'arXivtest3', 'conftest3']
        canonical_bibcodes = ['test1', 'test2', 'test3']
        solr_docs = [
            {'bibcode': 'test1'},
            {'bibcode': 'test2'},
            {'bibcode': 'test3', 'alternate_bibcode': ['arXivtest3',
                                                       'conftest3']},
        ]

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode={k: {} for k in original_bibcodes})

        # Give the user and library permissions
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        # Retrieve the bibcodes using the web services
        with MockSolrBigqueryService(solr_docs=solr_docs):
            response_library = self.library_view.solr_big_query(
                bibcodes=library.bibcode
            ).json()
        self.assertIn('responseHeader', response_library)

        # Now check solr updates the records correctly
        solr_docs = response_library['response']['docs']
        updates = self.library_view.solr_update_library(library=library,
                                                        solr_docs=solr_docs)

        self.assertEqual(updates['num_updated'], 2)
        self.assertEqual(updates['duplicates_removed'], 1)
        update_list = updates['update_list']

        self.assertEqual(
            get_item(update_list, 'arXivtest3'),
            'test3'
        )
        self.assertEqual(
            get_item(update_list, 'conftest3'),
            'test3'
        )

        library = Library.query.filter(Library.id == library.id).one()

        self.assertUnsortedNotEqual(library.get_bibcodes(),
                                    original_bibcodes)
        self.assertUnsortedEqual(library.get_bibcodes(),
                                 canonical_bibcodes)

    def test_user_without_permission_cannot_access_private_library(self):
        """
        Tests that the user requesting to see the contents of a library has
        the correct permissions. In this case, they do not, and are refused to
        see the library content.

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user = User(absolute_uid=self.stub_user_1.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        # Give the user and library permissions
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        # Make sure the second user is denied access
        # add 1 to the UID to represent a random user
        stub_user_random = UserShop()
        access = self.library_view.read_access(service_uid=self.stub_user_2.id,
                                               library_id=library.id)
        self.assertIsNotNone(access)
        self.assertFalse(access)

    def test_if_a_library_exists_or_not(self):
        """
        Tests if a library exists or not

        :return: no return
        """

        # Make a library
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)
        db.session.add(library)
        db.session.commit()

        exists = self.library_view.helper_library_exists(library_id=library.id)
        self.assertTrue(exists)

        db.session.delete(library)
        db.session.commit()

        exists = self.library_view.helper_library_exists(library_id=library.id)
        self.assertFalse(exists)



class TestDocumentViews(TestCaseDatabase):
    """
    Base class to test the Document view for POST/DELETE (PUT for tags?)
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """

        super(TestDocumentViews, self).__init__(*args, **kwargs)
        self.document_view = DocumentView

        # Stub data
        self.stub_user = self.stub_user_1 = UserShop()
        self.stub_user_2 = UserShop()

        self.stub_library = self.stub_library_1 = LibraryShop()
        self.stub_library_2 = LibraryShop()

    def test_user_can_delete_a_library(self):
        """
        Tests that the user can correctly remove a library from its account

        :return: no return
        """

        # Step 1. Make the user, library, and permissions

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
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        library = Library.query.filter(Library.id == library.id).one()
        self.assertIsInstance(library, Library)

        self.document_view.delete_library(library_id=library.id)

        with self.assertRaises(NoResultFound):
            Library.query.filter(Library.id == library.id).one()

    def test_user_cannot_delete_a_library_if_not_owner(self):
        """
        Tests that the user cannot delete a library if they are not the owner

        :return: no return
        """

        # Step 1. Make the user, library, and permissions

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
        permission = Permissions(read=True, owner=False)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()
        library = Library.query.filter(Library.id == library.id).one()
        self.assertIsInstance(library, Library)

        access = self.document_view.delete_access(service_uid=user.id,
                                                  library_id=library.id)
        self.assertFalse(access)

    def test_user_can_delete_a_library_if_owner(self):
        """
        Tests that the user cannot delete a library if they are not the owner

        :return: no return
        """

        # Step 1. Make the user, library, and permissions

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
        permission = Permissions(read=False, owner=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()
        library = Library.query.filter(Library.id == library.id).one()
        self.assertIsInstance(library, Library)

        access = self.document_view.delete_access(service_uid=user.id,
                                                  library_id=library.id)
        self.assertTrue(access)

    def test_when_delete_library_it_removes_permissions(self):
        """
        Tests that when a library is deleted, the associated permissions are
         also deleted. Otherwise this leads to issues.

        :return: no return
        """

        # Make the user, library, and permissions
        user = User(absolute_uid=self.stub_user.absolute_uid)
        user_2 = User(absolute_uid=self.stub_user_2.absolute_uid)
        db.session.add_all([user, user_2])
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        # Give the user and library permissions
        permission = Permissions(owner=True)
        permission_2 = Permissions(owner=False, read=True)

        # Commit the stub data
        user.permissions.append(permission)
        user_2.permissions.append(permission_2)

        library.permissions.append(permission)
        library.permissions.append(permission_2)

        db.session.add_all([library, permission, user, user_2, permission_2])
        db.session.commit()

        search_library = Library.query.filter(
            Library.id == library.id
        ).one()
        search_permission = Permissions.query.filter(
            Permissions.id == permission.id
        ).all()
        self.assertIsInstance(search_library, Library)
        self.assertTrue(len(search_permission), 2)

        self.document_view.delete_library(library_id=library.id)

        with self.assertRaises(NoResultFound):
            Library.query.filter(
                Library.id == library.id
            ).one()

        with self.assertRaises(NoResultFound):
            Permissions.query.filter(
                Permissions.id == permission.id
            ).one()

        with self.assertRaises(NoResultFound):
            Permissions.query.filter(
                Permissions.id == permission_2.id
            ).one()

        with self.assertRaises(NoResultFound):
            Permissions.query.filter(
                Permissions.library_id == library.id
            ).one()

    def test_user_can_add_to_library(self):
        """
        Tests that adding a bibcode to a library works correctly

        :return:
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True)

        # Give the user and library permissions
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        library_id = library.id

        # Get stub data for the document

        # Add a document to the library
        number_added = self.document_view.add_document_to_library(
            library_id=library_id,
            document_data=self.stub_library.document_view_post_data('add')
        )
        self.assertEqual(number_added, len(self.stub_library.bibcode))

        # Check that the document is in the library
        library = Library.query.filter(Library.id == library_id).all()
        for _lib in library:
            self.assertIn(self.stub_library.bibcode.keys()[0], _lib.bibcode)

        # Add a different document to the library
        number_added = self.document_view.add_document_to_library(
            library_id=library_id,
            document_data=self.stub_library_2.document_view_post_data('add')
        )
        self.assertEqual(number_added, len(self.stub_library.bibcode))

        # Check that the document is in the library
        library = Library.query.filter(Library.id == library_id).all()
        for _lib in library:
            self.assertIn(self.stub_library_2.bibcode.keys()[0], _lib.bibcode)

    def test_user_cannot_duplicate_same_document_in_library(self):
        """
        Tests that adding a bibcode to a library works correctly

        :return:
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True)

        # Give the user and library permissions
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        library_id = library.id

        # Get stub data for the document

        # Add a document to the library
        number_added = self.document_view.add_document_to_library(
            library_id=library_id,
            document_data=self.stub_library.document_view_post_data('add')
        )
        self.assertEqual(number_added, len(self.stub_library.bibcode))

        # Shouldn't add the same document again
        number_added = self.document_view.add_document_to_library(
            library_id=library_id,
            document_data=self.stub_library.document_view_post_data('add')
        )
        self.assertEqual(0, number_added)

    def test_user_can_remove_document_from_library(self):
        """
        Test that can remove a document from the library

        :return: no return
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
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        # Remove the bibcode from the library
        number_removed = self.document_view.remove_documents_from_library(
            library_id=library.id,
            document_data=self.stub_library.document_view_post_data('remove')
        )
        self.assertEqual(number_removed, len(self.stub_library.bibcode))

        # Check it worked
        library = Library.query.filter(Library.id == library.id).one()

        self.assertTrue(
            len(library.bibcode) == 0,
            'There should be no bibcodes: {0}'.format(library.bibcode)
        )

    def test_user_without_permission_cannot_edit_private_library(self):
        """
        Tests that the user requesting to edit the contents of a library has
        the correct permissions. In this case, they do not, and are refused to
        see the library content.

        :return: no return
        """

        # Make a fake user and library
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
        permission = Permissions(read=True,
                                 write=True)

        # Commit the stub data
        user.permissions.append(permission)
        library.permissions.append(permission)
        db.session.add_all([library, permission, user])
        db.session.commit()

        # add 1 to the UID to represent a random user
        access = self.document_view.write_access(
            service_uid=self.stub_user_2.absolute_uid,
            library_id=library.id
        )
        self.assertIsNotNone(access)
        self.assertFalse(access)

    def test_can_update_libraries_details(self):
        """
        Tests that a user can update the libraries details, such as name and
        description. This only works if they have owner or admin permission.

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        db.session.add(library)
        db.session.commit()

        new_name = 'New name'
        new_description = 'New description'
        new_publicity = True
        random_text = 'Not added'

        # Update first just the name
        update_data = dict(name=new_name,
                           random=random_text)

        return_data = self.document_view.update_library(
            library_id=library.id,
            library_data=update_data
        )

        self.assertIn('name', return_data)
        self.assertNotIn('description', return_data)
        self.assertNotIn('public', return_data)
        self.assertEqual(return_data['name'], new_name)

        # Then update the description
        update_data = dict(description=new_description,
                           random=random_text)

        return_data = self.document_view.update_library(
            library_id=library.id,
            library_data=update_data
        )

        self.assertIn('description', return_data)
        self.assertNotIn('name', return_data)
        self.assertNotIn('public', return_data)
        self.assertEqual(return_data['description'], new_description)

        # Then update the publicity
        update_data = dict(public=new_publicity,
                           random=random_text)

        return_data = self.document_view.update_library(
            library_id=library.id,
            library_data=update_data
        )

        self.assertIn('public', return_data)
        self.assertNotIn('name', return_data)
        self.assertNotIn('description', return_data)
        self.assertEqual(return_data['public'], new_publicity)

        # Update both
        # Then update the description
        new_name += ' new'
        new_description += ' new'
        new_publicity = False
        update_data = dict(name=new_name,
                           description=new_description,
                           public=new_publicity,
                           random=random_text)

        return_data = self.document_view.update_library(
            library_id=library.id,
            library_data=update_data
        )

        self.assertIn('name', return_data)
        self.assertIn('description', return_data)
        self.assertIn('public', return_data)
        self.assertEqual(return_data['name'], new_name)
        self.assertEqual(return_data['description'], new_description)
        self.assertEqual(return_data['public'], new_publicity)

        new_library = Library.query.filter(Library.id == library.id).one()
        self.assertEqual(new_library.name, new_name)
        self.assertEqual(new_library.description, new_description)
        with self.assertRaises(AttributeError):
            library.random

    def test_can_update_libraries_details_if_owner_or_admin(self):
        """
        Tests that a user can update the libraries details, such as name and
        description. This only works if they have owner or admin permission.

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user_owner = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_admin = User(absolute_uid=self.stub_user_2.absolute_uid)
        db.session.add_all([user_owner, user_admin])
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        # Give the user and library permissions
        permission_owner = Permissions(owner=True)
        permission_admin = Permissions(admin=True, owner=False)

        # Commit the stub data
        user_owner.permissions.append(permission_owner)
        user_admin.permissions.append(permission_admin)

        library.permissions.append(permission_owner)
        library.permissions.append(permission_admin)
        db.session.add_all([library, permission_owner, permission_admin,
                            user_admin, user_owner])
        db.session.commit()

        for user in [user_owner, user_admin]:
            access = self.document_view.update_access(
                service_uid=user.id,
                library_id=library.id
            )
            self.assertTrue(access)

    def test_cannot_update_libraries_details_if_not_owner_or_admin(self):
        """
        Test that users with no permissions, read, and write permissions,
        cannot alter the name or description of the library.

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user_read = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_write = User(absolute_uid=self.stub_user_2.absolute_uid)
        user_random = User(absolute_uid=1)

        db.session.add_all([user_random, user_read, user_write])
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        # Give the user and library permissions
        permission_read = Permissions(read=True, owner=False)
        permission_write = Permissions(write=True, owner=False)

        # Commit the stub data
        user_read.permissions.append(permission_read)
        user_write.permissions.append(permission_write)

        library.permissions.append(permission_read)
        library.permissions.append(permission_write)
        db.session.add_all([library, permission_read, permission_write,
                            user_read, user_write])
        db.session.commit()

        for user in [user_random, user_read, user_write]:
            access = self.document_view.update_access(
                service_uid=user.id,
                library_id=library.id
            )
            self.assertFalse(access)

class TestPermissionViews(TestCaseDatabase):
    """
    Base class to test the creation, modification, deletion of user
    permissions via the Permissions view.
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """

        super(TestPermissionViews, self).__init__(*args, **kwargs)
        self.permission_view = PermissionView
        self.user_view = UserView

        # Stub data
        self.stub_user = self.stub_user_1 = UserShop()
        self.stub_user_2 = UserShop()
        self.stub_user_3 = UserShop()
        self.stub_library = LibraryShop()

    def test_can_add_read_permission_to_user(self):
        """
        Tests the backend logic for adding read permissions to a user

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        db.session.add_all([user, library])
        db.session.commit()

        self.permission_view.add_permission(service_uid=user.id,
                                            library_id=library.id,
                                            permission='read',
                                            value=True)

        try:
            permission = Permissions.query.filter(
                Permissions.user_id == user.id,
                Permissions.library_id == library.id
            ).one()
        except Exception as error:
            self.fail('No permissions were created, most likely the code has '
                      'not been implemented. [{0}]'.format(error))

        self.assertTrue(permission.read)
        self.assertFalse(permission.write)
        self.assertFalse(permission.owner)

    def test_that_permissions_are_removed_if_the_user_has_none_left(self):
        """
        Tests that if a permission is removed and all the values are False, then
        the permission for that person and library is removed.

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        db.session.add_all([user, library])
        db.session.commit()

        # Add the permission
        self.permission_view.add_permission(service_uid=user.id,
                                            library_id=library.id,
                                            permission='read',
                                            value=True)
        self.permission_view.add_permission(service_uid=user.id,
                                            library_id=library.id,
                                            permission='write',
                                            value=True)
        # Check the permission was added
        permission = Permissions.query.filter(
            Permissions.user_id == user.id,
            Permissions.library_id == library.id
        ).one()
        self.assertTrue(permission.read)
        self.assertTrue(permission.write)

        # Remove the permission
        self.permission_view.add_permission(service_uid=user.id,
                                            library_id=library.id,
                                            permission='write',
                                            value=False)

        # Check the permission was removed
        permission = Permissions.query.filter(
            Permissions.user_id == user.id,
            Permissions.library_id == library.id
        ).one()
        self.assertTrue(permission.read)
        self.assertFalse(permission.write)

        # Remove the permission
        self.permission_view.add_permission(service_uid=user.id,
                                            library_id=library.id,
                                            permission='read',
                                            value=False)

        # Check the permission is not available
        with self.assertRaises(NoResultFound):
            Permissions.query.filter(
                Permissions.user_id == user.id,
                Permissions.library_id == library.id
            ).one()

    def test_a_user_without_permissions_cannot_modify_permissions(self):
        """
        Tests that a user that does not have admin permissions, cannot modify
        the permissions of another user.

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user_1 = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_2 = User(absolute_uid=self.stub_user_2.absolute_uid)

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        permission = Permissions()
        user_1.permissions.append(permission)
        library.permissions.append(permission)

        db.session.add_all([user_1, user_2, library])
        db.session.commit()

        result = self.permission_view.has_permission(
            service_uid_editor=user_2.id,
            service_uid_modify=user_1.id,
            library_id=library.id
        )

        self.assertFalse(result)

    def test_a_user_with_owner_permissions_can_edit_permissions(self):
        """
        Tests that the owner has the ability to edit permissions of users
        within their library.

        :return: no return
        """
        # Make a fake user and library
        # Ensure a user exists
        user_1 = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_2 = User(absolute_uid=self.stub_user_2.absolute_uid)

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        permission = Permissions()
        permission.owner = True
        user_2.permissions.append(permission)
        library.permissions.append(permission)

        db.session.add_all([user_1, user_2, library])
        db.session.commit()

        result = self.permission_view.has_permission(
            service_uid_editor=user_2.id,
            service_uid_modify=user_1.id,
            library_id=library.id
        )

        self.assertTrue(result)

    def test_a_user_with_editing_permissions_can_edit_permissions(self):
        """
        Tests that a user that has been given admin privileges can edit other
        users in the library.

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user_1 = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_2 = User(absolute_uid=self.stub_user_2.absolute_uid)

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        permission_1 = Permissions()
        permission_1.admin = True
        permission_2 = Permissions()
        permission_2.admin = True

        user_1.permissions.append(permission_1)
        library.permissions.append(permission_1)

        user_2.permissions.append(permission_2)
        library.permissions.append(permission_2)

        db.session.add_all([user_1, user_2, library])
        db.session.commit()

        result = self.permission_view.has_permission(
            service_uid_editor=user_2.id,
            service_uid_modify=user_1.id,
            library_id=library.id
        )

        self.assertTrue(result)

    def test_a_user_with_editing_permissions_cannot_edit_owner(self):
        """
        Tests that a user with admin permissions cannot manipulate any of the
        settings of the owners permissions.

        :return: no return
        """
        # Make a fake user and library
        # Ensure a user exists
        user_1 = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_2 = User(absolute_uid=self.stub_user_2.absolute_uid)

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        permission_1 = Permissions()
        permission_1.owner = True
        permission_2 = Permissions()
        permission_2.admin = True

        user_1.permissions.append(permission_1)
        library.permissions.append(permission_1)

        user_2.permissions.append(permission_2)
        library.permissions.append(permission_2)

        db.session.add_all([user_1, user_2, library])
        db.session.commit()

        result = self.permission_view.has_permission(
            service_uid_editor=user_2.id,
            service_uid_modify=user_1.id,
            library_id=library.id
        )

        self.assertFalse(result)

    def test_a_user_with_permissions_cannot_edit_anyone(self):
        """
        Tests that a user with read permissions cannot do any permission
        changes to other users.

        :return: no return
        """
        # Make a fake user and library
        # Ensure a user exists
        user_admin = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_read_only = User(absolute_uid=self.stub_user_2.absolute_uid)

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        permission_admin = Permissions()
        permission_admin.admin = True
        permission_read_only = Permissions()
        permission_read_only.read = True

        user_admin.permissions.append(permission_admin)
        library.permissions.append(permission_admin)

        user_read_only.permissions.append(permission_read_only)
        library.permissions.append(permission_read_only)

        db.session.add_all([user_admin, user_read_only, library])
        db.session.commit()

        result = self.permission_view.has_permission(
            service_uid_editor=user_read_only.id,
            service_uid_modify=user_admin.id,
            library_id=library.id
        )

        self.assertFalse(result)

    def test_owner_does_not_modify_owner(self):
        """
        Tests that the owner cannot modify the owners own properties within
        the database. Given that the owner has all powers, it makes no sense
        to change any value.

        :return: no return
        """
        # Make a fake user and library
        # Ensure a user exists
        user_owner = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user_owner)
        db.session.commit()

        # Ensure a library exists
        library = self.user_view.create_library(
            service_uid=user_owner.id,
            library_data=self.stub_library.user_view_post_data
        )

        # Check our user has owner permissions
        permission = Permissions.query.filter(
            Permissions.library_id == library.id,
            Permissions.user_id == user_owner.id
        ).one()
        self.assertTrue(permission.owner)

        # Check that the owner cannot mess with the owner's permissions
        result = self.permission_view.has_permission(
            service_uid_editor=user_owner.id,
            service_uid_modify=user_owner.id,
            library_id=library.id
        )
        self.assertFalse(result)

    def test_admin_cannot_modify_owner_value(self):
        """
        Test to ensure that the user with owner privileges cannot modify the
        owner value of a library

        :return: no return
        """
        # Make a fake user and library
        # Ensure a user exists
        user_owner = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_admin = User(absolute_uid=self.stub_user_2.absolute_uid)
        user_random = User(absolute_uid=self.stub_user_3.absolute_uid)

        db.session.add_all([user_owner, user_admin, user_random])
        db.session.commit()

        # Ensure a library exists
        library = self.user_view.create_library(
            service_uid=user_owner.id,
            library_data=self.stub_library.user_view_post_data
        )

        # Check our user has owner permissions
        permission = Permissions.query.filter(
            Permissions.library_id == library.id,
            Permissions.user_id == user_owner.id
        ).one()
        self.assertTrue(permission.owner)

        # Give the second user, admin permissions
        self.permission_view.add_permission(service_uid=user_admin.id,
                                            library_id=library.id,
                                            permission='admin',
                                            value=True)

        # Check our user has owner permissions
        permission = Permissions.query.filter(
            Permissions.library_id == library.id,
            Permissions.user_id == user_admin.id
        ).one()
        self.assertTrue(permission.admin)
        self.assertFalse(permission.owner)

        # Check that the admin cannot modify the owner status of random user
        with self.assertRaises(PermissionDeniedError):
            self.permission_view.add_permission(service_uid=user_random.id,
                                                library_id=library.id,
                                                permission='owner',
                                                value=True)

        # Check our user has owner permissions
        with self.assertRaises(NoResultFound):
            Permissions.query.filter(
                Permissions.library_id == library.id,
                Permissions.user_id == user_random.id
            ).one()

    def test_can_get_permissions_for_a_user(self):
        """
        Tests that the permissions of the user are returned
        :return: no return
        """

        # Make a fake user and library
        user = User(absolute_uid=self.stub_user.absolute_uid)
        db.session.add(user)
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        permission = Permissions(owner=True)
        user.permissions.append(permission)
        library.permissions.append(permission)

        db.session.add_all([user, library, permission])
        db.session.commit()

        with MockEmailService(self.stub_user, end_type='uid'):
            permissions = self.permission_view.get_permissions(
                library_id=library.id
            )

        self.assertIsInstance(permissions, list)
        self.assertIn(self.stub_user.email, permissions[0])
        self.assertIn('owner', permissions[0][self.stub_user.email])

    def test_cannot_get_permissions_for_non_user_and_owner(self):
        """
        Tests that the permissions of the user are not returned if the
        requesting user is not an admin or owner

        :return: no return
        """

        # Make a fake user and library
        user_read = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_write = User(absolute_uid=self.stub_user_2.absolute_uid)
        db.session.add_all([user_read, user_write])
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        permission_read = Permissions(read=True)
        permission_write = Permissions(write=True)
        user_read.permissions.append(permission_read)
        user_write.permissions.append(permission_write)

        library.permissions.append(permission_read)
        library.permissions.append(permission_write)

        db.session.add_all([user_read, user_write, library, permission_read,
                            permission_write])
        db.session.commit()

        for user in [user_read, user_write]:
            allowed = self.permission_view.read_access(
                service_uid=user.id,
                library_id=library.id
            )

            self.assertFalse(allowed)

    def test_can_get_permissions_for_user_and_owner(self):
        """
        Tests that the permissions of the user are returned if the requesting
        user is an admin or owner

        :return: no return
        """

        # Make a fake user and library
        user_admin = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_owner = User(absolute_uid=self.stub_user_2.absolute_uid)
        db.session.add_all([user_owner, user_admin])
        db.session.commit()

        # Ensure a library exists
        library = Library(name='MyLibrary',
                          description='My library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        permission_owner = Permissions(owner=True)
        permission_admin = Permissions(admin=True)
        user_owner.permissions.append(permission_owner)
        user_admin.permissions.append(permission_admin)

        library.permissions.append(permission_owner)
        library.permissions.append(permission_admin)

        db.session.add_all([user_owner, user_admin, library, permission_owner,
                            permission_admin])
        db.session.commit()

        for user in [user_admin, user_owner]:
            allowed = self.permission_view.read_access(
                service_uid=user.id,
                library_id=library.id
            )

            self.assertTrue(allowed)

    def test_permissions_returned_dont_include_other_libraries(self):
        """
        Makes sure the query being used does not return strange content

        :return: no return
        """
        # Make a fake user and library
        user_1 = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_2 = User(absolute_uid=self.stub_user_2.absolute_uid)
        db.session.add_all([user_1, user_2])
        db.session.commit()

        # Ensure a library exists
        library_1 = Library(name='MyLibrary',
                            description='My library',
                            public=True,
                            bibcode=self.stub_library.bibcode)

        library_2 = Library(name='MyLibrary',
                            description='My library',
                            public=True,
                            bibcode=self.stub_library.bibcode)

        permission_1 = Permissions(owner=True)
        permission_2 = Permissions(admin=True)
        user_1.permissions.append(permission_1)
        user_2.permissions.append(permission_2)

        library_1.permissions.append(permission_1)
        library_2.permissions.append(permission_2)

        db.session.add_all([user_1, user_2, library_1, library_2,
                            permission_1, permission_2])
        db.session.commit()

        with MockEmailService(self.stub_user_1, end_type='uid'):
            return_1 = self.permission_view.get_permissions(
                library_id=library_1.id
            )
        with MockEmailService(self.stub_user_2, end_type='uid'):
            return_2 = self.permission_view.get_permissions(
                library_id=library_2.id
            )

        self.assertNotEqual(return_1, return_2)
        self.assertTrue(len(return_1) == 1)
        self.assertTrue(len(return_2) == 1)
        self.assertIn(self.stub_user_1.email, return_1[0])
        self.assertIn(self.stub_user_2.email, return_2[0])
        self.assertEqual(['owner'], return_1[0][self.stub_user_1.email])
        self.assertEqual(['admin'], return_2[0][self.stub_user_2.email])

class TestTransferViews(TestCaseDatabase):
    """
    Base class to test the transferring of libraries between users.
    """
    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """

        super(TestTransferViews, self).__init__(*args, **kwargs)
        self.permission_view = PermissionView
        self.transfer_view = TransferView

        # Stub data
        self.stub_user = self.stub_user_1 = UserShop()
        self.stub_user_2 = UserShop()
        self.stub_user_3 = UserShop()
        self.stub_user_4 = UserShop()
        self.stub_library = LibraryShop()

    def test_cannot_transfer_ownership_if_not_owner(self):
        """
        Tests that if you do not have owner permissions then the user does
        not have 'write' access to the transfer process

        :return: no return
        """

        # Make a fake user and library
        user_none = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_read = User(absolute_uid=self.stub_user_2.absolute_uid)
        user_write = User(absolute_uid=self.stub_user_3.absolute_uid)
        user_admin = User(absolute_uid=self.stub_user_4.absolute_uid)
        db.session.add_all([user_none, user_read, user_write, user_admin])
        db.session.commit()

        # Ensure a library exists
        stub_library = Library(name='MyLibrary',
                               description='My library',
                               public=True,
                               bibcode=self.stub_library.bibcode)

        permissions_read = Permissions(admin=True)
        permissions_write = Permissions(write=True)
        permissions_admin = Permissions(admin=True)

        user_read.permissions.append(permissions_read)
        user_write.permissions.append(permissions_write)
        user_admin.permissions.append(permissions_admin)

        stub_library.permissions.append(permissions_read)
        stub_library.permissions.append(permissions_write)
        stub_library.permissions.append(permissions_admin)

        db.session.add_all([permissions_read, permissions_write,
                            permissions_admin, user_read, user_write,
                            user_admin, stub_library])
        db.session.commit()

        for stub_user in [user_none, user_read, user_write, user_admin]:
            access = self.transfer_view.write_access(
                service_uid=stub_user.id,
                library_id=stub_library.id
            )
            self.assertFalse(access)

    def test_can_transfer_a_library(self):
        """
        Tests that you can transfer the ownership of a library

        :return: no return
        """
        # Make a fake user and library
        user_owner = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_new_owner = User(absolute_uid=self.stub_user_2.absolute_uid)

        db.session.add_all([user_owner, user_new_owner])
        db.session.commit()

        # Ensure a library exists
        stub_library = Library(name='MyLibrary',
                               description='My library',
                               public=True,
                               bibcode=self.stub_library.bibcode)

        permissions = Permissions(owner=True)
        user_owner.permissions.append(permissions)
        stub_library.permissions.append(permissions)

        db.session.add_all([permissions, user_owner, stub_library])
        db.session.commit()

        self.transfer_view.transfer_ownership(current_owner_uid=user_owner.id,
                                              new_owner_uid=user_new_owner.id,
                                              library_id=stub_library.id)

        permission = Permissions.query.filter(
            Permissions.user_id == user_new_owner.id
        ).filter(
            Permissions.library_id == stub_library.id
        ).one()
        self.assertTrue(permission.owner)

        with self.assertRaises(NoResultFound):
            Permissions.query.filter(
                Permissions.user_id == user_owner.id
            ).filter(
                Permissions.library_id == stub_library.id
            ).one()

    def test_can_transfer_a_library_for_a_reader(self):
        """
        Tests that you can transfer the ownership of a library

        :return: no return
        """
        # Make a fake user and library
        user_owner = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_new_owner = User(absolute_uid=self.stub_user_2.absolute_uid)

        db.session.add_all([user_owner, user_new_owner])
        db.session.commit()

        # Ensure a library exists
        stub_library = Library(name='MyLibrary',
                               description='My library',
                               public=True,
                               bibcode=self.stub_library.bibcode)

        permissions = Permissions(owner=True)
        permissions_read = Permissions(read=True)
        user_owner.permissions.append(permissions)
        user_new_owner.permissions.append(permissions_read)
        stub_library.permissions.append(permissions)
        stub_library.permissions.append(permissions_read)

        db.session.add_all([permissions, user_owner, stub_library,
                            permissions_read, user_new_owner])
        db.session.commit()

        self.transfer_view.transfer_ownership(current_owner_uid=user_owner.id,
                                              new_owner_uid=user_new_owner.id,
                                              library_id=stub_library.id)

        permission = Permissions.query.filter(
            Permissions.user_id == user_new_owner.id
        ).filter(
            Permissions.library_id == stub_library.id
        ).all()
        self.assertTrue(len(permission) == 1)
        self.assertTrue(permission[0].owner)
        self.assertTrue(permission[0].read)

        with self.assertRaises(NoResultFound):
            Permissions.query.filter(
                Permissions.user_id == user_owner.id
            ).filter(
                Permissions.library_id == stub_library.id
            ).one()

    def test_transfer_query_when_mutliple_libraries(self):
        """
        Checks that the same logic works when there is more than one library
        within the database.

        :return:
        """
        # Make a fake user and library
        user_owner = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_random = User(absolute_uid=self.stub_user_2.absolute_uid)
        user_new_owner = User(absolute_uid=self.stub_user_3.absolute_uid)
        db.session.add_all([user_owner, user_new_owner, user_random])
        db.session.commit()

        # Ensure a library exists
        stub_library_1 = Library(
            name='MyLibrary',
            description='My library',
            public=True,
            bibcode=self.stub_library.bibcode
        )
        stub_library_2 = Library(
            name='MyLibrary',
            description='My library',
            public=True,
            bibcode=self.stub_library.bibcode
        )
        db.session.add_all([
            stub_library_1,
            stub_library_2
        ])
        db.session.commit()

        # Generate and add permissions
        permission_owner = Permissions(
            owner=True,
            library_id=stub_library_1.id,
            user_id=user_owner.id
        )
        permission_random_library_1 = Permissions(
            read=True,
            library_id=stub_library_1.id,
            user_id=user_random.id
        )
        permission_random_library_2 = Permissions(
            owner=True,
            library_id=stub_library_2.id,
            user_id=user_random.id
        )
        db.session.add_all([
            permission_owner,
            permission_random_library_1,
            permission_random_library_2
        ])
        db.session.commit()

        # Transfer the ownership of library 1
        self.transfer_view.transfer_ownership(current_owner_uid=user_owner.id,
                                              new_owner_uid=user_new_owner.id,
                                              library_id=stub_library_1.id)

        # Check that the permissions changed properly
        # New user owner has owner permissions
        permission = Permissions.query.filter(
            Permissions.user_id == user_new_owner.id
        ).filter(
            Permissions.library_id == stub_library_1.id
        ).one()
        self.assertTrue(permission.owner)

        # Old owner no longer has permissions
        with self.assertRaises(NoResultFound):
            Permissions.query.filter(
                Permissions.user_id == user_owner.id
            ).filter(
                Permissions.library_id == stub_library_1.id
            ).one()

        # Check the random user did not change
        # Random owns library 2
        permission = Permissions.query.filter(
            Permissions.user_id == user_random.id
        ).filter(
            Permissions.library_id == stub_library_2.id
        ).one()
        self.assertTrue(permission.owner)

        # Random reads library 1
        permission = Permissions.query.filter(
            Permissions.user_id == user_random.id
        ).filter(
            Permissions.library_id == stub_library_1.id
        ).one()
        self.assertTrue(permission.read)

if __name__ == '__main__':
    unittest.main(verbosity=2)
