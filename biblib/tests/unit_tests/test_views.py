"""
Tests Views of the application
"""
import unittest
import uuid
from biblib.models import User, Library, Permissions, MutableDict, Notes
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from biblib.views import UserView, LibraryView, DocumentView, PermissionView, \
    BaseView, TransferView, ClassicView, OperationsView, QueryView, NotesView
from biblib.views import DEFAULT_LIBRARY_DESCRIPTION
from biblib.tests.stubdata.stub_data import UserShop, LibraryShop, fake_biblist
from biblib.utils import get_item
from biblib.biblib_exceptions import BackendIntegrityError, PermissionDeniedError
from biblib.tests.base import TestCaseDatabase, MockEmailService, \
    MockSolrBigqueryService, MockSolrQueryService
from biblib.emails import PermissionsChangedEmail
from flask import current_app

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
                    {'read': True, 'write': False, 'admin': False, 'owner': False}
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
                        {'read': True, 'write': False, 'admin': False, 'owner': False}
                    )
                )

    def test_send_email(self):
        """
        Tests that an email message is constructed
        Note: no email is sent in flask testing mode (currently set in inherited class
        TestCaseDatabase, TESTING=True; https://pythonhosted.org/Flask-Mail)

        :return: none
        """
        email = 'test@email'
        payload = u'This is a test payload'
        msg = BaseView.send_email(email_addr=email, payload_plain=payload, payload_html=payload, email_template=PermissionsChangedEmail)

        self.assertTrue(payload in msg.body)
        self.assertEqual(msg.subject, PermissionsChangedEmail.subject)

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
        self.stub_user_3 = UserShop()

        self.stub_library = LibraryShop()

    def test_user_creation(self):
        """
        Creates a user and checks it exists within the database

        :return: no return
        """

        with self.app.session_scope() as session:
            # Create a user using the function
            self.user_view.create_user(absolute_uid=self.stub_user_1.absolute_uid)
            # Create another use so that we know it returns a single record
            self.user_view.create_user(absolute_uid=self.stub_user_2.absolute_uid)

            # Check if it really exists in the database
            result = session.query(User).filter(
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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Create the library for the user we created
            library = self.user_view.create_library(
                service_uid=user.id,
                library_data=self.stub_library.user_view_post_data
            )

            with self.assertRaises(KeyError):
                library['bibcode']

            # Check that the library was created with the correct permissions
            result = session.query(Permissions)\
                .filter(User.id == Permissions.user_id)\
                .filter(BaseView.helper_slug_to_uuid(library['id']) == Permissions.library_id)\
                .all()

            with self.assertRaises(AttributeError):
                result.library.bibcode

            self.assertTrue(len(result) == 1)

        user_unicode = User(absolute_uid=self.stub_user_2.absolute_uid)
        with self.app.session_scope() as session:
            # confirm for a library with a unicode name
            session.add(user_unicode)
            session.commit()

            stub_library_unicode = LibraryShop()
            stub_library_unicode.user_view_post_data['name'] = u'\u521b\u65b0\u7fa4\u4f53'
            library_unicode = self.user_view.create_library(
                service_uid=user_unicode.id,
                library_data=stub_library_unicode.user_view_post_data
            )

            with self.assertRaises(KeyError):
                library_unicode['bibcode']

            # Check that the library was created with the correct permissions
            result = session.query(Permissions) \
                .filter(User.id == Permissions.user_id) \
                .filter(BaseView.helper_slug_to_uuid(library_unicode['id']) == Permissions.library_id) \
                .all()

            with self.assertRaises(AttributeError):
                result.library_unicode.bibcode

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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Create the library for the user we created
            library = self.user_view.create_library(
                service_uid=user.id,
                library_data=stub_library.user_view_post_data
            )

            # Check that the library was created with the correct permissions
            result = session.query(Permissions)\
                .filter(User.id == Permissions.user_id)\
                .filter(BaseView.helper_slug_to_uuid(library['id']) == Permissions.library_id)\
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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

        library_data = stub_library.user_view_post_data

        for bib_type in ['string', int(3), float(3.0), dict(test='test')]:
            with self.assertRaises(TypeError):
                library_data['bibcode'] = bib_type
                # Create the library for the user we created
                lib = self.user_view.create_library(
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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

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
        
        self.assertEqual(libraries['count'], number_of_libs)

    def test_user_can_retrieve_rows_number_of_libraries(self):
        """
        Test that we can obtain a given number libraries that correspond to a given user

        :return: no return
        """

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

        # Make a library that ensures we get one back
        number_of_libs = 100
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
                absolute_uid=user.absolute_uid, rows=20
            )
        
        self.assertEqual(len(libraries['libraries']), 20)

    def test_user_can_retrieve_libraries_from_start(self):
        """
        Test that we can obtain the libraries that correspond to a given user
        with a given starting point

        :return: no return
        """

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

        # Make a library that ensures we get one back
        number_of_libs = 100
        for i in range(number_of_libs):
            stub_library = LibraryShop()
            self.user_view.create_library(
                service_uid=user.id,
                library_data=stub_library.user_view_post_data
            )
        with MockEmailService(self.stub_user, end_type='uid'):
            libraries_full = self.user_view.get_libraries(
                service_uid=user.id,
                absolute_uid=user.absolute_uid, start=0
            )['libraries']
        
        # Get the library created
        with MockEmailService(self.stub_user, end_type='uid'):
            my_libraries = self.user_view.get_libraries(
                service_uid=user.id,
                absolute_uid=user.absolute_uid, start=10
            )['libraries'] 

        self.assertEqual(len(my_libraries), 90)
        self.assertEqual(libraries_full[10:], my_libraries)

    def test_user_can_retrieve_all_libraries_by_paging(self):
        """
        Test that we can obtain the libraries that correspond to a given user
        with a given starting point

        :return: no return
        """
        # import pudb
        # pudb.set_trace()

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

        # Make a library that ensures we get one back
        number_of_libs = 100
        for i in range(number_of_libs):
            stub_library = LibraryShop()
            self.user_view.create_library(
                service_uid=user.id,
                library_data=stub_library.user_view_post_data
            )
        with MockEmailService(self.stub_user, end_type='uid'):
            libraries_full = self.user_view.get_libraries(
                service_uid=user.id,
                absolute_uid=user.absolute_uid, start=0
            )['libraries']
       
        
        # Get the library created
        libraries = []
        total_libraries = 0
        with MockEmailService(self.stub_user, end_type='uid'):
            for start in range(number_of_libs):
                curr_libraries = self.user_view.get_libraries(
                    service_uid=user.id,
                    absolute_uid=user.absolute_uid, start=start*10,
                    rows=10
                )
                libraries += curr_libraries['libraries']
                total_libraries = curr_libraries['count']
        self.assertEqual(total_libraries, 100)
        self.assertEqual(libraries_full, libraries)

    def test_user_can_retrieve_library_when_uid_does_not_exist(self):
        """
        Test that we can obtain the libraries that correspond to a given user

        :return: no return
        """

        # To make a library we need an actual user
        stub_user = UserShop(name='fail')
        user = User(absolute_uid=stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

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
        
        self.assertEqual(libraries['libraries'][0]['owner'], 'Not available')

    def test_user_retrieves_correct_library_content_from_userview(self):
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
        with self.app.session_scope() as session:
            session.add_all([user, user_other])
            session.commit()
            session.refresh(user)
            session.expunge(user)
            session.refresh(user_other)
            session.expunge(user_other)

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
        self.permission_view.add_permission(library_id=BaseView.helper_slug_to_uuid(_lib['id']),
                                            service_uid=user_other.id,
                                            permission={'read': True})

        # Get the library created
        with MockEmailService(stub_user_1, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user.id,
                absolute_uid=user.absolute_uid
            )
        
        self.assertTrue(libraries['count'] == number_of_libs)
        
        for library in libraries['libraries']:
            for key in self.stub_library.user_view_get_response():
                self.assertIn(key, library.keys(), 'Missing key: {0}'
                                                   .format(key))

        for j in range(number_of_libs):
            i = number_of_libs - j - 1
            for key in ['name', 'description', 'public']:
                self.assertEqual(libraries['libraries'][i][key],
                                libs[j].user_view_post_data[key])

            self.assertEqual(libraries['libraries'][i]['num_documents'], 0)

            if libraries['libraries'][i]['id'] == _lib['id']:
                self.assertEqual(libraries['libraries'][i]['num_users'], 2)
            else:
                self.assertEqual(libraries['libraries'][i]['num_users'], 1)

            self.assertEqual(libraries['libraries'][i]['permission'], 'owner')
        
        # Get the library created with a different sort order
        with MockEmailService(stub_user_1, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user.id,
                absolute_uid=user.absolute_uid,
                sort_order='asc'
            )
        
        self.assertTrue(libraries['count'] == number_of_libs)
        for library in libraries['libraries']:
            for key in self.stub_library.user_view_get_response():
                self.assertIn(key, library.keys(), 'Missing key: {0}'
                                                   .format(key))

        
        for i in range(number_of_libs):
            for key in ['name', 'description', 'public']:
                self.assertEqual(libraries['libraries'][i][key],
                                libs[i].user_view_post_data[key])
            self.assertEqual(libraries['libraries'][i]['num_documents'], 0)

            if libraries['libraries'][i]['id'] == _lib['id']:
                self.assertEqual(libraries['libraries'][i]['num_users'], 2)
            else:
                self.assertEqual(libraries['libraries'][i]['num_users'], 1)

            self.assertEqual(libraries['libraries'][i]['permission'], 'owner')
        
        # Get the library created with a different sort order and sort column
        with MockEmailService(stub_user_1, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user.id,
                absolute_uid=user.absolute_uid,
                sort_col='date_last_modified',
                sort_order='asc'
            )

        self.assertTrue(libraries['count'] == number_of_libs)
        for library in libraries['libraries']:
            for key in self.stub_library.user_view_get_response():
                self.assertIn(key, library.keys(), 'Missing key: {0}'
                                                   .format(key))

        
        for i in range(number_of_libs):
            for key in ['name', 'description', 'public']:
                self.assertEqual(libraries['libraries'][i][key],
                                libs[i].user_view_post_data[key])

            self.assertEqual(libraries['libraries'][i]['num_documents'], 0)

            if libraries['libraries'][i]['id'] == _lib['id']:
                self.assertEqual(libraries['libraries'][i]['num_users'], 2)
            else:
                self.assertEqual(libraries['libraries'][i]['num_users'], 1)

            self.assertEqual(libraries['libraries'][i]['permission'], 'owner')

        # Get the library created
        with MockEmailService(stub_user_2, end_type='uid'):
            with MockEmailService(stub_user_1, end_type='uid'):
                libraries = self.user_view.get_libraries(
                    service_uid=user_other.id,
                    absolute_uid=user_other.absolute_uid
                )

        self.assertTrue(libraries['count'] == 2)

    def test_dates_of_updates_change_correctly(self):
        """
        Test that dates change when a library is updated

        :return: no return
        """

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

        # Make a library that ensures we get one back
        stub_library = LibraryShop()
        library_dict = self.user_view.create_library(
            service_uid=user.id,
            library_data=stub_library.user_view_post_data
        )
        with self.app.session_scope() as session:
            library_1 = session.query(Library).filter(Library.id == BaseView.helper_slug_to_uuid(library_dict['id'])).one()
            session.expunge(library_1)


        self.document_view.update_library(
            library_id=BaseView.helper_slug_to_uuid(library_dict['id']),
            library_data=dict(public=True)
        )

        with self.app.session_scope() as session:
            library_2 = session.query(Library).filter(Library.id == BaseView.helper_slug_to_uuid(library_dict['id'])).one()

            self.assertEqual(library_1.date_created, library_2.date_created)
            self.assertNotEqual(library_1.date_created,
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
        with self.app.session_scope() as session:
            session.add_all([user, user_other])
            session.commit()
            session.refresh(user)
            session.expunge(user)
            session.refresh(user_other)
            session.expunge(user_other)

        # Make a library to make sure things work properly
        stub_library = LibraryShop()
        library = self.user_view.create_library(
            service_uid=user.id,
            library_data=stub_library.user_view_post_data
        )

        stub_permissions = [{'read': True}, {'write': True}, {'admin': True}]
        for permission in stub_permissions:
            self.permission_view.add_permission(library_id=BaseView.helper_slug_to_uuid(library['id']),
                                                service_uid=user_other.id,
                                                permission=permission)
            # Get the library created
            with MockEmailService(stub_user_other, end_type='uid'):
                with MockEmailService(self.stub_user, end_type='uid'):
                    libraries = self.user_view.get_libraries(
                        service_uid=user_other.id,
                        absolute_uid=user_other.absolute_uid
                    )

            self.assertEqual(list(permission.keys())[0], libraries['libraries'][0]['permission'])

    def test_can_only_see_number_of_people_with_admin_or_owner(self):
        """
        Test that the owner and admin can see the number of people
        :return: no return
        """

        # To make a library we need an actual user
        user_owner = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_admin = User(absolute_uid=self.stub_user_2.absolute_uid)

        library = Library()
        permission_admin = Permissions(permissions={'read': False, 'write': False, 'admin': True, 'owner': False})
        permission_owner = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})
        library.permissions.append(permission_admin)
        library.permissions.append(permission_owner)
        user_admin.permissions.append(permission_admin)
        user_owner.permissions.append(permission_owner)

        with self.app.session_scope() as session:
            session.add_all([user_owner, user_admin, library, permission_admin,
                                permission_owner])
            session.commit()
            for obj in [user_owner, user_admin, library, permission_admin,
                        permission_owner]:
                session.refresh(obj)
                session.expunge(obj)

        # Get the library created
        # For user admin
        with MockEmailService(self.stub_user_2, end_type='uid'):
            with MockEmailService(self.stub_user_1, end_type='uid'):
                libraries = self.user_view.get_libraries(
                    service_uid=user_admin.id,
                    absolute_uid=user_admin.absolute_uid
                )['libraries']
        
        self.assertTrue(libraries[0]['num_users'] > 0)

        # For user owner
        with MockEmailService(self.stub_user_1, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user_owner.id,
                absolute_uid=user_owner.absolute_uid
            )['libraries']
        
        self.assertTrue(libraries[0]['num_users'] > 0)

    def test_cannot_see_number_of_people_with_lower_than_admin(self):
        """
        Test that the non-owner and non-admin cannot see the number of people
        :return: no return
        """

        # To make a library we need an actual user
        user_read = User(absolute_uid=self.stub_user_1.absolute_uid)
        user_write = User(absolute_uid=self.stub_user_2.absolute_uid)
        user_owner = User(absolute_uid=self.stub_user_3.absolute_uid)

        library = Library()
        permission_read = Permissions(permissions={'read': True, 'write': False, 'admin': False, 'owner': False})
        permission_write = Permissions(permissions={'read': False, 'write': True, 'admin': False, 'owner': False})
        permission_owner = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})
        library.permissions.append(permission_read)
        library.permissions.append(permission_write)
        library.permissions.append(permission_owner)
        user_read.permissions.append(permission_read)
        user_write.permissions.append(permission_write)
        user_owner.permissions.append(permission_owner)

        with self.app.session_scope() as session:
            session.add_all([user_read, user_write, user_owner, library, permission_read,
                             permission_write, permission_owner])
            session.commit()
            for obj in [user_read, user_write, user_owner, library, permission_read,
                             permission_write, permission_owner]:
                session.refresh(obj)
                session.expunge(obj)

        # Get the library created
        # For user read
        with MockEmailService(self.stub_user_3, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user_read.id,
                absolute_uid=user_read.absolute_uid
            )['libraries']
        self.assertTrue(libraries[0]['num_users'] == 0)
        # make sure the owner is correct
        self.assertIn(libraries[0]['owner'], self.stub_user_3.email)

        # For user write
        with MockEmailService(self.stub_user_3, end_type='uid'):
            libraries = self.user_view.get_libraries(
                service_uid=user_write.id,
                absolute_uid=user_write.absolute_uid
            )['libraries']
        self.assertTrue(libraries[0]['num_users'] == 0)
        self.assertIn(libraries[0]['owner'], self.stub_user_3.email)

    def test_user_cannot_add_two_libraries_with_the_same_name(self):
        """
        Test that a user cannot add a new library with the same name

        :return: no return
        """

        # To make a library we need an actual user
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

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

            lib = session.query(Library).filter(Library.id == BaseView.helper_slug_to_uuid(library['id'])).one()
            self.assertTrue(lib.name == 'Untitled Library {0}'.format(i+1))
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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

        # Make the first library
        for i in range(2):
            library = self.user_view.create_library(
                service_uid=user.id,
                library_data=stub_library.user_view_post_data
            )

            with self.app.session_scope() as session:
                lib = session.query(Library).filter(Library.id == BaseView.helper_slug_to_uuid(library['id'])).one()
                self.assertTrue(lib.name == 'Untitled Library {0}'.format(i+1))
                self.assertTrue(lib.description == DEFAULT_LIBRARY_DESCRIPTION)

    def test_long_description_is_truncated(self):
        """
        Test that a user who provides a very long library description has that description
        truncated appropriately.

        :return: no return
        """

        # stub data
        stub_library = LibraryShop(name="Test Library", description="x"*400)

        # make a user
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

        # make the library
        library = self.user_view.create_library(service_uid=user.id, library_data=stub_library.user_view_post_data)

        # check description length
        with self.app.session_scope() as session:
            lib = session.query(Library).filter(Library.id == BaseView.helper_slug_to_uuid(library['id'])).one()
            self.assertTrue(lib.name == "Test Library")
            self.assertTrue(len(lib.description) <= 200)

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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': True})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([library, permission, user])
            session.commit()
            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)

        # Retrieve the bibcodes using the web services
        with MockEmailService(self.stub_user, end_type='uid'):
            response_library, meta_data = \
                self.library_view.get_library_and_metadata(
                    library_id=library.id,
                    service_uid=user.id, 
                    session=session
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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([library, permission, user])
            session.commit()
            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)

        with MockEmailService(self.stub_user, end_type='uid'):
            library, metadata = self.library_view.get_library_and_metadata(
                library_id=library.id,
                service_uid=user.id, 
                session=session
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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=False,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([library, permission, user, user_random])
            session.commit()
            for obj in [library, permission, user, user_random]:
                session.refresh(obj)
                session.expunge(obj)

        with MockEmailService(self.stub_user, end_type='uid'):
            library, metadata = self.library_view.get_library_and_metadata(
                library_id=library.id,
                service_uid=user_random.id,
                session=session
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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([library, permission, user])
            session.commit()
            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)

        # Retrieve the bibcodes using the web services
        with MockSolrBigqueryService():
            response_library = self.library_view.process_solr_big_query(
                bibcodes=library.bibcode
            )
        self.assertIn('responseHeader', response_library.json())


    def test_update_notes_should_create_new_note_if_canonical_note_does_not_exist(self): 
        original_bibcodes = ['arXivtest1', 'arXivtest2', 'arXivtest3', 'arXivtest4']
        canonical_bibcodes = ['canonical1', 'canonical2', 'canonical3', 'canonical4']
        with self.app.session_scope() as session: 
            # Simulating solr response where original bibcodes have a corresponding canonical bibcodes
            updated_list = [{original_bibcodes[i]: canonical_bibcodes[i]} for i in range(len(original_bibcodes))]
            
            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode={bibcode: {} for bibcode in canonical_bibcodes+original_bibcodes})
            session.add(library)
            session.commit()
            notes_ids = []
            for bibcode in original_bibcodes: 
                note = Notes.create_unique(session=session, 
                                    content='content{0}'.format(bibcode), 
                                    bibcode=bibcode,
                                    library=library)
                session.add(note)
                session.commit()
                notes_ids.append(note.id)
            
            
            LibraryView.update_notes(session, library, updated_list)
            session.refresh(library)
            session.expunge(library)

        # Assert the new notes with canonical bibcodes were created and old notes were preserved
        notes = session.query(Notes).filter(Notes.library_id == library.id).all()
        self.assertEqual(len(notes), len(original_bibcodes+canonical_bibcodes))
        self.assertEqual(original_bibcodes + canonical_bibcodes, [note.bibcode for note in notes])
        self.assertUnsortedNotEqual(notes_ids, [note.id for note in notes])
        self.assertIn('contentarXivtest1', [note.content for note in notes])
        self.assertIn('contentarXivtest2', [note.content for note in notes])
        self.assertIn('contentarXivtest3', [note.content for note in notes])
        self.assertIn('contentarXivtest4', [note.content for note in notes]) 
        self.assertNotIn('contentcanonical1', [note.content for note in notes]) 

    def test_update_notes_should_merge_content_if_canonical_already_exists(self): 
        original_bibcode1 = 'arXivtest1'
        original_bibcode2 = 'arXivtest2'
        canonical_bibcode = 'canonical1'
        with self.app.session_scope() as session:
            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode={bibcode: {} for bibcode in [original_bibcode1, original_bibcode2, canonical_bibcode]})
            session.add(library)
            session.commit()
            # Create a canonical note 
            canonical_note = Notes.create_unique(session=session, 
                                    content='canonical_note_content', 
                                    bibcode=canonical_bibcode,
                                    library=library)
            
            # Create an arxiv note 1
            arxiv_note1 = Notes.create_unique(session=session, 
                                    content='arxiv_note1_content', 
                                    bibcode=original_bibcode1,
                                    library=library)
            
            # Create an arxiv note 2 
            arxiv_note2 = Notes.create_unique(session=session, 
                                    content='arxiv_note2_content', 
                                    bibcode=original_bibcode2,
                                    library=library)
            session.add_all([canonical_note, arxiv_note1,arxiv_note2])
            session.commit()
            updated_list = [{original_bibcode1: canonical_bibcode}, {original_bibcode2: canonical_bibcode}]

            updated_notes = LibraryView.update_notes(session, library, updated_list)
            session.refresh(library)
            session.expunge(library)
            notes = session.query(Notes).filter(Notes.library_id == library.id).all()
            canonical_note = session.query(Notes).filter(Notes.library_id == library.id, Notes.bibcode == canonical_bibcode).one()
            self.assertEqual(len(notes), 3)
            self.assertUnsortedEqual([note.bibcode for note in notes], [canonical_bibcode, original_bibcode1, original_bibcode2])
            self.assertEqual(canonical_note.content, 'canonical_note_content arxiv_note1_content arxiv_note2_content')
            self.assertEqual(len(updated_notes), 3)
        
    def test_that_solr_updates_canonical_bibcodes(self):
        """
        Tests that a comparison between the solr data and the stored data is
        carried out. Mismatching documents are then updated appropriately.

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

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
                              bibcode={bibcode: {} for bibcode in original_bibcodes})
            
            

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([library, permission, user])
            session.commit()

            note = Notes.create_unique(session=session, library=library, content='arxivtest3content', bibcode='arXivtest3')
            session.add(note)
            session.commit()

            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)
            

            # Retrieve the bibcodes using the web services
            with MockSolrBigqueryService(solr_docs=solr_docs):
                response_library = self.library_view.process_solr_big_query(
                    bibcodes=library.bibcode
                ).json()
            self.assertIn('responseHeader', response_library)
            # Now check solr updates the records correctly
            solr_docs = response_library['response']['docs']
            updates = self.library_view.solr_update_library(library_id=library.id,
                                                            solr_docs=solr_docs, 
                                                            session=session)

            # Check the data returned is correct on what files were updated and why
            self.assertEqual(updates['num_updated'], 1)
            self.assertEqual(updates['duplicates_removed'], 0)
            # New note was created and old note was also added to updated_notes list
            self.assertEqual(len(updates['updated_notes']), 2)
            update_list = updates['update_list']
            self.assertEqual(update_list[0]['arXivtest3'],
                            'test3')
            

        with self.app.session_scope() as session:
            library = session.query(Library).filter(Library.id == library.id).one()
            notes = session.query(Notes).filter(Notes.library_id == library.id).all()

            self.assertEqual(len(notes), 2)
            self.assertUnsortedEqual([note.bibcode for note in notes], ['test3', 'arXivtest3'])

            self.assertUnsortedNotEqual(library.get_bibcodes(),
                                        original_bibcodes)
            self.assertUnsortedEqual(library.get_bibcodes(),
                                        canonical_bibcodes)
    def test_that_solr_maintains_bibcode_info(self):
        """
        Tests that a comparison between the solr data and the stored data is
        carried out. Mismatching documents are then updated appropriately.
        This specifically considers the case when fewer documents are returned
        as there exists two alternates.

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            original_bibcodes = ['test1', 'test2', 'arXivtest3']
            result = {'test1': {'0': 0}, 'test2': {'1': 1}, 'test3': {'2': 2}}
            solr_docs = [
                {'bibcode': 'test1'},
                {'bibcode': 'test2'},
                {'bibcode': 'test3', 'alternate_bibcode': ['arXivtest3']}
            ]

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode={k: {} for k in original_bibcodes})
            
            for i, element in enumerate(library.bibcode):
                library.bibcode[element] = {i: i}

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([library, permission, user])
            session.commit()

            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)

            # Retrieve the bibcodes using the web services
            with MockSolrBigqueryService(solr_docs=solr_docs):
                response_library = self.library_view.process_solr_big_query(
                    bibcodes=library.bibcode
                ).json()
            self.assertIn('responseHeader', response_library)

            # Now check solr updates the records correctly
            solr_docs = response_library['response']['docs']
            updates = self.library_view.solr_update_library(library_id=library.id,
                                                            solr_docs=solr_docs, 
                                                            session=session)
            
            self.assertEqual(len(updates['update_list']), 1)

        with self.app.session_scope() as session:
            library = session.query(Library).filter(Library.id == library.id).one()
            self.assertIn('timestamp', library.bibcode['test1'])
            self.assertIn('timestamp', library.bibcode['test2'])
            self.assertIn('timestamp', library.bibcode['test3'])

            for element in library.bibcode: 
                del library.bibcode[element]['timestamp']


            self.assertUnsortedEqual(library.bibcode, result)

    def test_that_solr_updates_canonical_bibcodes_with_multi_alternates(self): 
        """
        Tests that a comparison between the solr data and the stored data is
        carried out. Mismatching documents are then updated appropriately.
        This specifically considers the case when fewer documents are returned
        as there exists two alternates.

        It also tests that the notes are updated accordingly. 
        Meaning that their content will be merged if the bibcodes are updated.

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            original_bibcodes = ['test1', 'test2', 'test3', 'arXivtest3', 'conftest3']
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
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([library, permission, user])
            session.commit()

            note1 = Notes.create_unique(session=session, library=library, content='test3content', bibcode='test3')
            note2 = Notes.create_unique(session=session, library=library, content='arxivtest3content', bibcode='arXivtest3')
            note3 = Notes.create_unique(session=session, library=library, content='conftest3content', bibcode='conftest3')

            session.add_all([note1, note2, note3])
            session.commit()

            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)
             
            # Retrieve the bibcodes using the web services
            with MockSolrBigqueryService(solr_docs=solr_docs):
                response_library = self.library_view.process_solr_big_query(
                    bibcodes=library.bibcode
                ).json()
            self.assertIn('responseHeader', response_library)

            # Now check solr updates the records correctly
            solr_docs = response_library['response']['docs']
            updates = self.library_view.solr_update_library(library_id=library.id,
                                                            solr_docs=solr_docs,
                                                            session=session)

            self.assertEqual(updates['num_updated'], 2)
            self.assertEqual(updates['duplicates_removed'], 2)
            update_list = updates['update_list']

            self.assertEqual(
                get_item(update_list, 'arXivtest3'),
                'test3'
            )
            self.assertEqual(
                get_item(update_list, 'conftest3'),
                'test3'
            )

        with self.app.session_scope() as session:
            library = session.query(Library).filter(Library.id == library.id).one()

            notes = session.query(Notes).filter(Notes.library_id ==library.id).all()

            self.assertEqual(len(notes), 3)
            self.assertUnsortedEqual([note.bibcode for note in notes], ['test3', 'arXivtest3', 'conftest3'])
            self.assertUnsortedEqual([note.content for note in notes], ['arxivtest3content', 'conftest3content', 'test3content arxivtest3content conftest3content'])

            self.assertUnsortedNotEqual(library.get_bibcodes(),
                                        original_bibcodes)
            self.assertUnsortedEqual(library.get_bibcodes(),
                                     canonical_bibcodes)

    def test_that_solr_updates_canonical_bibcodes_paginate(self):
        """
        Tests that a comparison between the solr data and the stored data is
        carried out. Mismatching documents are then updated appropriately.

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            original_bibcodes = ['test1', 'arXivtest2', 'test3', 'test4']
            canonical_bibcodes = ['test1', 'test2', 'test3', 'test4']

            # We will paginate with 2, so solr will only return 2 documents
            solr_docs = [
                {'bibcode': 'test1'},
                {'bibcode': 'test2', 'alternate_bibcode': ['arXivtest2']},
            ]

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode={k: {} for k in original_bibcodes})

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([library, permission, user])
            session.commit()
            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)

            # Retrieve the bibcodes using the web services
            with MockSolrBigqueryService(solr_docs=solr_docs):
                response_library = self.library_view.process_solr_big_query(
                    bibcodes=library.bibcode
                ).json()
            self.assertIn('responseHeader', response_library)

            # Now check solr updates the records correctly
            solr_docs = response_library['response']['docs']
            updates = self.library_view.solr_update_library(library_id=library.id,
                                                            solr_docs=solr_docs,
                                                            session=session)

            # Check the data returned is correct on what files were updated and why
            self.assertEqual(updates['num_updated'], 1)
            self.assertEqual(updates['duplicates_removed'], 0)
            update_list = updates['update_list']
            self.assertEqual(update_list[0]['arXivtest2'],
                            'test2')

        with self.app.session_scope() as session:
            library = session.query(Library).filter(Library.id == library.id).one()

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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()
            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)

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
        with self.app.session_scope() as session:
            session.add(library)
            session.commit()
            session.refresh(library)
            session.expunge(library)

        exists = self.library_view.helper_library_exists(library_id=library.id)
        self.assertTrue(exists)

        with self.app.session_scope() as session:
            session.delete(library)
            session.commit()

            exists = self.library_view.helper_library_exists(library_id=library.id)
            self.assertFalse(exists)

    def test_get_library_name(self):
        """
        Tests retrieval of a library name

        :return: no return
        """

        # Make a library
        library = Library(name='TestLibrary',
                          description='Test library',
                          public=True,
                          bibcode=self.stub_library.bibcode)

        with self.app.session_scope() as session:
            session.add(library)
            session.commit()
            session.refresh(library)
            session.expunge(library)

        name = self.library_view.helper_library_name(library_id=library.id)
        self.assertEqual(name, library.name)


    def test_get_notes_from_library_retrieves_notes_and_orphan_notes(self):
        """
        Tests if get_notes_from_library retrieves notes and orphan notes

        :return: no return
        """
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            bibcodes = fake_biblist(15)
            
            canonical_bibcodes = bibcodes[:5]

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode={bibcode: {} for bibcode in bibcodes})

            # Give the user and library permissions
            permission = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([library, permission, user])
            session.commit()
            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)
            
            self.assertEqual(library.get_bibcodes(), bibcodes) 

            # add notes to the library 
            for i in range(len(bibcodes)): 
                bibcode = bibcodes[i]
                note = Notes.create_unique(library=library, bibcode=bibcode, content="content" + bibcode, session=session)
                session.add(note)
                session.commit()
    
            library.bibcode = {bibcode: {} for bibcode in canonical_bibcodes}
            session.add(library)
            session.commit()
            
            
            response = self.library_view.get_notes_from_library(library, session)
            self.assertEqual(len(response['notes']), 5)
            self.assertEqual(len(response['orphan_notes']), 10)
            self.assertUnsortedEqual(response['notes'].keys(), canonical_bibcodes)
            self.assertUnsortedEqual(response['orphan_notes'].keys(), bibcodes[5:])
                

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
        self.stub_library_3 = LibraryShop(nb_codes=4)
        self.stub_library_max = LibraryShop(nb_codes=600)

    def test_user_can_delete_a_library(self):
        """
        Tests that the user can correctly remove a library from its account

        :return: no return
        """

        # Step 1. Make the user, library, and permissions

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

            library = session.query(Library).filter(Library.id == library.id).one()
            self.assertIsInstance(library, Library)

            self.document_view.delete_library(library_id=library.id)

            with self.assertRaises(NoResultFound):
                session.query(Library).filter(Library.id == library.id).one()

    def test_user_cannot_delete_a_library_if_not_owner(self):
        """
        Tests that the user cannot delete a library if they are not the owner

        :return: no return
        """

        # Step 1. Make the user, library, and permissions

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': False, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()
            library = session.query(Library).filter(Library.id == library.id).one()
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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()
            library = session.query(Library).filter(Library.id == library.id).one()
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
        with self.app.session_scope() as session:
            session.add_all([user, user_2])
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})
            permission_2 = Permissions(permissions={'read': True, 'write': False, 'admin': False, 'owner': True})

            # Commit the stub data
            user.permissions.append(permission)
            user_2.permissions.append(permission_2)

            library.permissions.append(permission)
            library.permissions.append(permission_2)

            session.add_all([library, permission, user, user_2, permission_2])
            session.commit()

            search_library = session.query(Library).filter(
                Library.id == library.id
            ).one()
            search_permission = session.query(Permissions).filter(
                Permissions.id == permission.id
            ).all()
            self.assertIsInstance(search_library, Library)
            self.assertTrue(len(search_permission), 2)

            self.document_view.delete_library(library_id=library.id)

            with self.assertRaises(NoResultFound):
                session.query(Library).filter(
                    Library.id == library.id
                ).one()

            with self.assertRaises(NoResultFound):
                session.query(Permissions).filter(
                    Permissions.id == permission.id
                ).one()

            with self.assertRaises(NoResultFound):
                session.query(Permissions).filter(
                    Permissions.id == permission_2.id
                ).one()

            with self.assertRaises(NoResultFound):
                session.query(Permissions).filter(
                    Permissions.library_id == library.id
                ).one()

    def test_user_can_add_to_library(self):
        """
        Tests that adding a bibcode to a library works correctly

        :return:
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

            library_id = library.id

            # Get stub data for the document
            # Add a document to the library
            with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('add').get('bibcode')):
                output = self.document_view.add_document_to_library(
                    library_id=library_id,
                    document_data=self.stub_library.document_view_post_data('add')
                )
            self.assertEqual(output.get("number_added"), len(self.stub_library.bibcode))

            # Check that the document is in the library
            library = session.query(Library).filter(Library.id == library_id).all()
            for _lib in library:
                self.assertIn(list(self.stub_library.bibcode.keys())[0], _lib.bibcode)

            # Add a different document to the library
            with MockSolrQueryService(canonical_bibcode = self.stub_library_2.document_view_post_data('add').get('bibcode')):
                output = self.document_view.add_document_to_library(
                    library_id=library_id,
                    document_data=self.stub_library_2.document_view_post_data('add')
                )
            self.assertEqual(output.get("number_added"), len(self.stub_library.bibcode))

            # Check that the document is in the library
            library = session.query(Library).filter(Library.id == library_id).all()
            for _lib in library:
                self.assertIn(list(self.stub_library_2.bibcode.keys())[0], _lib.bibcode)
            #Check that timestamps have been assigned
            for _lib in library:
                for bib in _lib.bibcode:
                    self.assertIn("timestamp", _lib.bibcode[bib].keys())
                    self.assertEqual(type(_lib.bibcode[bib]["timestamp"]), float)

    def test_user_cannot_duplicate_same_document_in_library(self):
        """
        Tests that adding a bibcode to a library works correctly

        :return:
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

            library_id = library.id

            # Get stub data for the document

            # Add a document to the library
            with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('add').get('bibcode')):
                output = self.document_view.add_document_to_library(
                    library_id=library_id,
                    document_data=self.stub_library.document_view_post_data('add')
                )
            self.assertEqual(output.get("number_added"), len(self.stub_library.bibcode))

            # Shouldn't add the same document again
            with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('add').get('bibcode')):
                output = self.document_view.add_document_to_library(
                    library_id=library_id,
                    document_data=self.stub_library.document_view_post_data('add')
                )
                self.assertEqual(0, output.get("number_added"))

    def test_user_cannot_add_invalid_document_to_library(self):
        """
        Tests user cannot add invalid bibcode to a library and that 
        it returns invalid bibcodes.
        :return:
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

            library_id = library.id

            # Get stub data for the document

            # Add a document to the library
            
            with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('add').get('bibcode')):
                output = self.document_view.add_document_to_library(
                    library_id=library_id,
                    document_data=self.stub_library.document_view_post_data('add')
                )
            self.assertEqual(output.get("number_added"), len(self.stub_library.bibcode))

            # Check that the document is in the library
            library = session.query(Library).filter(Library.id == library_id).all()
            for _lib in library:
                self.assertIn(list(self.stub_library.bibcode.keys())[0], _lib.bibcode)

            # Add an invalid document to the library
            with MockSolrQueryService(canonical_bibcode = self.stub_library_2.document_view_post_data('add').get('bibcode'), invalid = True):
                output = self.document_view.add_document_to_library(
                    library_id=library_id,
                    document_data=self.stub_library_2.document_view_post_data('add')
                )
            self.assertEqual(output.get("number_added"), 0)
            self.assertEqual(output.get("invalid_bibcodes"), self.stub_library_2.document_view_post_data('add').get('bibcode'))

            # Check that the document is not in the library
            library = session.query(Library).filter(Library.id == library_id).all()
            for _lib in library:
                self.assertNotIn(list(self.stub_library_2.bibcode.keys())[0], _lib.bibcode)

    def test_user_can_add_mixed_validity_documents_to_library(self):
        """
        Tests user cannot add invalid bibcode to a library and that 
        it returns invalid bibcodes, but can still add valid ones.
        :return:
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

            library_id = library.id

            # Get stub data for the document

            # Add a document to the library
            
            with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('add').get('bibcode')):
                output = self.document_view.add_document_to_library(
                    library_id=library_id,
                    document_data=self.stub_library.document_view_post_data('add')
                )
            self.assertEqual(output.get("number_added"), len(self.stub_library.bibcode))

            # Check that the document is in the library
            library = session.query(Library).filter(Library.id == library_id).all()
            for _lib in library:
                self.assertIn(list(self.stub_library.bibcode.keys())[0], _lib.bibcode)

            # Add some more documents to the library with some being invalid
            with MockSolrQueryService(canonical_bibcode = self.stub_library_3.document_view_post_data('add').get('bibcode'), invalid = True):
                output = self.document_view.add_document_to_library(
                    library_id=library_id,
                    document_data=self.stub_library_3.document_view_post_data('add')
                )
            self.assertEqual(output.get("number_added"), 2)
            self.assertUnsortedEqual(output.get("invalid_bibcodes"), self.stub_library_3.document_view_post_data('add').get('bibcode')[0::2])

            # Check that the  first document is not in the library but the second one is.
            library = session.query(Library).filter(Library.id == library_id).all()
            for _lib in library:
                self.assertNotIn(list(self.stub_library_3.bibcode.keys())[0], _lib.bibcode)
                self.assertIn(list(self.stub_library_3.bibcode.keys())[1], _lib.bibcode)

    def test_biblib_does_not_query_bigquery_extra_times(self):
        """
        Tests that add_document_to_library() does not keep querying if
        bigquery returns empty responses during paging.
        :return:
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

            library_id = library.id

            # Get stub data for the document

            # Add a document to the library
            
            with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('add').get('bibcode')):
                output = self.document_view.add_document_to_library(
                    library_id=library_id,
                    document_data=self.stub_library.document_view_post_data('add')
                )
            self.assertEqual(output.get("number_added"), len(self.stub_library.bibcode))

            # Check that the document is in the library
            library = session.query(Library).filter(Library.id == library_id).all()
            for _lib in library:
                self.assertIn(list(self.stub_library.bibcode.keys())[0], _lib.bibcode)

            # Add some more documents to the library with some requiring a paging action
            with MockSolrBigqueryService(canonical_bibcode = self.stub_library_max.document_view_post_data('add').get('bibcode'), invalid=True) as pages:
                output = self.document_view.add_document_to_library(
                    library_id=library_id,
                    document_data=self.stub_library_max.document_view_post_data('add')
                )
                #Checks to make sure paging stops when we have all valid bibcodes.
                self.assertEqual(pages, 1)
            self.assertEqual(output.get("number_added"), round(len(self.stub_library_max.document_view_post_data('add').get('bibcode'))/4))

            # Check that the first document is not in the library but the 597th one is.
            library = session.query(Library).filter(Library.id == library_id).all()
            for _lib in library:
                self.assertNotIn(list(self.stub_library_max.bibcode.keys())[0], _lib.bibcode)
                self.assertIn(list(self.stub_library_max.bibcode.keys())[597], _lib.bibcode)

    def test_user_can_add_more_than_BIGQUERY_MAX_ROWS(self):
        """
        Tests user can add bibcodes that exceed the number 
        of bibcodes bigquery can return in a single page.
        :return:
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

            library_id = library.id

            # Get stub data for the document

            # Add a document to the library
            
            with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('add').get('bibcode')):
                output = self.document_view.add_document_to_library(
                    library_id=library_id,
                    document_data=self.stub_library.document_view_post_data('add')
                )
            self.assertEqual(output.get("number_added"), len(self.stub_library.bibcode))

            # Check that the document is in the library
            library = session.query(Library).filter(Library.id == library_id).all()
            for _lib in library:
                self.assertIn(list(self.stub_library.bibcode.keys())[0], _lib.bibcode)

            # Add some more documents to the library with some requiring a paging action
            with MockSolrBigqueryService(canonical_bibcode = self.stub_library_max.document_view_post_data('add').get('bibcode')) as pages:
                output = self.document_view.add_document_to_library(
                    library_id=library_id,
                    document_data=self.stub_library_max.document_view_post_data('add')
                )
                self.assertEqual(pages, 3)

            self.assertEqual(output.get("number_added"), len(self.stub_library_max.document_view_post_data('add').get('bibcode')))

            # Check that the last document is in the library.
            library = session.query(Library).filter(Library.id == library_id).all()
            for _lib in library:
                self.assertIn(list(self.stub_library_max.bibcode.keys())[-1], _lib.bibcode)

    def test_user_can_remove_document_from_library(self):
        """
        Test that can remove a document from the library

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()
            session.refresh(library)
            session.expunge(library)

        # Remove the bibcode from the library
        output_dict = self.document_view.remove_documents_from_library(
            library_id=library.id,
            document_data=self.stub_library.document_view_post_data('remove')
        )
        number_removed = output_dict.get('number_removed')
        self.assertEqual(number_removed, len(self.stub_library.bibcode))

        # Check it worked
        library = session.query(Library).filter(Library.id == library.id).one()

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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            session.add(library)
            session.commit()
            session.refresh(library)
            session.expunge(library)

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

        new_library = session.query(Library).filter(Library.id == library.id).one()
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
        with self.app.session_scope() as session:
            session.add_all([user_owner, user_admin])
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission_owner = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})
            permission_admin = Permissions(permissions={'read': False, 'write': False, 'admin': True, 'owner': False})

            # Commit the stub data
            user_owner.permissions.append(permission_owner)
            user_admin.permissions.append(permission_admin)

            library.permissions.append(permission_owner)
            library.permissions.append(permission_admin)
            session.add_all([library, permission_owner, permission_admin,
                             user_admin, user_owner])
            session.commit()
            for obj in (library, user_owner, user_admin):
                session.refresh(obj)
                session.expunge(obj)

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

        with self.app.session_scope() as session:
            session.add_all([user_random, user_read, user_write])
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission_read = Permissions(permissions={'read': True, 'write': False, 'admin': False, 'owner': False})
            permission_write = Permissions(permissions={'read': False, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user_read.permissions.append(permission_read)
            user_write.permissions.append(permission_write)

            library.permissions.append(permission_read)
            library.permissions.append(permission_write)
            session.add_all([library, permission_read, permission_write,
                             user_read, user_write])
            session.commit()
            for obj in (library, user_random, user_read, user_write):
                session.refresh(obj)
                session.expunge(obj)

        for user in [user_random, user_read, user_write]:
            access = self.document_view.update_access(
                service_uid=user.id,
                library_id=library.id
            )
            self.assertFalse(access)

class TestQueryViews(TestCaseDatabase):
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

        super(TestQueryViews, self).__init__(*args, **kwargs)
        self.query_view = QueryView
        self.document_view = DocumentView
        # Stub data
        self.stub_user = self.stub_user_1 = UserShop()
        self.stub_user_2 = UserShop()

        self.stub_library = self.stub_library_1 = LibraryShop()
        self.stub_library_2 = LibraryShop()

    def test_user_can_add_to_library(self):
        """
        Tests that adding a bibcode to a library works correctly

        :return:
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

            library_id = library.id

            # Get stub data for the document

            # Add a document to the library
            with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('add').get('bibcode')) as SQ:
                output_dict = self.query_view.add_query_to_library(
                    library_id=library_id,
                    document_data=self.stub_library.query_view_post_data()
                )
            self.assertEqual(output_dict.get("number_added"), len(self.stub_library.bibcode))

            # Check that the document is in the library
            library = session.query(Library).filter(Library.id == library_id).all()
            for _lib in library:
                self.assertIn(list(self.stub_library.bibcode.keys())[0], _lib.bibcode)

            # Add a different document to the library
            with MockSolrQueryService(canonical_bibcode = self.stub_library_2.document_view_post_data('add').get('bibcode')) as SQ:
                output_dict = self.query_view.add_query_to_library(
                    library_id=library_id,
                    document_data=self.stub_library_2.query_view_post_data()
                )
            self.assertEqual(output_dict.get("number_added"), len(self.stub_library.bibcode))

            # Check that the document is in the library
            library = session.query(Library).filter(Library.id == library_id).all()
            for _lib in library:
                self.assertIn(list(self.stub_library_2.bibcode.keys())[0], _lib.bibcode)

    def test_user_cannot_duplicate_same_document_in_library(self):
        """
        Tests that adding a bibcode to a library works correctly

        :return:
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

            library_id = library.id

            # Get stub data for the document

            # Add a document to the library
            with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('add').get('bibcode')) as SQ:
                output_dict = self.query_view.add_query_to_library(
                    library_id=library_id,
                    document_data=self.stub_library.query_view_post_data()
                )
            self.assertEqual(output_dict.get('number_added'), len(self.stub_library.bibcode))

            # Shouldn't add the same document again
            with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('add').get('bibcode')) as SQ:
                output_dict = self.query_view.add_query_to_library(
                    library_id=library_id,
                    document_data=self.stub_library.query_view_post_data()
                )
            self.assertEqual(0, output_dict.get('number_added'))

    def test_user_can_remove_document_from_library(self):
        """
        Test that can remove a document from the library

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()
            session.refresh(library)
            session.expunge(library)

        # Remove the bibcode from the library
        with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('remove').get('bibcode')) as SQ:
            output_dict = self.query_view.remove_query_from_library(
                library_id=library.id,
                document_data=self.stub_library.query_view_post_data()
            )
        self.assertEqual(output_dict.get("number_removed"), len(self.stub_library.bibcode))

        # Check it worked
        library = session.query(Library).filter(Library.id == library.id).one()

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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

            # add 1 to the UID to represent a random user
            access = self.query_view.write_access(
                service_uid=self.stub_user_2.absolute_uid,
                library_id=library.id
            )
            self.assertIsNotNone(access)
            self.assertFalse(access)

