"""
Alembic migration management file
"""
import os
import sys
PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_HOME)
from flask import current_app
from flask_script import Manager, Command, Option
from flask_migrate import Migrate, MigrateCommand
from biblib.models import Base, User, Permissions, Library
from biblib.app import create_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Load the app with the factory
app = create_app()


class CreateDatabase(Command):
    """
    Creates the database based on models.py
    """
    @staticmethod
    def run(app=app):
        """
        Creates the database in the application context
        :return: no return
        """
        Base.metadata.create_all(bind=app.db.engine)


class DestroyDatabase(Command):
    """
    Creates the database based on models.py
    """
    @staticmethod
    def run(app=app):
        """
        Creates the database in the application context
        :return: no return
        """
        app.db.session.remove()
        Base.metadata.drop_all(bind=app.db.engine)


class DeleteStaleUsers(Command):
    """
    Compares the users that exist within the API to those within the
    microservice and deletes any stale users that no longer exist. The logic
    also takes care of the associated permissions and libraries depending on
    the cascade that has been implemented.
    """
    @staticmethod
    def run(app=app):
        """
        Carries out the deletion of the stale content
        """
        with app.app_context():
            with current_app.session_scope() as session:
                # Obtain the list of API users
                postgres_search_text = 'SELECT id FROM users;'
                result = session.execute(postgres_search_text).fetchall()
                list_of_api_users = [int(r[0]) for r in result]

                # Loop through every use in the service database
                removal_list = []
                for service_user in session.query(User).all():
                    if service_user.absolute_uid not in list_of_api_users:
                        try:
                            # Obtain the libraries that should be deleted
                            permissions = session.query(Permissions).filter(Permissions.user_id == service_user.id).all()
                            libraries = [session.query(Library).filter(Library.id == permission.library_id).one() for permission in permissions if permission.permissions['owner']]

                            # Delete all the libraries found
                            # By cascade this should delete all the permissions
                            d = [session.delete(library) for library in libraries]
                            p = [session.delete(permission) for permission in permissions]
                            d = len(d)

                            session.delete(service_user)
                            session.commit()
                            current_app.logger.info('Removed stale user: {} and {} libraries'.format(service_user, d))
                            removal_list.append(service_user)

                        except Exception as error:
                            current_app.logger.info('Problem with database, could not remove user {}: {}'
                                                    .format(service_user, error))
                            session.rollback()
                current_app.logger.info('Deleted {} stale users: {}'.format(len(removal_list), removal_list))


# Set up the alembic migration
migrate = Migrate(app, app.db, compare_type=True, directory='migrations')

# Setup the command line arguments using Flask-Script
manager = Manager(app)
manager.add_command('db', MigrateCommand)
manager.add_command('createdb', CreateDatabase())
manager.add_command('destroydb', DestroyDatabase())
manager.add_command('syncdb', DeleteStaleUsers())

if __name__ == '__main__':
    manager.run()
