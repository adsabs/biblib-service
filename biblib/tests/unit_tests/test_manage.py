"""
Tests the methods within the flask-script file manage.py
"""

import os
import unittest
import testing.postgresql
from biblib.app import create_app
from biblib.manage import CreateDatabase, DestroyDatabase, DeleteStaleUsers
from biblib.models import Base, User, Library, Permissions
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.exc import NoResultFound
from biblib.tests.base import TestCaseDatabase

class TestManagePy(TestCaseDatabase):
    """
    Class for testing the behaviour of the custom manage scripts
    """
    """
    Base test class for when databases are being used.
    """

    def test_create_database(self):
        """
        Tests the CreateDatabase action. This should create all the tables
        that should exist in the database.

        :return: no return
        """

        # Setup the tables
        CreateDatabase.run(app=self.app)
        engine = create_engine(TestManagePy.postgresql_url)
        connection = engine.connect()

        for model in [User, Library, Permissions]:
            exists = engine.dialect.has_table(connection, model.__tablename__)
            self.assertTrue(exists)

        # Clean up the tables
        Base.metadata.drop_all(bind=self.app.db.engine)

    def test_destroy_database(self):
        """
        Tests the DestroyDatabase action. This should clear all the tables
        that were created in the database.

        :return: no return
        """

        # Setup the tables
        engine = create_engine(TestManagePy.postgresql_url)
        connection = engine.connect()
        Base.metadata.create_all(bind=self.app.db.engine)

        for model in [User, Library, Permissions]:
            exists = engine.dialect.has_table(connection, model.__tablename__)
            self.assertTrue(exists)

        DestroyDatabase.run(app=self.app)

        for model in [User, Library, Permissions]:
            exists = engine.dialect.has_table(connection, model.__tablename__)
            self.assertFalse(exists)

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

if __name__ == '__main__':
    unittest.main(verbosity=2)