class TestOperationsViews(TestCaseDatabase):
    """
    Base class to test the Operations View for POST
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """

        super(TestOperationsViews, self).__init__(*args, **kwargs)
        self.operations_view = OperationsView
        self.user_view = UserView()

        # Stub data
        self.stub_user = UserShop()

        self.stub_library = LibraryShop()

    def _create_libraries(self):
        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            bibcodes_1 = ['test1', 'test2', 'test3']
            bibcodes_2 = ['test1', 'test2', 'test4']

            # Ensure a library exists
            library_1 = Library(name='MyLibrary1',
                                description='My library 1',
                                public=True,
                                bibcode={k: {} for k in bibcodes_1})

            library_2 = Library(name='MyLibrary2',
                                description='My library 2',
                                public=True,
                                bibcode={k: {} for k in bibcodes_2})

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library_1.permissions.append(permission)
            library_2.permissions.append(permission)

            session.add_all([library_1, library_2, permission, user])
            session.commit()
            for obj in [library_1, library_2, permission, user]:
                session.refresh(obj)
                session.expunge(obj)

            lib1 = session.query(Library).filter(Library.name == 'MyLibrary1').one()
            id1 = lib1.id
            lib2 = session.query(Library).filter(Library.name == 'MyLibrary2').one()
            id2 = lib2.id

            return id1, id2

    def test_library_union(self):
        """
        Test that a user with appropriate permissions can take the union of two libraries
        :return: none
        """
        id1, id2 = self._create_libraries()

        lib2_dict = {'libraries': [id2]}
        union_lib = self.operations_view.setops_libraries(id1, lib2_dict, operation='union')

        expected_union = ['test1', 'test2', 'test3', 'test4']
        self.assertEqual(len(union_lib), len(expected_union))
        self.assertEqual(set(union_lib),set(expected_union))

    def test_library_intersection(self):
        """
        Test that a user with appropriate permissions can take the intersection of two libraries
        :return: none
        """
        id1, id2 = self._create_libraries()

        lib2_dict = {'libraries': [id2]}
        intersect_lib = self.operations_view.setops_libraries(id1, lib2_dict, operation='intersection')

        expected_intersection = ['test1', 'test2']
        self.assertEqual(len(intersect_lib), len(expected_intersection))
        self.assertEqual(set(intersect_lib), set(expected_intersection))

    def test_library_difference(self):
        """
        Test that a user with appropriate permissions can take the difference of two libraries
        :return: none
        """
        id1, id2 = self._create_libraries()

        lib2_dict = {'libraries': [id2]}
        diff_lib = self.operations_view.setops_libraries(id1, lib2_dict, operation='difference')

        expected_diff = ['test3']
        self.assertEqual(len(diff_lib), len(expected_diff))
        self.assertEqual(set(diff_lib), set(expected_diff))

    def test_copy_library(self):
        """
        Test that a user with appropriate permissions can copy one library into another
        :return: none
        """
        id1, id2 = self._create_libraries()

        lib2_dict = {'libraries': [id2]}
        copy_lib = self.operations_view.copy_library(id1, lib2_dict)

        with self.app.session_scope() as session:
            lib2 = session.query(Library).filter(Library.name == 'MyLibrary2').one()
            copy_lib['bibcode'] = lib2.get_bibcodes()

        expected_dict = {'name': 'MyLibrary2',
                         'description': 'My library 2',
                         'public': True,
                         'bibcode': ['test1', 'test2', 'test3', 'test4']}
        self.assertEqual(len(copy_lib['bibcode']), len(expected_dict['bibcode']))
        self.assertIn('test3', copy_lib['bibcode'])
        self.assertEqual(copy_lib['name'], expected_dict['name'])

    def test_empty_library(self):
        """
        Test that a user with appropriate permissions can empty a library
        :return: none
        """
        id1, id2 = self._create_libraries()

        empty_lib = self.operations_view.empty_library(id2)

        with self.app.session_scope() as session:
            lib2 = session.query(Library).filter(Library.name == 'MyLibrary2').one()
            empty_lib['bibcode'] = lib2.get_bibcodes()

        expected_dict = {'name': 'MyLibrary2',
                         'description': 'My library 2',
                         'public': True,
                         'bibcode': []}
        self.assertEqual(len(empty_lib['bibcode']), len(expected_dict['bibcode']))
        self.assertEqual(empty_lib['name'], expected_dict['name'])

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
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            session.add_all([user, library])
            session.commit()
            for obj in [user, library]:
                session.refresh(obj)
                session.expunge(obj)

        self.permission_view.add_permission(service_uid=user.id,
                                            library_id=library.id,
                                            permission={'read': True})

        with self.app.session_scope() as session:
            try:
                permission = session.query(Permissions).filter(
                    Permissions.user_id == user.id,
                    Permissions.library_id == library.id
                ).one()
            except Exception as error:
                self.fail('No permissions were created, most likely the code has '
                          'not been implemented. [{0}]'.format(error))

            self.assertTrue(permission.permissions['read'])
            self.assertFalse(permission.permissions['write'])
            self.assertFalse(permission.permissions['owner'])

    def test_that_permissions_are_removed_if_the_user_has_none_left(self):
        """
        Tests that if a permission is removed and all the values are False, then
        the permission for that person and library is removed.

        :return: no return
        """

        # Make a fake user and library
        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            session.add_all([user, library])
            session.commit()
            for obj in [user, library]:
                session.refresh(obj)
                session.expunge(obj)

        # Add the permission
        self.permission_view.add_permission(service_uid=user.id,
                                            library_id=library.id,
                                            permission={'read': True})
        self.permission_view.add_permission(service_uid=user.id,
                                            library_id=library.id,
                                            permission={'write': True})

        with self.app.session_scope() as session:
            # Check the permission was added
            permission = session.query(Permissions).filter(
                Permissions.user_id == user.id,
                Permissions.library_id == library.id
            ).one()
            self.assertTrue(permission.permissions['read'])
            self.assertTrue(permission.permissions['write'])

        # Remove the permission
        self.permission_view.add_permission(service_uid=user.id,
                                            library_id=library.id,
                                            permission={'write': False})

        with self.app.session_scope() as session:
            # Check the permission was removed
            permission = session.query(Permissions).filter(
                Permissions.user_id == user.id,
                Permissions.library_id == library.id
            ).one()
            self.assertTrue(permission.permissions['read'])
            self.assertFalse(permission.permissions['write'])

        # Remove the permission
        self.permission_view.add_permission(service_uid=user.id,
                                            library_id=library.id,
                                            permission={'read': False})

        with self.app.session_scope() as session:
            # Check the permission is not available
            with self.assertRaises(NoResultFound):
                session.query(Permissions).filter(
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

        with self.app.session_scope() as session:
            session.add_all([user_1, user_2, library])
            session.commit()

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

        permission = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})
        user_2.permissions.append(permission)
        library.permissions.append(permission)

        with self.app.session_scope() as session:
            session.add_all([user_1, user_2, library])
            session.commit()
            for obj in [user_1, user_2, library]:
                session.refresh(obj)
                session.expunge(obj)

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

        permission_1 = Permissions(permissions={'read': False, 'write': False, 'admin': True, 'owner': False})
        permission_2 = Permissions(permissions={'read': False, 'write': False, 'admin': True, 'owner': False})

        user_1.permissions.append(permission_1)
        library.permissions.append(permission_1)

        user_2.permissions.append(permission_2)
        library.permissions.append(permission_2)

        with self.app.session_scope() as session:
            session.add_all([user_1, user_2, library])
            session.commit()

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

        permission_1 = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})
        permission_2 = Permissions(permissions={'read': False, 'write': False, 'admin': True, 'owner': False})

        user_1.permissions.append(permission_1)
        library.permissions.append(permission_1)

        user_2.permissions.append(permission_2)
        library.permissions.append(permission_2)

        with self.app.session_scope() as session:
            session.add_all([user_1, user_2, library])
            session.commit()
            for obj in [user_1, user_2, library]:
                session.refresh(obj)
                session.expunge(obj)

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

        permission_admin = Permissions(permissions={'read': False, 'write': False, 'admin': True, 'owner': False})
        permission_read_only = Permissions(permissions={'read': True, 'write': False, 'admin': False, 'owner': False})

        user_admin.permissions.append(permission_admin)
        library.permissions.append(permission_admin)

        user_read_only.permissions.append(permission_read_only)
        library.permissions.append(permission_read_only)

        with self.app.session_scope() as session:
            session.add_all([user_admin, user_read_only, library])
            session.commit()
            for obj in [user_admin, user_read_only, library]:
                session.refresh(obj)
                session.expunge(obj)

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
        with self.app.session_scope() as session:
            session.add(user_owner)
            session.commit()
            session.refresh(user_owner)
            session.expunge(user_owner)

        # Ensure a library exists
        library = self.user_view.create_library(
            service_uid=user_owner.id,
            library_data=self.stub_library.user_view_post_data
        )

        with self.app.session_scope() as session:
            # Check our user has owner permissions
            permission = session.query(Permissions).filter(
                Permissions.library_id == BaseView.helper_slug_to_uuid(library['id']),
                Permissions.user_id == user_owner.id
            ).one()
            self.assertTrue(permission.permissions['owner'])

        # Check that the owner cannot mess with the owner's permissions
        result = self.permission_view.has_permission(
            service_uid_editor=user_owner.id,
            service_uid_modify=user_owner.id,
            library_id=library['id']
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

        with self.app.session_scope() as session:
            session.add_all([user_owner, user_admin, user_random])
            session.commit()
            for obj in [user_owner, user_admin, user_random]:
                session.refresh(obj)
                session.expunge(obj)

        # Ensure a library exists
        library = self.user_view.create_library(
            service_uid=user_owner.id,
            library_data=self.stub_library.user_view_post_data
        )

        with self.app.session_scope() as session:
            # Check our user has owner permissions
            permission = session.query(Permissions).filter(
                Permissions.library_id == BaseView.helper_slug_to_uuid(library['id']),
                Permissions.user_id == user_owner.id
            ).one()
            self.assertTrue(permission.permissions['owner'])

        # Give the second user, admin permissions
        self.permission_view.add_permission(service_uid=user_admin.id,
                                            library_id=BaseView.helper_slug_to_uuid(library['id']),
                                            permission={'admin': True})

        with self.app.session_scope() as session:
            # Check our user has owner permissions
            permission = session.query(Permissions).filter(
                Permissions.library_id == BaseView.helper_slug_to_uuid(library['id']),
                Permissions.user_id == user_admin.id
            ).one()
            self.assertTrue(permission.permissions['admin'])
            self.assertFalse(permission.permissions['owner'])

        # Check that the admin cannot modify the owner status of random user
        with self.assertRaises(PermissionDeniedError):
            self.permission_view.add_permission(service_uid=user_random.id,
                                                library_id=BaseView.helper_slug_to_uuid(library['id']),
                                                permission={'owner': True})

        with self.app.session_scope() as session:
            # Check our user has owner permissions
            with self.assertRaises(NoResultFound):
                session.query(Permissions).filter(
                    Permissions.library_id == BaseView.helper_slug_to_uuid(library['id']),
                    Permissions.user_id == user_random.id
                ).one()

    def test_can_get_permissions_for_a_user(self):
        """
        Tests that the permissions of the user are returned
        :return: no return
        """

        # Make a fake user and library
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            permission = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([user, library, permission])
            session.commit()

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
        with self.app.session_scope() as session:
            session.add_all([user_read, user_write])
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            permission_read = Permissions(permissions={'read': True, 'write': False, 'admin': False, 'owner': False})
            permission_write = Permissions(permissions={'read': False, 'write': True, 'admin': False, 'owner': False})
            user_read.permissions.append(permission_read)
            user_write.permissions.append(permission_write)

            library.permissions.append(permission_read)
            library.permissions.append(permission_write)

            session.add_all([user_read, user_write, library, permission_read,
                             permission_write])
            session.commit()
            for obj in[user_read, user_write, library, permission_read,
                             permission_write]:
                session.refresh(obj)
                session.expunge(obj)

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
        with self.app.session_scope() as session:
            session.add_all([user_owner, user_admin])
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            permission_owner = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})
            permission_admin = Permissions(permissions={'read': False, 'write': False, 'admin': True, 'owner': False})
            user_owner.permissions.append(permission_owner)
            user_admin.permissions.append(permission_admin)

            library.permissions.append(permission_owner)
            library.permissions.append(permission_admin)

            session.add_all([user_owner, user_admin, library, permission_owner,
                             permission_admin])
            session.commit()
            for obj in [user_owner, user_admin, library, permission_owner,
                             permission_admin]:
                session.refresh(obj)
                session.expunge(obj)

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
        with self.app.session_scope() as session:
            session.add_all([user_1, user_2])
            session.commit()

            # Ensure a library exists
            library_1 = Library(name='MyLibrary',
                                description='My library',
                                public=True,
                                bibcode=self.stub_library.bibcode)

            library_2 = Library(name='MyLibrary',
                                description='My library',
                                public=True,
                                bibcode=self.stub_library.bibcode)

            permission_1 = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})
            permission_2 = Permissions(permissions={'read': False, 'write': False, 'admin': True, 'owner': False})
            user_1.permissions.append(permission_1)
            user_2.permissions.append(permission_2)

            library_1.permissions.append(permission_1)
            library_2.permissions.append(permission_2)

            session.add_all([user_1, user_2, library_1, library_2,
                             permission_1, permission_2])
            session.commit()
            for obj in [user_1, user_2, library_1, library_2,
                             permission_1, permission_2]:
                session.refresh(obj)
                session.expunge(obj)

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
        with self.app.session_scope() as session:
            session.add_all([user_none, user_read, user_write, user_admin])
            session.commit()

            # Ensure a library exists
            stub_library = Library(name='MyLibrary',
                                   description='My library',
                                   public=True,
                                   bibcode=self.stub_library.bibcode)

            permissions_read = Permissions(permissions={'read': True, 'write': False, 'admin': False, 'owner': False})
            permissions_write = Permissions(permissions={'read': False, 'write': True, 'admin': False, 'owner': False})
            permissions_admin = Permissions(permissions={'read': False, 'write': False, 'admin': True, 'owner': False})

            user_read.permissions.append(permissions_read)
            user_write.permissions.append(permissions_write)
            user_admin.permissions.append(permissions_admin)

            stub_library.permissions.append(permissions_read)
            stub_library.permissions.append(permissions_write)
            stub_library.permissions.append(permissions_admin)

            session.add_all([permissions_read, permissions_write,
                             permissions_admin, user_read, user_write,
                             user_admin, stub_library])
            session.commit()
            for obj in [user_none, user_read, user_write, user_admin] \
                        + [permissions_read, permissions_write, \
                             permissions_admin, \
                             stub_library]:
                session.refresh(obj)
                session.expunge(obj)

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

        with self.app.session_scope() as session:
            session.add_all([user_owner, user_new_owner])
            session.commit()

            # Ensure a library exists
            stub_library = Library(name='MyLibrary',
                                   description='My library',
                                   public=True,
                                   bibcode=self.stub_library.bibcode)

            permissions = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})
            user_owner.permissions.append(permissions)
            stub_library.permissions.append(permissions)

            session.add_all([permissions, user_owner, stub_library])
            session.commit()
            for obj in [user_owner, user_new_owner] + [permissions, stub_library]:
                session.refresh(obj)
                session.expunge(obj)

        self.transfer_view.transfer_ownership(current_owner_uid=user_owner.id,
                                              new_owner_uid=user_new_owner.id,
                                              library_id=stub_library.id)

        with self.app.session_scope() as session:
            permission = session.query(Permissions).filter(
                Permissions.user_id == user_new_owner.id
            ).filter(
                Permissions.library_id == stub_library.id
            ).one()
            self.assertTrue(permission.permissions['owner'])

            with self.assertRaises(NoResultFound):
                session.query(Permissions).filter(
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

        with self.app.session_scope() as session:
            session.add_all([user_owner, user_new_owner])
            session.commit()

            # Ensure a library exists
            stub_library = Library(name='MyLibrary',
                                   description='My library',
                                   public=True,
                                   bibcode=self.stub_library.bibcode)

            permissions = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})
            permissions_read = Permissions(permissions={'read': True, 'write': False, 'admin': False, 'owner': False})
            user_owner.permissions.append(permissions)
            user_new_owner.permissions.append(permissions_read)
            stub_library.permissions.append(permissions)
            stub_library.permissions.append(permissions_read)

            session.add_all([permissions, user_owner, stub_library,
                             permissions_read, user_new_owner])
            session.commit()
            for obj in [user_owner, user_new_owner] + [permissions, stub_library, \
                             permissions_read]:
                session.refresh(obj)
                session.expunge(obj)

        self.transfer_view.transfer_ownership(current_owner_uid=user_owner.id,
                                              new_owner_uid=user_new_owner.id,
                                              library_id=stub_library.id)

        with self.app.session_scope() as session:
            permission = session.query(Permissions).filter(
                Permissions.user_id == user_new_owner.id
            ).filter(
                Permissions.library_id == stub_library.id
            ).all()
            self.assertTrue(len(permission) == 1)
            self.assertTrue(permission[0].permissions['owner'])
            self.assertTrue(permission[0].permissions['read'])

            with self.assertRaises(NoResultFound):
                session.query(Permissions).filter(
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
        with self.app.session_scope() as session:
            session.add_all([user_owner, user_new_owner, user_random])
            session.commit()

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
            session.add_all([
                stub_library_1,
                stub_library_2
            ])
            session.commit()

            # Generate and add permissions
            permission_owner = Permissions(
                permissions={'read': False, 'write': False, 'admin': False, 'owner': True},
                library_id=stub_library_1.id,
                user_id=user_owner.id
            )
            permission_random_library_1 = Permissions(
                permissions={'read': True, 'write': False, 'admin': False, 'owner': False},
                library_id=stub_library_1.id,
                user_id=user_random.id
            )
            permission_random_library_2 = Permissions(
                permissions={'read': False, 'write': False, 'admin': False, 'owner': True},
                library_id=stub_library_2.id,
                user_id=user_random.id
            )
            session.add_all([
                permission_owner,
                permission_random_library_1,
                permission_random_library_2
            ])
            session.commit()
            for obj in [user_owner, user_new_owner, user_random] \
                        + [ stub_library_1, stub_library_2 ] \
                        + [ permission_owner, permission_random_library_1, permission_random_library_2 ]:
                session.refresh(obj)
                session.expunge(obj)

        # Transfer the ownership of library 1
        self.transfer_view.transfer_ownership(current_owner_uid=user_owner.id,
                                              new_owner_uid=user_new_owner.id,
                                              library_id=stub_library_1.id)

        # Check that the permissions changed properly
        # New user owner has owner permissions
        with self.app.session_scope() as session:
            permission = session.query(Permissions).filter(
                Permissions.user_id == user_new_owner.id
            ).filter(
                Permissions.library_id == stub_library_1.id
            ).one()
            self.assertTrue(permission.permissions['owner'])

            # Old owner no longer has permissions
            with self.assertRaises(NoResultFound):
                session.query(Permissions).filter(
                    Permissions.user_id == user_owner.id
                ).filter(
                    Permissions.library_id == stub_library_1.id
                ).one()

            # Check the random user did not change
            # Random owns library 2
            permission = session.query(Permissions).filter(
                Permissions.user_id == user_random.id
            ).filter(
                Permissions.library_id == stub_library_2.id
            ).one()
            self.assertTrue(permission.permissions['owner'])

            # Random reads library 1
            permission = session.query(Permissions).filter(
                Permissions.user_id == user_random.id
            ).filter(
                Permissions.library_id == stub_library_1.id
            ).one()
            self.assertTrue(permission.permissions['read'])


class TestClassicViews(TestCaseDatabase):
    """
    Base class to test the import of libraries from ADS Classic
    """
    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """

        super(TestClassicViews, self).__init__(*args, **kwargs)
        self.classic_view = ClassicView

        # Stub data
        self.stub_user = self.stub_user_1 = UserShop()
        self.stub_user_2 = UserShop()
        self.stub_library = self.stub_library_1 = LibraryShop()
        self.stub_library_2 = LibraryShop()

    def test_can_upsert_a_library_into_database(self):
        """
        Tests that you can create a library and upsert any bibcodes when there
        are no matching bibcodes
        """
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

        self.classic_view.upsert_library(
            service_uid=user.id,
            library=self.stub_library.classic_view_data()
        )

        with self.app.session_scope() as session:
            library = session.query(Library).filter(Library.name == self.stub_library.name).one()
            self.assertEqual(library.bibcode.keys(), self.stub_library.bibcode.keys())

    def test_can_upsert_a_library_when_the_names_match(self):
        """
        Tests that can try adding bibcodes when there is a library with a matching
        name
        """
        stub_user = User(absolute_uid=self.stub_user.absolute_uid)
        stub_library = Library(
            name=self.stub_library.name,
            description=self.stub_library.description,
            bibcode=self.stub_library.bibcode
        )
        stub_permission = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})
        stub_user.permissions.append(stub_permission)
        stub_library.permissions.append(stub_permission)

        with self.app.session_scope() as session:
            session.add_all([stub_user, stub_library, stub_permission])
            session.commit()
            for obj in [stub_user, stub_library, stub_permission]:
                session.refresh(obj)
                session.expunge(obj)

        stub_library_new = self.stub_library.classic_view_data().copy()
        stub_library_new['documents'].append('new bibcode')

        self.classic_view.upsert_library(
            service_uid=stub_user.id,
            library=stub_library_new
        )

        with self.app.session_scope() as session:
            library = session.query(Library).filter(Library.name == stub_library_new['name']).all()
            self.assertEqual(
                len(library),
                1,
                msg='There should only be one library with this name: {}'.format(library)
            )

            library = library[0]
            first_list = library.get_bibcodes()
            second_list = stub_library_new['documents']
            first_list.sort()
            second_list.sort()
            self.assertEqual(first_list, second_list)
            self.assertNotEqual(library.get_bibcodes(), self.stub_library.get_bibcodes())

    def test_that_it_does_not_modify_another_library_with_the_same_name(self):
        """
        Sanity check of the logic, that it is correctly modifying the users
        library, and not someone elses.
        """
        stub_user_1 = User(absolute_uid=self.stub_user_1.absolute_uid)
        stub_user_2 = User(absolute_uid=self.stub_user_2.absolute_uid)
        with self.app.session_scope() as session:
            session.add_all([stub_user_1, stub_user_2])
            session.commit()

            # Ensure a library exists
            stub_library_1 = Library(
                name=self.stub_library.name,
                description=self.stub_library.description,
                bibcode=self.stub_library.bibcode
            )
            stub_library_2 = Library(
                name=self.stub_library.name,
                description=self.stub_library.description,
                bibcode=self.stub_library.bibcode
            )
            session.add_all([
                stub_library_1,
                stub_library_2
            ])
            session.commit()

            # Generate and add permissions
            permission_user_1 = Permissions(
                permissions={'read': False, 'write': False, 'admin': False, 'owner': True},
                library_id=stub_library_1.id,
                user_id=stub_user_1.id
            )
            permission_user_2 = Permissions(
                permissions={'read': False, 'write': False, 'admin': False, 'owner': True},
                library_id=stub_library_2.id,
                user_id=stub_user_2.id
            )
            session.add_all([permission_user_1, permission_user_2])
            session.commit()
            for obj in [stub_user_1, stub_user_2] \
                        + [ stub_library_1, stub_library_2 ] \
                        + [permission_user_1, permission_user_2]:
                session.refresh(obj)
                session.expunge(obj)

        stub_library_new = self.stub_library.classic_view_data().copy()
        stub_library_new['documents'].append('new bibcode')

        self.assertEqual(stub_library_1.get_bibcodes(), stub_library_2.get_bibcodes())

        self.classic_view.upsert_library(
            service_uid=stub_user_1.id,
            library=stub_library_new
        )

        with self.app.session_scope() as session:
            library_1 = session.query(Library).filter(Library.id == stub_library_1.id).one()
            library_2 = session.query(Library).filter(Library.id == stub_library_2.id).one()

            self.assertUnsortedEqual(library_1.get_bibcodes(), stub_library_new['documents'])
            self.assertUnsortedEqual(library_2.get_bibcodes(), self.stub_library.get_bibcodes())
            self.assertNotEqual(library_1.get_bibcodes(), library_2.get_bibcodes())

    def test_it_does_nothing_if_the_same_library_name_exists(self):
        """
        Sanity check that it does nothing if another user has that library, but
        the requesting user does not
        """
        stub_user_1 = User(absolute_uid=self.stub_user_1.absolute_uid)
        stub_user_2 = User(absolute_uid=self.stub_user_2.absolute_uid)
        with self.app.session_scope() as session:
            session.add_all([stub_user_1, stub_user_2])
            session.commit()

            # Ensure a library exists
            stub_library = Library(
                name=self.stub_library.name,
                description=self.stub_library.description,
                bibcode=self.stub_library.bibcode
            )
            session.add_all([
                stub_library
            ])
            session.commit()

            # Generate and add permissions
            permission_user_2 = Permissions(
                permissions={'read': False, 'write': False, 'admin': False, 'owner': True},
                library_id=stub_library.id,
                user_id=stub_user_2.id
            )
            session.add(permission_user_2)
            session.commit()
            for obj in [stub_user_1, stub_user_2] \
                        + [stub_library, permission_user_2]:
                session.refresh(obj)
                session.expunge(obj)

        stub_library_new = self.stub_library.classic_view_data().copy()
        stub_library_new['documents'].append('new bibcode')

        lib = self.classic_view.upsert_library(
            service_uid=stub_user_1.id,
            library=stub_library_new
        )
        lib_id = BaseView.helper_slug_to_uuid(lib['library_id'])

        with self.app.session_scope() as session:
            library_1 = session.query(Library).filter(Library.id == lib_id).one()
            library_2 = session.query(Library).filter(Library.id == stub_library.id).one()

            self.assertUnsortedEqual(library_1.get_bibcodes(), stub_library_new['documents'])
            self.assertUnsortedEqual(library_2.get_bibcodes(), self.stub_library.get_bibcodes())
            self.assertNotEqual(library_1.get_bibcodes(), library_2.get_bibcodes())
            self.assertNotIn('new bibcode', library_2.get_bibcodes())

    def test_it_does_not_work_if_the_permission_is_not_owner(self):
        # Stub user
        stub_user = User(absolute_uid=self.stub_user_1.absolute_uid)
        with self.app.session_scope() as session:
            session.add(stub_user)
            session.commit()

            # Ensure a library exists
            stub_library = Library(
                name=self.stub_library.name,
                description=self.stub_library.description,
                bibcode=self.stub_library.bibcode
            )
            session.add(stub_library)
            session.commit()

            # Some permissions
            permission_user = Permissions(
                permissions={'read': True, 'write': False, 'admin': False, 'owner': False},
                library_id=stub_library.id,
                user_id=stub_user.id
            )
            session.add(permission_user)
            session.commit()
            for obj in (stub_library, stub_user, permission_user):
                session.refresh(obj)
                session.expunge(obj)

        stub_library_new = self.stub_library.classic_view_data().copy()
        stub_library_new['documents'].append('new bibcode')

        with self.app.session_scope() as session:
            for access in ['read', 'write', 'admin']:
                permission = session.query(Permissions).filter(Permissions.library_id == stub_library.id).one()
                permission.permissions = {'read': False, 'write': False, 'admin': False, 'owner': False}
                setattr(permission, access, True)
                session.add(permission)
                session.commit()

                self.classic_view.upsert_library(
                    service_uid=stub_user.id,
                    library=stub_library_new
                )

            self.assertNotIn('new bibcode', stub_library.get_bibcodes())

class TestNotesViews(TestCaseDatabase):
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

        super(TestNotesViews, self).__init__(*args, **kwargs)
        self.user_view = UserView
        self.base_view = BaseView()
        self.library_view = LibraryView
        self.notes_view = NotesView()

        self.stub_user = self.stub_user_1 = UserShop()
        self.stub_user_2 = UserShop()

        self.stub_library = LibraryShop()

    def test_user_can_get_notes_from_library(self):
        """
        Test that can retrieve all the notes from a library

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            bibcode = self.stub_library.bibcode
            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': True})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([library, permission, user])
            session.commit()

            expected_response = []
            for bibcode in library.get_bibcodes():
                note = Notes.create_unique(bibcode=bibcode, 
                             content='note {}'.format(bibcode), 
                             library=library, 
                             session=session)
                session.add(note)
                session.commit()
                expected_response.append(note.as_dict())

            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)

            # Retrieve the bibcodes using the web services
            with MockEmailService(self.stub_user, end_type='uid'):
                _, _ = \
                    self.notes_view.get_library_and_metadata_wrapper(
                        library_id=library.id,
                        service_uid=user.id, 
                        session=session
                    )
                
                response = self.notes_view.get_note_data(document_id=library.get_bibcodes()[0], library_id=library.id, service_uid=user.id)                
            
            self.assertEqual(response[2], expected_response.pop())
            session.expunge_all()
            session.close()

    def test_user_cannot_get_notes_if_no_permission(self):
        """
        Tests that the user cannot get notes if not reading access

        :return: no return
        """

        # Step 1. Make the user, library, and permissions

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)
            
            access = self.base_view.helper_check_user_has_read_access(service_uid=user.id,
                                                      library=library)
            self.assertFalse(access)


    def test_user_can_add_notes_to_library(self):
        """
        Test that can add notes to a library

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()
        
            bibcode = self.stub_library.bibcode
            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': True})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([library, permission, user])
            session.commit()

            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)

            # Retrieve the bibcodes using the web services
            with MockEmailService(self.stub_user, end_type='uid'):
                _, _ = \
                    self.notes_view.get_library_and_metadata_wrapper(
                        library_id=library.id,
                        service_uid=user.id, 
                        session=session
                    )
                
                response = self.notes_view.add_note_to_document(document_id=library.get_bibcodes()[0], library_id=library.id, service_uid=user.id, note_data={'content': 'note {}'.format(library.get_bibcodes()[0])})

            self.assertEqual(response[0]["content"], 'note {}'.format(library.get_bibcodes()[0]))
            session.expunge_all()
            session.close()

    def test_user_cannot_add_a_note_if_no_permission(self):
        """
        Tests that the user cannot add a note to library if not writing access

        :return: no return
        """

        # Step 1. Make the user, library, and permissions

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': False, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()
            library = session.query(Library).filter(Library.id == library.id).one()
            self.assertIsInstance(library, Library)

            access = self.base_view.write_access(service_uid=user.id,
                                                      library_id=library.id)
            self.assertFalse(access)



    def test_user_can_delete_notes_from_library(self):
        """
        Tests that the user can correctly remove note from a library 

        :return: no return
        """

        # Step 1. Make the user, library, and permissions

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            bibcode = self.stub_library.bibcode
            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()

            
            for bibcode in library.get_bibcodes():
                note = Notes.create_unique(bibcode=bibcode, 
                             content='note {}'.format(bibcode), 
                             library=library, 
                             session=session)
                session.add(note)
                session.commit()
            
            
            response = self.notes_view.delete_note(document_id=library.get_bibcodes()[0], library_id=library.id)

            self.assertEqual(response, True)

            session.expunge_all()
            session.close()

    def test_user_cannot_delete_a_note_if_not_owner(self):
        """
        Tests that the user cannot delete a library if they are not the owner

        :return: no return
        """

        # Step 1. Make the user, library, and permissions

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': False, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()
            library = session.query(Library).filter(Library.id == library.id).one()
            self.assertIsInstance(library, Library)

            access = self.base_view.delete_access(service_uid=user.id,
                                                      library_id=library.id)
            self.assertFalse(access)

    def test_user_can_delete_a_note_from_library_if_owner(self):
        """
        Tests that the user cannot delete a library if they are not the owner

        :return: no return
        """

        # Step 1. Make the user, library, and permissions

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': False, 'write': False, 'admin': False, 'owner': True})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()
            library = session.query(Library).filter(Library.id == library.id).one()
            self.assertIsInstance(library, Library)

            access = self.base_view.delete_access(service_uid=user.id,
                                                      library_id=library.id)
            self.assertTrue(access)

    def test_user_can_update_note_in_library(self):
        """
        Test that can update a note in library  if owner or admin

        :return: no return
        """

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            bibcode = self.stub_library.bibcode
            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': True, 'admin': False, 'owner': True})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)

            session.add_all([library, permission, user])
            session.commit()

            for obj in [library, permission, user]:
                session.refresh(obj)
                session.expunge(obj)

            # Retrieve the bibcodes using the web services
            with MockEmailService(self.stub_user, end_type='uid'):
                _, _ = \
                    self.notes_view.get_library_and_metadata_wrapper(
                        library_id=library.id,
                        service_uid=user.id, 
                        session=session
                    )
                
                self.notes_view.add_note_to_document(document_id=library.get_bibcodes()[0], library_id=library.id, service_uid=user.id, note_data={'content': 'note {}'.format(library.get_bibcodes()[0])})

                response = self.notes_view.update_note(library_id=library.id, document_id=library.get_bibcodes()[0], library_data={'content': 'updated content'})

            self.assertEqual(response["content"], 'updated content')
            session.expunge_all()
            session.close()

    def test_user_cannot_update_a_note_if_no_permission(self):
        """
        Tests that the user cannot update a note if not owner or admin

        :return: no return
        """

        # Step 1. Make the user, library, and permissions

        # Ensure a user exists
        user = User(absolute_uid=self.stub_user.absolute_uid)
        with self.app.session_scope() as session:
            session.add(user)
            session.commit()

            # Ensure a library exists
            library = Library(name='MyLibrary',
                              description='My library',
                              public=True,
                              bibcode=self.stub_library.bibcode)

            # Give the user and library permissions
            permission = Permissions(permissions={'read': True, 'write': False, 'admin': False, 'owner': False})

            # Commit the stub data
            user.permissions.append(permission)
            library.permissions.append(permission)
            session.add_all([library, permission, user])
            session.commit()
            library = session.query(Library).filter(Library.id == library.id).one()
            self.assertIsInstance(library, Library)

            access = self.base_view.update_access(service_uid=user.id,
                                                      library_id=library.id)
            self.assertFalse(access)

if __name__ == '__main__':
    unittest.main(verbosity=2)
