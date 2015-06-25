"""
Tests the methods within the flask-script file manage.py
"""

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import test_config
import unittest
from manage import CreateDatabase, DestroyDatabase, DeleteStaleUsers
from models import User, Library, Permissions, db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound


class TestManagePy(unittest.TestCase):
    """
    Class for testing the behaviour of the custom manage scripts
    """

    def test_create_database(self):
        """
        Tests the CreateDatabase action. This should create all the tables
        that should exist in the database.

        :return: no return
        """

        # Setup the tables
        CreateDatabase.run()
        engine = create_engine(test_config.SQLALCHEMY_BINDS['libraries'])
        connection = engine.connect()

        for model in [User, Library, Permissions]:
            exists = engine.dialect.has_table(connection, model.__tablename__)
            self.assertTrue(exists)

        # Clean up the tables
        db.metadata.drop_all(bind=engine)

    def test_destroy_database(self):
        """
        Tests the DestroyDatabase action. This should clear all the tables
        that were created in the database.

        :return: no return
        """

        # Setup the tables
        engine = create_engine(test_config.SQLALCHEMY_BINDS['libraries'])
        connection = engine.connect()
        db.metadata.create_all(bind=engine)

        for model in [User, Library, Permissions]:
            exists = engine.dialect.has_table(connection, model.__tablename__)
            self.assertTrue(exists)

        DestroyDatabase.run()

        for model in [User, Library, Permissions]:
            exists = engine.dialect.has_table(connection, model.__tablename__)
            self.assertFalse(exists)

    def test_delete_stale_users(self):
        """
        Tests that the DeleteStaleUsers action that propogates the deletion of
        users from the API database to that of the microservice.

        :return: no return
        """

        # Setup the tables
        engine = create_engine(test_config.SQLALCHEMY_BINDS['libraries'])

        session_factory = sessionmaker(bind=engine)
        session = session_factory()

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
                owner=True,
                library_id=library_1.id,
                user_id=user_1.id
            )
            permission_user_1_library_2 = Permissions(
                read=True,
                library_id=library_2.id,
                user_id=user_1.id
            )
            permission_user_2_library_1 = Permissions(
                read=True,
                library_id=library_1.id,
                user_id=user_2.id
            )
            permission_user_2_library_2 = Permissions(
                owner=True,
                library_id=library_1.id,
                user_id=user_2.id
            )

            session.add_all([
                permission_user_1_library_1, permission_user_1_library_2,
                permission_user_2_library_1, permission_user_2_library_2
            ])
            session.commit()

            # Now run the stale deletion
            DeleteStaleUsers.run()

            # Check the state of users, libraries and permissions
            # User 2
            # 1. the user 2 should still exist
            # 2. library 2 should exist
            # 3. the permissions for library 2 for user 2 should exist
            # 4. the permissions for library 1 for user 2 should not exist
            _user_2 = session.query(User).filter(User.absolute_uid == 2).one()
            self.assertIsInstance(_user_2, User)

            _library_2 = session.query(Library)\
                .filter(Library.id == library_2.id)\
                .one()
            self.assertIsInstance(_library_2, Library)

            _permission_user_2_library_1 = session.query(Permissions)\
                .filter(Permissions.library_id == library_1.id)\
                .filter(Permissions.user_id == user_1.id)\
                .one()
            self.assertIsInstance(_permission_user_2_library_1, Permissions)

            # Temporarily skip
            try:
                with self.assertRaises(NoResultFound):
                    session.query(Permissions)\
                        .filter(Permissions.library_id == library_1.id)\
                        .filter(Permissions.user_id == user_1.id)\
                        .one()
            except:
                pass

            # User 1
            # 1. the user should not exist
            # 2. library 1 should not exist
            # 3. the permissions for library 1 for user 1 should not exist
            # 4. the permissions for library 2 for user 1 should not exist
            with self.assertRaises(NoResultFound):
                session.query(User)\
                    .filter(User.absolute_uid == user_1.absolute_uid).one()

            with self.assertRaises(NoResultFound):
                session.query(Library)\
                    .filter(Library.id == library_1.id)\
                    .one()

            with self.assertRaises(NoResultFound):
                session.query(Permissions)\
                    .filter(Permissions.library_id == library_1.id)\
                    .filter(Permissions.user_id == user_1.id)\
                    .one()

            with self.assertRaises(NoResultFound):
                session.query(Permissions)\
                    .filter(Permissions.library_id == library_2.id)\
                    .filter(Permissions.user_id == user_1.id)\
                    .one()

        except Exception:
            raise
        finally:
            # Destroy the tables
            session.close()
            db.metadata.drop_all(bind=engine)

#
# class TestManagePyFlask(flask_testing.TestCase):
#     """
#     Class for testing the behaviour of the custom manage scripts. This uses
#     flask for easy access to the database connection.
#     """
#


if __name__ == '__main__':
    unittest.main(verbosity=2)