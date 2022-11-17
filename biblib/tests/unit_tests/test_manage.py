"""
Tests the methods within the flask-script file manage.py
"""

import unittest
from biblib.manage import DeleteObsoleteVersionsNumber, DeleteStaleUsers, DeleteObsoleteVersionsTime
from biblib.models import User, Library, Permissions
from sqlalchemy.orm.exc import NoResultFound
from biblib.tests.base import TestCaseDatabase
import sqlalchemy_continuum
import freezegun
from datetime import datetime
from dateutil.relativedelta import relativedelta

from biblib.tests.base import TestCaseDatabase, MockSolrQueryService
from biblib.tests.stubdata.stub_data import LibraryShop
from biblib.views import DocumentView

class TestManagePy(TestCaseDatabase):
    """
    Class for testing the behaviour of the custom manage scripts
    """
    """
    Base test class for when databases are being used.
    """
    def __init__(self, *args, **kwargs):
        """
        Constructor of the class

        :param args: to pass on to the super class
        :param kwargs: to pass on to the super class

        :return: no return
        """
        super(TestManagePy, self).__init__(*args, **kwargs)

        self.document_view = DocumentView

        # Stub data
        self.stub_library = self.stub_library_1 = LibraryShop()
        self.stub_library_2 = LibraryShop()
        self.stub_library_3 = LibraryShop(nb_codes=4)
        self.n_revisions = 1
        self.n_years = 2

    def test_delete_stale_users(self):
        """
        Tests that the DeleteStaleUsers action that propogates the deletion of
        users from the API database to that of the microservice.

        :return: no return
        """

        with self.app.session_scope() as session:
            # We do not add user 1 to the API database
            session.execute('create table users (id integer, random integer);')
            session.execute('insert into users (id, random) values (2, 7);')
            session.commit()

        with self.app.session_scope() as session:
            try:

                # Add some content to the users, libraries, and permissions within
                # the microservices
                user_1 = User(absolute_uid=1)
                session.add(user_1)
                session.commit()

                user_2 = User(absolute_uid=2)

                library_1 = Library(name='Lib1')
                library_2 = Library(name='Lib2')

                session.add_all([
                    user_1, user_2,
                    library_1, library_2
                ])
                session.commit()

                # Make some permissions
                # User 1 owns library 1 and can read library 2
                # User 2 owns library 2 and can read library 1
                permission_user_1_library_1 = Permissions(
                    permissions={'read': False, 'write': False, 'admin': False, 'owner': True},
                    library_id=library_1.id,
                    user_id=user_1.id
                )
                permission_user_1_library_2 = Permissions(
                    permissions={'read': True, 'write': False, 'admin': False, 'owner': False},
                    library_id=library_2.id,
                    user_id=user_1.id
                )
                permission_user_2_library_1 = Permissions(
                    permissions={'read': True, 'write': False, 'admin': False, 'owner': False},
                    library_id=library_1.id,
                    user_id=user_2.id
                )
                permission_user_2_library_2 = Permissions(
                    permissions={'read': False, 'write': False, 'admin': False, 'owner': True},
                    library_id=library_2.id,
                    user_id=user_2.id
                )

                session.add_all([
                    permission_user_1_library_1, permission_user_1_library_2,
                    permission_user_2_library_1, permission_user_2_library_2
                ])
                session.commit()

                # Retain some IDs for when they are deleted
                user_1_id = user_1.id
                user_2_id = user_2.id
                user_1_absolute_uid = user_1.absolute_uid
                library_1_id = library_1.id
                library_2_id = library_2.id

                # Now run the stale deletion
                DeleteStaleUsers().run(app=self.app)

                # Check the state of users, libraries and permissions
                # User 2
                # 1. the user 2 should still exist
                # 2. library 2 should exist
                # 3. the permissions for library 2 for user 2 should exist
                # 4. the permissions for library 1 for user 2 should not exist
                _user_2 = session.query(User).filter(User.absolute_uid == 2).one()
                self.assertIsInstance(_user_2, User)

                _library_2 = session.query(Library)\
                    .filter(Library.id == library_2_id)\
                    .one()
                self.assertIsInstance(_library_2, Library)

                _permission_user_2_library_2 = session.query(Permissions)\
                    .filter(Permissions.library_id == library_2_id)\
                    .filter(Permissions.user_id == user_2_id)\
                    .one()
                self.assertIsInstance(_permission_user_2_library_2, Permissions)

                with self.assertRaises(NoResultFound):
                    session.query(Permissions)\
                        .filter(Permissions.library_id == library_1_id)\
                        .filter(Permissions.user_id == user_2_id)\
                        .one()

                # User 1
                # 1. the user should not exist
                # 2. library 1 should not exist
                # 3. the permissions for library 1 for user 1 should not exist
                # 4. the permissions for library 2 for user 1 should not exist
                with self.assertRaises(NoResultFound):
                    session.query(User)\
                        .filter(User.absolute_uid == user_1_absolute_uid).one()

                with self.assertRaises(NoResultFound):
                    session.query(Library)\
                        .filter(Library.id == library_1_id)\
                        .one()

                with self.assertRaises(NoResultFound):
                    session.query(Permissions)\
                        .filter(Permissions.library_id == library_1_id)\
                        .filter(Permissions.user_id == user_1_id)\
                        .one()

                with self.assertRaises(NoResultFound):
                    session.query(Permissions)\
                        .filter(Permissions.library_id == library_2_id)\
                        .filter(Permissions.user_id == user_1_id)\
                        .one()

            except Exception:
                raise
            finally:
                # Destroy the tables
                session.execute('drop table users;')
                pass

    def test_delete_obsolete_versions_number(self):
        """
        Tests that the DeleteObsoleteVersionsNumber action that removes 
        LibraryVersions older than a given number of years.

        :return: no return
        """

        with self.app.session_scope() as session:
            # We do not add user 1 to the API database
            session.execute('create table users (id integer, random integer);')
            session.execute('insert into users (id, random) values (2, 7);')
            session.commit()

        with self.app.session_scope() as session:
            try:

                # Add some content to the users, libraries, and permissions within
                # the microservices
                user_1 = User(absolute_uid=1)
                session.add(user_1)
                session.commit()

                user_2 = User(absolute_uid=2)

                library_1 = Library(name='Lib1')
                library_2 = Library(name='Lib2')

                session.add_all([
                    user_1, user_2,
                    library_1, library_2
                ])
                session.commit()

                # Make some permissions
                # User 1 owns library 1 and can read library 2
                # User 2 owns library 2 and can read library 1
                permission_user_1_library_1 = Permissions(
                    permissions={'read': False, 'write': False, 'admin': False, 'owner': True},
                    library_id=library_1.id,
                    user_id=user_1.id
                )
                permission_user_1_library_2 = Permissions(
                    permissions={'read': True, 'write': False, 'admin': False, 'owner': False},
                    library_id=library_2.id,
                    user_id=user_1.id
                )
                permission_user_2_library_1 = Permissions(
                    permissions={'read': True, 'write': False, 'admin': False, 'owner': False},
                    library_id=library_1.id,
                    user_id=user_2.id
                )
                permission_user_2_library_2 = Permissions(
                    permissions={'read': False, 'write': False, 'admin': False, 'owner': True},
                    library_id=library_2.id,
                    user_id=user_2.id
                )

                session.add_all([
                    permission_user_1_library_1, permission_user_1_library_2,
                    permission_user_2_library_1, permission_user_2_library_2
                ])
                session.commit()

                # Retain some IDs for when they are deleted
                user_1_id = user_1.id
                user_2_id = user_2.id
                user_1_absolute_uid = user_1.absolute_uid
                library_1_id = library_1.id
                library_2_id = library_2.id

                #create multiple versions by adding to library
                with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('add').get('bibcode')):
                    output = self.document_view.add_document_to_library(
                            library_id=library_1_id,
                            document_data=self.stub_library.document_view_post_data('add')
                        )
                    self.assertEqual(output.get("number_added"), len(self.stub_library.bibcode))
                    # Check that the document is in the library
                    library = session.query(Library).filter(Library.id == library_1_id).all()
                    for _lib in library:
                        self.assertIn(list(self.stub_library.bibcode.keys())[0], _lib.bibcode)

                    # Add a different document to the library
                with MockSolrQueryService(canonical_bibcode = self.stub_library_2.document_view_post_data('add').get('bibcode')):
                    output = self.document_view.add_document_to_library(
                        library_id=library_1_id,
                        document_data=self.stub_library_2.document_view_post_data('add')
                    )
                    self.assertEqual(output.get("number_added"), len(self.stub_library_2.bibcode))
                    library = session.query(Library).filter(Library.id == library_1_id).all()
                    for _lib in library:
                        self.assertIn(list(self.stub_library_2.bibcode.keys())[0], _lib.bibcode)

                with MockSolrQueryService(canonical_bibcode = self.stub_library_3.document_view_post_data('add').get('bibcode')):
                    output = self.document_view.add_document_to_library(
                        library_id=library_1_id,
                        document_data=self.stub_library_3.document_view_post_data('add')
                    )
                    self.assertEqual(output.get("number_added"), len(self.stub_library_3.bibcode))
                    # Check that the document is in the library
                    library = session.query(Library).filter(Library.id == library_1_id).all()
                    for _lib in library:
                        self.assertIn(list(self.stub_library_3.bibcode.keys())[0], _lib.bibcode)

                    service_user = user_1_id
                    permissions = session.query(Permissions).filter(Permissions.user_id == service_user).all()
                    libraries = [session.query(Library).filter(Library.id == permission.library_id).one() for permission in permissions if permission.permissions['owner']]
                    LibraryVersion = sqlalchemy_continuum.version_class(Library)
                    revision_lengths = []
                    for library in libraries:
                        revisions = session.query(LibraryVersion).filter_by(id=library.id).all()
                        revision_lengths.append(len(revisions))
                
                # Now run the obsolete deletion
                DeleteObsoleteVersionsNumber().run(app=self.app, n_revisions=self.n_revisions)
                service_user = user_1_id
                permissions = session.query(Permissions).filter(Permissions.user_id == service_user).all()
                libraries = [session.query(Library).filter(Library.id == permission.library_id).one() for permission in permissions if permission.permissions['owner']]
                LibraryVersion = sqlalchemy_continuum.version_class(Library)
                updated_revision_lengths = []
                
                #confirm most recent remaining revision matches current state of library
                for library in libraries:
                    updated_revisions = session.query(LibraryVersion).filter_by(id=library.id).all()
                    updated_revision_lengths.append(len(updated_revisions))
                    self.assertUnsortedEqual(library.bibcode, updated_revisions[-1].bibcode) 
                
                #Confirm number of revisions matches expected length
                for i in range(0,len(updated_revision_lengths)):
                    self.assertEqual(revision_lengths[i]-updated_revision_lengths[i], revision_lengths[i]-self.n_revisions)
    

            except Exception:
                raise
            finally:
                # Destroy the tables
                session.execute('drop table users;')
                pass

    def test_delete_obsolete_versions_time(self):
        """
        Tests that the DeleteObsoleteVersionsTime action that removes 
        LibraryVersions older than a given number of years.

        :return: no return
        """

        with self.app.session_scope() as session:
            # We do not add user 1 to the API database
            session.execute('create table users (id integer, random integer);')
            session.execute('insert into users (id, random) values (2, 7);')
            session.commit()

        with self.app.session_scope() as session:
            try:

                # Add some content to the users, libraries, and permissions within
                # the microservices
                user_1 = User(absolute_uid=1)
                session.add(user_1)
                session.commit()

                user_2 = User(absolute_uid=2)

                library_1 = Library(name='Lib1')
                library_2 = Library(name='Lib2')

                session.add_all([
                    user_1, user_2,
                    library_1, library_2
                ])
                session.commit()

                # Make some permissions
                # User 1 owns library 1 and can read library 2
                # User 2 owns library 2 and can read library 1
                permission_user_1_library_1 = Permissions(
                    permissions={'read': False, 'write': False, 'admin': False, 'owner': True},
                    library_id=library_1.id,
                    user_id=user_1.id
                )
                permission_user_1_library_2 = Permissions(
                    permissions={'read': True, 'write': False, 'admin': False, 'owner': False},
                    library_id=library_2.id,
                    user_id=user_1.id
                )
                permission_user_2_library_1 = Permissions(
                    permissions={'read': True, 'write': False, 'admin': False, 'owner': False},
                    library_id=library_1.id,
                    user_id=user_2.id
                )
                permission_user_2_library_2 = Permissions(
                    permissions={'read': False, 'write': False, 'admin': False, 'owner': True},
                    library_id=library_2.id,
                    user_id=user_2.id
                )

                session.add_all([
                    permission_user_1_library_1, permission_user_1_library_2,
                    permission_user_2_library_1, permission_user_2_library_2
                ])
                session.commit()

                # Retain some IDs for when they are deleted
                user_1_id = user_1.id
                user_2_id = user_2.id
                user_1_absolute_uid = user_1.absolute_uid
                library_1_id = library_1.id
                library_2_id = library_2.id

                #create multiple versions by adding to library
                with MockSolrQueryService(canonical_bibcode = self.stub_library.document_view_post_data('add').get('bibcode')):
                    output = self.document_view.add_document_to_library(
                            library_id=library_1_id,
                            document_data=self.stub_library.document_view_post_data('add')
                        )
                    self.assertEqual(output.get("number_added"), len(self.stub_library.bibcode))
                    #Check that the document is in the library
                    library = session.query(Library).filter(Library.id == library_1_id).all()
                    for _lib in library:
                        self.assertIn(list(self.stub_library.bibcode.keys())[0], _lib.bibcode)

                #Add a different document to the library
                with MockSolrQueryService(canonical_bibcode = self.stub_library_2.document_view_post_data('add').get('bibcode')):
                    output = self.document_view.add_document_to_library(
                        library_id=library_1_id,
                        document_data=self.stub_library_2.document_view_post_data('add')
                    )
                    self.assertEqual(output.get("number_added"), len(self.stub_library_2.bibcode))
                    library = session.query(Library).filter(Library.id == library_1_id).all()
                    for _lib in library:
                        self.assertIn(list(self.stub_library_2.bibcode.keys())[0], _lib.bibcode)

                with MockSolrQueryService(canonical_bibcode = self.stub_library_3.document_view_post_data('add').get('bibcode')):
                    output = self.document_view.add_document_to_library(
                        library_id=library_1_id,
                        document_data=self.stub_library_3.document_view_post_data('add')
                    )
                    self.assertEqual(output.get("number_added"), len(self.stub_library_3.bibcode))
                    #Check that the document is in the library
                    library = session.query(Library).filter(Library.id == library_1_id).all()
                    for _lib in library:
                        self.assertIn(list(self.stub_library_3.bibcode.keys())[0], _lib.bibcode)

                    service_user = user_1_id
                    permissions = session.query(Permissions).filter(Permissions.user_id == service_user).all()
                    libraries = [session.query(Library).filter(Library.id == permission.library_id).one() for permission in permissions if permission.permissions['owner']]
                    LibraryVersion = sqlalchemy_continuum.version_class(Library)
                    revision_lengths = []
                    for library in libraries:
                        revisions = session.query(LibraryVersion).filter_by(id=library.id).all()
                        revision_lengths.append(len(revisions))
                
                #Now run the obsolete deletion acting as if we are 1 year in the future.
                current_offset = datetime.now() + relativedelta(years=1)
                with freezegun.freeze_time(current_offset):
                    DeleteObsoleteVersionsTime().run(app=self.app, n_years=self.n_years)
                service_user = user_1_id
                permissions = session.query(Permissions).filter(Permissions.user_id == service_user).all()
                libraries = [session.query(Library).filter(Library.id == permission.library_id).one() for permission in permissions if permission.permissions['owner']]
                LibraryVersion = sqlalchemy_continuum.version_class(Library)
                updated_revision_lengths = []
                
                #Confirm most recent remaining revision matches current state of library
                for library in libraries:
                    updated_revisions = session.query(LibraryVersion).filter_by(id=library.id).all()
                    updated_revision_lengths.append(len(updated_revisions))
                    self.assertUnsortedEqual(library.bibcode, updated_revisions[-1].bibcode) 

                #Run obsolete deletion assuming we are 2 years in the future.
                current_offset = datetime.now() + relativedelta(years=2)
                with freezegun.freeze_time(current_offset):
                    DeleteObsoleteVersionsTime().run(app=self.app, n_years=self.n_years)
                service_user = user_1_id
                permissions = session.query(Permissions).filter(Permissions.user_id == service_user).all()
                libraries = [session.query(Library).filter(Library.id == permission.library_id).one() for permission in permissions if permission.permissions['owner']]
                LibraryVersion = sqlalchemy_continuum.version_class(Library)
                updated_revision_lengths = []

                #Confirm all things are deleted now.
                for library in libraries:
                    updated_revisions = session.query(LibraryVersion).filter_by(id=library.id).all()
                    self.assertEqual(len(updated_revisions), 0) 

            except Exception:
                # Destroy the tables
                raise
            finally:
                # Destroy the tables
                session.execute('drop table users;')
                pass

if __name__ == '__main__':
    unittest.main(verbosity=2)


